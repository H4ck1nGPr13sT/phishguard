---
phase: 08-batch-processing-web-interface
plan: 04
subsystem: api
tags: [fastapi, csv, background-tasks, threading, pydantic]

# Dependency graph
requires:
  - phase: 08-batch-processing-web-interface
    provides: "Wave 0 contract tests (tests/test_batch_api.py) and fixture tests/fixtures/batch_sample.csv defining the POST /batch + GET /batch/{id} API shape"
provides:
  - "src/api/inference.py: predict_url_multi / predict_email_text / predict_sms_text — single shared inference code path"
  - "src/api/batch.py: POST /batch (validated CSV upload -> background job -> uuid4 id) and GET /batch/{id} (status/progress polling with offset slice)"
  - "Bounded, locked, in-memory job store (JOBS/_LOCK) with MAX_JOBS eviction of finished jobs only"
affects: [08-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shared inference helpers: single endpoints and the batch runner call the same predict_url_multi/predict_email_text/predict_sms_text functions (no duplicated inference logic)"
    - "Sync background job: run_batch is a sync def scheduled via FastAPI BackgroundTasks, runs in the threadpool so it never blocks the event loop"
    - "Per-row error isolation: one bad CSV row never aborts the batch; stored error is a short generic message + exception class name only, never str(e)/traceback"

key-files:
  created: [src/api/inference.py, src/api/batch.py]
  modified: [src/api/endpoints.py, src/api/main.py]

key-decisions:
  - "Extracted per-content-type inference into src/api/inference.py first (Task 1), then built batch on top of it (Task 2), so there is exactly one inference code path for URL/email/SMS shared by both single endpoints and the batch runner"
  - "CSV intake validated in this order: .csv extension -> bounded read(MAX+1) size cap -> utf-8-sig decode -> case-insensitive type/content header check -> csv.Error-wrapped row collection (catches field_size_limit overflows) -> row-count cap -> zero-data-rows cap"
  - "MAX_JOBS eviction only removes a job whose status is done/failed, walking JOBS in insertion order; queued/running jobs are never evicted to avoid a KeyError inside an in-flight run_batch"
  - "_dispatch_row reuses the existing URLRequest/EmailTextRequest/SMSRequest Pydantic validators per row for per-row validation parity with the single endpoints, then routes to the shared inference helpers"

patterns-established:
  - "New inference logic (any future content type) should be added to src/api/inference.py as a pure predict_*(content) -> dict helper and consumed by both the endpoint and any batch-style caller, not duplicated"

requirements-completed: [INPUT-05, WEB-07, WEB-02]

# Metrics
duration: 4min
completed: 2026-09-30
---

# Phase 08 Plan 04: Shared Inference Helpers + Async CSV Batch Processing Summary

**Extracted predict_url_multi/predict_email_text/predict_sms_text into src/api/inference.py and built POST /batch + GET /batch/{id} on top of them with a bounded, locked, in-memory job store — no internal HTTP calls, no duplicated inference.**

## Performance

- **Duration:** ~4 min (task commits 20:37:54 -> 20:41:17 UTC+2)
- **Started:** 2026-09-30T20:37:54+02:00
- **Completed:** 2026-09-30T20:41:17+02:00
- **Tasks:** 2
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments
- Single inference code path: `src/api/inference.py` exposes `predict_url_multi`, `predict_email_text`, `predict_sms_text`; `src/api/endpoints.py`'s `predict_multi_paradigm`/`predict_email`/`predict_sms` now call these helpers instead of duplicating the pipeline inline. Zero behavior change — all 67 existing endpoint tests still pass.
- Real async CSV batch endpoint: `POST /batch` validates a CSV upload (extension, 1MB size cap, utf-8-sig decode, case-insensitive `type,content` header, `csv.field_size_limit`-bounded cells, 500-row cap, header-only rejection) entirely in memory (`io.StringIO`, never written to disk), starts a background job via `BackgroundTasks.add_task(run_batch, ...)`, and returns `{"job_id": <uuid4.hex>, "total": N}`.
- `GET /batch/{job_id}` returns `{"status","total","done","rows"}` with an `offset`-sliced, copied row list; 404s on unknown ids.
- `run_batch` is a sync `def` (runs in FastAPI's threadpool, never blocks the event loop) with strict per-row error isolation: a failing row is recorded with `error = "row failed: {ExceptionClassName}"` — no `str(e)` or traceback ever stored — and the loop continues to the next row.
- `JOBS`/`_LOCK`-protected in-memory store bounded by `MAX_JOBS = 50`; eviction only removes the oldest job whose status is `"done"`/`"failed"`, never a `"queued"`/`"running"` job.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract shared inference helpers and refactor endpoints to use them** - `9a316ba` (refactor)
2. **Task 2: Implement /batch upload + polling + bounded in-memory job store** - `5213edf` (feat)

**Plan metadata:** (this commit) - `docs(08-04): complete shared inference + batch plan`

## Files Created/Modified
- `src/api/inference.py` - New. `predict_url_multi(url)`, `predict_email_text(raw_email)`, `predict_sms_text(message)` — pure helpers wrapping the existing feature-extraction -> model -> (aggregator, for URL) pipelines; raises `ModelsNotLoaded` if required `ml_models` keys are missing.
- `src/api/endpoints.py` - Modified. `predict_multi_paradigm`, `predict_email`, `predict_sms` now call the shared helpers and map the returned dict into their existing Pydantic response models; `/predict`, `/predict/ensemble`, `/predict/email/file`, `/predict/image` bodies untouched (they still call `extract_*_features` directly, as scoped).
- `src/api/batch.py` - New. `router` (`POST /batch`, `GET /batch/{job_id}`), `_dispatch_row` (monkeypatch seam), `run_batch`, `JOBS`/`_LOCK`, cap constants (`MAX_CSV_BYTES`, `MAX_CSV_ROWS`, `MAX_CELL_CHARS`, `ALLOWED_TYPES`, `MAX_JOBS`).
- `src/api/main.py` - Modified. Imports and includes `batch_router` alongside the existing `web_router`/`router`.

## Decisions Made
- Kept `/predict/image` and `/predict/email/file` calling `extract_*_features` directly rather than routing through the new helpers — they have OCR/visual-signal pipelines materially different from the plain email/SMS text path and the plan scoped the refactor to the three helpers listed in the interfaces section (predict_multi_paradigm, predict_email, predict_sms only).
- `_dispatch_row` validates `row_type`/cell length and instantiates the matching Pydantic request model (raising `ValidationError` on bad rows) before calling the shared inference helper, so a CSV row gets the exact same input validation as its equivalent single-sample endpoint.

## Deviations from Plan

None - plan executed exactly as written, including the checker-warning fixes already folded into Task 2's action text (lowercased/normalized fieldnames read via lowercased keys, `csv.Error`-wrapped row collection, header-only rejection, finished-only MAX_JOBS eviction).

## Issues Encountered

A prior tool-call attempting to write `src/api/inference.py` and refactor `src/api/endpoints.py` via a Python heredoc script was interrupted mid-flight by the environment's safety classifier; on re-inspection the file changes had nonetheless already landed on disk (confirmed via `git diff`/`git status`). The only follow-up needed was fixing one leftover naming mismatch (the endpoints.py call site referenced `predict_url_multi` while the import had aliased it to `_predict_url_multi`) — corrected by dropping the alias. No functional deviation from the plan resulted.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`src/api/batch.py` and `src/api/inference.py` are ready for 08-05 (batch frontend: progress bar + results table polling `GET /batch/{id}`). The Wave 0 contract tests (`tests/test_batch_api.py`, 11 tests) and the full existing suite (`tests/test_api.py`, `tests/test_api_multiparadigm.py`, `tests/test_api_email_sms.py`, plus everything else) are green: `434 passed, 1 skipped` (the 1 skip is pre-existing and unrelated to this plan). No blockers.

---
*Phase: 08-batch-processing-web-interface*
*Completed: 2026-09-30*

## Self-Check: PASSED
- FOUND: src/api/inference.py
- FOUND: src/api/batch.py
- FOUND: .planning/phases/08-batch-processing-web-interface/08-04-SUMMARY.md
- FOUND: commit 9a316ba
- FOUND: commit 5213edf
