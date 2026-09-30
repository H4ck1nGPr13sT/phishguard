#!/usr/bin/env python3
"""Empirical latency harness for POST /predict/image (Phase 7).

Times the ``/predict/image`` endpoint on the deterministic fixture images and
reports p50/p95 per fixture plus an overall summary. Uses ``TestClient(app)`` as
a context manager so the FastAPI lifespan runs and the EasyOCR reader is warmed
BEFORE timing begins — this excludes one-time model-load cost from the measured
per-request numbers (only per-image inference is on the request path).

Resolves RESEARCH.md Assumption A1 / Pitfall 2 (unbenchmarked OCR latency) with a
measurement rather than a guess. If the OCR backend fell back to ``NullOCRBackend``
(easyocr absent), the printed numbers reflect the Null path and are explicitly
flagged as NOT representative of real OCR inference.

Usage:
    .venv/bin/python scripts/measure_ocr_latency.py [N]

    N = requests per fixture (default 10).

Always exits 0 — this is a measurement tool, not a test gate.
"""

import statistics
import sys
import tempfile
import time
from pathlib import Path

# Ensure project root on path when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from src.api.main import app, ml_models  # noqa: E402
from tests.fixtures.make_fixtures import generate_all  # noqa: E402

FIXTURES = ["text_login.png", "blank.png", "form_like.png"]


def _percentile(values, pct):
    """Nearest-rank percentile using stdlib only (no numpy dependency)."""
    if not values:
        return float("nan")
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return ordered[k]


def main():
    n = 10
    if len(sys.argv) > 1:
        try:
            n = max(1, int(sys.argv[1]))
        except ValueError:
            print(f"Ignoring non-integer N argument {sys.argv[1]!r}; using N=10")

    tmp = Path(tempfile.mkdtemp(prefix="phase7_latency_"))
    generate_all(str(tmp))

    print(f"OCR latency harness — {n} request(s) per fixture")
    print("=" * 60)

    with TestClient(app) as client:
        # Lifespan has run; report which backend is actually in use.
        backend = ml_models.get("ocr_backend")
        backend_name = type(backend).__name__ if backend is not None else "None"
        is_null = backend_name in ("NullOCRBackend", "NoneType")
        print(f"Active OCR backend: {backend_name}")
        if is_null:
            print(
                "WARNING: NullOCRBackend active (easyocr not installed) — timings "
                "reflect the Null path and are NOT representative of real OCR "
                "inference."
            )
        print("-" * 60)

        overall = []
        for fixture in FIXTURES:
            path = tmp / fixture
            if not path.exists():
                continue
            data = path.read_bytes()
            times_ms = []
            for _ in range(n):
                t0 = time.perf_counter()
                resp = client.post(
                    "/predict/image",
                    files={"file": (fixture, data, "image/png")},
                )
                dt_ms = (time.perf_counter() - t0) * 1000.0
                if resp.status_code == 200:
                    times_ms.append(dt_ms)
                    overall.append(dt_ms)
                else:
                    print(f"  [{fixture}] non-200 ({resp.status_code}) — excluded")
            if times_ms:
                print(
                    f"{fixture:16s}  p50={_percentile(times_ms, 50):8.1f} ms   "
                    f"p95={_percentile(times_ms, 95):8.1f} ms   "
                    f"min={min(times_ms):8.1f}  max={max(times_ms):8.1f}  n={len(times_ms)}"
                )

        print("-" * 60)
        if overall:
            print(
                f"{'OVERALL':16s}  p50={_percentile(overall, 50):8.1f} ms   "
                f"p95={_percentile(overall, 95):8.1f} ms   "
                f"mean={statistics.mean(overall):8.1f}  n={len(overall)}"
            )
            budget = 500.0
            p95 = _percentile(overall, 95)
            verdict = "UNDER" if p95 < budget else "OVER"
            print(
                f"\n/predict/image overall p95 is {verdict} the {budget:.0f}ms reference "
                f"budget (image endpoint is the documented sync exception)."
            )
        else:
            print("No successful timings collected.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
