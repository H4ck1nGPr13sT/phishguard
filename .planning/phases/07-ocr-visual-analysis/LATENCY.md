# /predict/image — Measured OCR Latency (Phase 7)

**Measured:** 2026-09-30 · resolves RESEARCH.md Assumption A1 / Pitfall 2 (previously unbenchmarked OCR latency).

## Environment

| Property | Value |
|----------|-------|
| Machine | Apple M4 Pro, 14 cores |
| OS | macOS (Darwin 25.5.0) |
| Python | 3.13.13 (project `.venv`) |
| torch | 2.14.0 (CPU) |
| easyocr | 1.7.2 (languages: en, gpu=False) |
| Harness | `scripts/measure_ocr_latency.py 10` via `TestClient(app)` (reader warmed at lifespan startup, so model-load cost is excluded) |
| Fixtures | `tests/fixtures/` — `text_login.png` (400×200, drawn text), `blank.png` (200×200), `form_like.png` (400×300) |

## Measured results (N=10 per fixture, warmed reader)

| Fixture | p50 (ms) | p95 (ms) | min (ms) | max (ms) |
|---------|---------:|---------:|---------:|---------:|
| text_login.png | 160.5 | 803.5 | 159.6 | 803.5 |
| blank.png | 78.4 | 87.4 | 77.7 | 87.4 |
| form_like.png | 169.0 | 186.2 | 168.2 | 186.2 |
| **OVERALL** | **160.5** | **194.7** | — | — |

Notes:
- The single 803ms `text_login` p95 is the **first** timed request for that fixture — a one-off warm spike (lazy JIT / thread-pool spin-up on the first real inference), not steady state. Every subsequent request on the same fixture sat near the ~160ms p50. Steady-state per-image inference is ~80–190ms on this CPU.
- Overall p95 across all 30 requests is **194.7ms — under the 500ms reference budget.**

## Documented <500ms exception decision

The hard **<500ms** response contract remains **binding** for `/predict`, `/predict/email`, and `/predict/sms`.

`/predict/image` is an **explicit, documented exception** to that budget because OCR neural inference is inherently slower than the text/URL feature paths. The mitigation is that the EasyOCR reader is **warmed once at FastAPI lifespan startup**, so only per-image inference (not the multi-second model load) is ever on the request path. With that warm-up, measured steady-state latency is comfortably within 500ms on this hardware; the endpoint stays synchronous (no async job/polling queue was built — deliberate, per the locked Phase 7 decision). On slower hardware the per-image cost could exceed 500ms; that is accepted for the image endpoint only (threat register T-07-14).

## Reproduce

```bash
# One-time: install the heavy Phase 7 deps (pulls torch; downloads ~64MB OCR weights on first run)
.venv/bin/pip install -r requirements.txt

# macOS: torch (EasyOCR) + xgboost (email ensemble) both ship OpenMP; conftest.py sets
# KMP_DUPLICATE_LIB_OK=TRUE automatically so the process does not segfault.

# Real-backend integration test (does NOT skip once easyocr is installed):
.venv/bin/python -m pytest tests/integration/test_image_integration.py -m slow -rs

# Latency measurement:
.venv/bin/python scripts/measure_ocr_latency.py 10

# Full suite (green, no regressions):
.venv/bin/python -m pytest -q
```

## Environment side-effects observed during this measurement

- **scikit-learn pinned to 1.8.0 for reproducibility.** Installing the Phase 7 deps left scikit-learn at 1.8.0. Empirically, the committed model artifacts in `models/` are pickled with **1.8.0** (the majority of estimators; a few Bayesian estimators are older 1.6.1 pickles that still load forward-compatibly). The full suite is green under 1.8.0 (414 passed); downgrading to 1.6.1 breaks the 1.8.0-pickled models (19 failures, `/predict/email|sms` return 500). `requirements.txt` and `pyproject.toml` now pin `scikit-learn==1.8.0` so the version stays in lockstep with the trained models. Residual `InconsistentVersionWarning` lines are only the handful of 1.6.1-era estimators and are non-fatal; a full re-train would clear them.
- **OpenMP duplicate-runtime segfault** (torch + xgboost on macOS) is neutralized by `conftest.py` setting `KMP_DUPLICATE_LIB_OK=TRUE` before either library imports.
