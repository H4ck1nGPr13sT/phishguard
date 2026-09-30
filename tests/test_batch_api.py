"""Batch API contract tests (Phase 8 Plan 01 — Wave 0).

These tests encode the INPUT-05 / WEB-07 contracts for the CSV batch
upload + polling endpoints (POST /batch, GET /batch/{job_id}) BEFORE the
implementation lands in plan 08-04. They are RED by design until 08-04
ships `src/api/batch.py` — that is the expected and correct state for
this plan.

Module-top imports are limited to `app`, `TestClient`, and stdlib so this
file always collects cleanly even before src/api/batch.py exists. The
monkeypatch seam (`src.api.batch._dispatch_row`) is referenced via its
dotted string path and `src.api.batch` is imported lazily inside test
bodies so collection never fails on the not-yet-existing module.
"""

import os

from fastapi.testclient import TestClient

from src.api.main import app

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def _fixture_bytes(name: str) -> bytes:
    with open(os.path.join(FIXTURES_DIR, name), "rb") as fh:
        return fh.read()


def _fake_dispatch_ok(row_type: str, content: str) -> dict:
    return {"prediction": "phishing", "probability": 0.9}


def test_batch_happy_path(monkeypatch):
    """Valid CSV -> 200 {job_id,total}; polling returns completed rows
    with the full per-row schema. (INPUT-05, WEB-07)
    """
    monkeypatch.setattr("src.api.batch._dispatch_row", _fake_dispatch_ok)
    csv_bytes = _fixture_bytes("batch_sample.csv")
    with TestClient(app) as c:
        resp = c.post("/batch", files={"file": ("b.csv", csv_bytes, "text/csv")})
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["total"] == 3

        job_id = data["job_id"]
        status = c.get(f"/batch/{job_id}").json()
        assert status["status"] == "done"
        assert status["done"] == status["total"] == 3
        for row in status["rows"]:
            for key in ("row", "type", "content_preview", "prediction", "probability", "error"):
                assert key in row


def test_batch_rejects_bad_extension():
    with TestClient(app) as c:
        resp = c.post("/batch", files={"file": ("x.txt", b"a", "text/plain")})
        assert resp.status_code == 400


def test_batch_rejects_bad_header():
    with TestClient(app) as c:
        resp = c.post("/batch", files={"file": ("x.csv", b"a,b\n1,2\n", "text/csv")})
        assert resp.status_code == 400


def test_batch_rejects_too_many_rows():
    big = b"type,content\n" + b"sms,hi\n" * 501
    with TestClient(app) as c:
        resp = c.post("/batch", files={"file": ("x.csv", big, "text/csv")})
        assert resp.status_code == 400


def test_batch_rejects_oversized():
    # header + enough padding rows to exceed 1MB.
    row = b"sms," + b"a" * 200 + b"\n"
    body = b"type,content\n" + row * 6000  # ~1.2MB
    assert len(body) > 1024 * 1024
    with TestClient(app) as c:
        resp = c.post("/batch", files={"file": ("big.csv", body, "text/csv")})
        assert resp.status_code == 400
        assert "size" in resp.json()["detail"].lower() or "large" in resp.json()["detail"].lower()


def test_batch_rejects_oversized_cell():
    oversized_cell = b"a" * 6000
    body = b"type,content\nsms," + oversized_cell + b"\n"
    with TestClient(app) as c:
        resp = c.post("/batch", files={"file": ("cell.csv", body, "text/csv")})
        assert resp.status_code == 400


def test_batch_accepts_case_insensitive_header(monkeypatch):
    """Mixed-case header (Type,Content) must still be accepted — proves
    fieldnames are lowercased before row access.
    """
    monkeypatch.setattr("src.api.batch._dispatch_row", _fake_dispatch_ok)
    body = b"Type,Content\nurl,https://example.com/login\n"
    with TestClient(app) as c:
        resp = c.post("/batch", files={"file": ("mixed.csv", body, "text/csv")})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


def test_batch_rejects_empty_csv():
    body = b"type,content\n"
    with TestClient(app) as c:
        resp = c.post("/batch", files={"file": ("empty.csv", body, "text/csv")})
        assert resp.status_code == 400


def test_unknown_job_404():
    with TestClient(app) as c:
        resp = c.get("/batch/doesnotexist")
        assert resp.status_code == 404


def test_polling():
    """Directly insert a partial job into JOBS and assert the offset
    slice / status / total / done contract, deterministically (no
    dependency on background-task timing under TestClient).
    """
    import src.api.batch as batch_mod

    job_id = "test-polling-job"
    rows = [
        {
            "row": i,
            "type": "sms",
            "content_preview": f"row {i}",
            "prediction": "phishing",
            "probability": 0.5,
            "error": None,
        }
        for i in range(5)
    ]
    batch_mod.JOBS[job_id] = {
        "status": "running",
        "total": 5,
        "done": 2,
        "rows": rows,
    }
    try:
        with TestClient(app) as c:
            resp = c.get(f"/batch/{job_id}", params={"offset": 2})
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "running"
            assert data["total"] == 5
            assert data["done"] == 2
            assert data["rows"] == rows[2:]
    finally:
        batch_mod.JOBS.pop(job_id, None)


def test_per_row_error_isolation(monkeypatch):
    """One failing row must not abort the job; its error must be a
    generic message with no traceback leak. (T-08-INFO)
    """

    def flaky_dispatch(row_type: str, content: str) -> dict:
        if "boom" in content:
            raise RuntimeError("synthetic failure")
        return {"prediction": "legitimate", "probability": 0.1}

    monkeypatch.setattr("src.api.batch._dispatch_row", flaky_dispatch)
    body = b"type,content\nsms,boom trigger\nsms,all good\n"
    with TestClient(app) as c:
        resp = c.post("/batch", files={"file": ("mix.csv", body, "text/csv")})
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]
        status = c.get(f"/batch/{job_id}").json()
        assert status["status"] == "done"
        assert status["done"] == status["total"]

        failing_rows = [r for r in status["rows"] if r["error"]]
        assert len(failing_rows) == 1
        error_text = failing_rows[0]["error"]
        assert "Traceback" not in error_text
