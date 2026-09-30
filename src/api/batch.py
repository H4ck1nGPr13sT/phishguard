"""Async CSV batch processing (INPUT-05, WEB-07).

POST /batch accepts a validated CSV (columns: type,content), starts a
real background job (FastAPI BackgroundTasks running a sync function in
the threadpool), and returns a uuid4 job id immediately. GET /batch/{id}
polls job status/progress with an offset-sliced row window.

Security (see 08-04-PLAN.md threat_model, ASVS V5/V12):
- Upload is bounded (1MB read cap, 500-row cap, 5000-char/cell cap) and
  processed entirely in-memory — never written to disk.
- Per-row errors are isolated: one bad row never aborts the job, and its
  stored error is a short generic message + exception class name only
  (never str(e)/traceback) to avoid leaking internals.
- Job ids are uuid4.hex (122-bit, unguessable); there is no list endpoint.
- The in-memory job store is protected by a lock and bounded by MAX_JOBS
  (oldest finished job evicted; running/queued jobs are never evicted).
"""

import csv
import io
import threading
import uuid

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from pydantic import ValidationError

from src.api.inference import predict_url_multi, predict_email_text, predict_sms_text
from src.api.models import EmailTextRequest, SMSRequest, URLRequest

MAX_CSV_BYTES = 1 * 1024 * 1024  # 1MB
MAX_CSV_ROWS = 500
MAX_CELL_CHARS = 5000
ALLOWED_TYPES = {"url", "email", "sms"}
MAX_JOBS = 50

# Bound the csv module's own field-size guard so an over-limit cell raises
# csv.Error during parsing instead of silently consuming unbounded memory.
csv.field_size_limit(MAX_CELL_CHARS)

JOBS: dict[str, dict] = {}
_LOCK = threading.Lock()

router = APIRouter()

_VALIDATORS = {
    "url": lambda content: URLRequest(url=content),
    "email": lambda content: EmailTextRequest(raw_email=content),
    "sms": lambda content: SMSRequest(message=content),
}

_DISPATCHERS = {
    "url": lambda content: predict_url_multi(content),
    "email": lambda content: predict_email_text(content),
    "sms": lambda content: predict_sms_text(content),
}


def _dispatch_row(row_type: str, content: str) -> dict:
    """Monkeypatch seam (tests patch 'src.api.batch._dispatch_row').

    Validates row_type/content, reuses the single-sample Pydantic request
    validators for per-row validation parity with the single endpoints,
    then routes to the shared inference helper. Returns a plain
    {"prediction": str, "probability": float} dict.
    """
    if row_type not in ALLOWED_TYPES:
        raise ValueError(f"Unsupported type: {row_type}")
    if len(content) > MAX_CELL_CHARS:
        raise ValueError("Cell content too large")

    # Reuse existing per-field validators (raises pydantic.ValidationError).
    _VALIDATORS[row_type](content)

    result = _DISPATCHERS[row_type](content)
    return {
        "prediction": result["final_prediction"],
        "probability": float(result["final_probability"]),
    }


def run_batch(job_id: str, rows: list[dict]) -> None:
    """Process all rows for a job. SYNC def — runs in FastAPI's threadpool
    (never async), per the research doc's Pattern 3 / Anti-Patterns.

    One bad row never aborts the job: per-row exceptions are caught and
    recorded as a short generic error + exception class name only.
    """
    with _LOCK:
        job = JOBS.get(job_id)
        if job is None:
            return
        job["status"] = "running"

    try:
        for i, row in enumerate(rows, start=1):
            row_type = row.get("type", "")
            content = row.get("content", "")
            content_preview = content[:80]

            result_row = {
                "row": i,
                "type": row_type,
                "content_preview": content_preview,
                "prediction": None,
                "probability": None,
                "error": None,
            }
            try:
                dispatched = _dispatch_row(row_type, content)
                result_row["prediction"] = dispatched["prediction"]
                result_row["probability"] = dispatched["probability"]
            except Exception as e:  # noqa: BLE001 — per-row isolation, generic message only
                result_row["prediction"] = "error"
                result_row["probability"] = 0.0
                result_row["error"] = f"row failed: {type(e).__name__}"

            with _LOCK:
                job = JOBS.get(job_id)
                if job is None:
                    return
                job["rows"].append(result_row)
                job["done"] += 1

        with _LOCK:
            job = JOBS.get(job_id)
            if job is not None:
                job["status"] = "done"
    except Exception:
        # Unexpected failure OUTSIDE the per-row loop (e.g. job vanished,
        # unrecoverable state) — mark the job failed rather than leaving
        # it stuck "running" forever.
        with _LOCK:
            job = JOBS.get(job_id)
            if job is not None:
                job["status"] = "failed"


def _evict_oldest_finished_locked() -> None:
    """Evict the oldest job whose status is 'done' or 'failed'. Never
    evicts a 'queued'/'running' job (that would KeyError inside a running
    run_batch). Caller must hold _LOCK. No-op if nothing is evictable."""
    if len(JOBS) <= MAX_JOBS:
        return
    for job_id, job in JOBS.items():  # dict preserves insertion order
        if job.get("status") in ("done", "failed"):
            del JOBS[job_id]
            return


@router.post("/batch")
async def start_batch(background: BackgroundTasks, file: UploadFile = File(...)):
    filename = (file.filename or "").lower()
    if not filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be .csv format")

    raw = await file.read(MAX_CSV_BYTES + 1)
    if len(raw) > MAX_CSV_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 1MB)")

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    reader = csv.DictReader(io.StringIO(text))
    fieldnames = [f.strip().lower() for f in (reader.fieldnames or [])]
    if not {"type", "content"}.issubset(set(fieldnames)):
        raise HTTPException(
            status_code=400, detail="CSV must have 'type' and 'content' columns"
        )
    reader.fieldnames = fieldnames

    rows: list[dict] = []
    try:
        for raw_row in reader:
            rows.append(
                {
                    "type": (raw_row.get("type") or "").strip(),
                    "content": raw_row.get("content") or "",
                }
            )
            if len(rows) > MAX_CSV_ROWS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Too many rows (max {MAX_CSV_ROWS})",
                )
    except csv.Error:
        raise HTTPException(status_code=400, detail="Invalid or oversized CSV cell")

    if len(rows) == 0:
        raise HTTPException(status_code=400, detail="CSV has no data rows")

    job_id = uuid.uuid4().hex
    with _LOCK:
        JOBS[job_id] = {
            "status": "queued",
            "total": len(rows),
            "done": 0,
            "rows": [],
        }
        _evict_oldest_finished_locked()

    background.add_task(run_batch, job_id, rows)

    return {"job_id": job_id, "total": len(rows)}


@router.get("/batch/{job_id}")
def batch_status(job_id: str, offset: int = 0):
    with _LOCK:
        job = JOBS.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        safe_offset = max(offset, 0)
        return {
            "status": job["status"],
            "total": job["total"],
            "done": job["done"],
            "rows": list(job["rows"][safe_offset:]),
        }
