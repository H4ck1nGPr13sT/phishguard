---
phase: 07-ocr-visual-analysis
plan: 05
subsystem: testing
tags: [integration-test, ocr, easyocr, latency, benchmark, dependency-isolation]

# Dependency graph
requires:
  - phase: 07-ocr-visual-analysis
    provides: "EasyOCRBackend/load_and_ocr (07-01), visual features (07-02), ContentType.IMAGE (07-03), POST /predict/image (07-04)"
provides:
  - "tests/integration/test_image_integration.py: real-EasyOCR end-to-end test (importorskip-guarded, @pytest.mark.slow)"
  - "scripts/measure_ocr_latency.py: p50/p95 latency harness for /predict/image"
  - "conftest.py: OpenMP duplicate-runtime guard (KMP_DUPLICATE_LIB_OK) + 'slow' marker registration"
  - ".planning/phases/07-ocr-visual-analysis/LATENCY.md: measured latency + documented <500ms exception"
affects: []

# Tech tracking
tech-stack:
  added:
    - "easyocr 1.7.2 (pulls torch 2.14.0, CPU), opencv-python-headless 5.0.0.93 — installed into .venv (user-authorized heavy install)"
  patterns:
    - "Import-isolation verified in a fresh subprocess (immune to sys.modules pollution by other tests in the session)"
    - "OpenMP dual-runtime (torch+xgboost) neutralized process-wide via conftest.py before any heavy import"

key-files:
  created:
    - tests/integration/test_image_integration.py
    - scripts/measure_ocr_latency.py
    - conftest.py
    - .planning/phases/07-ocr-visual-analysis/LATENCY.md
  modified:
    - src/features/ocr/backend.py
    - tests/features/test_extractors_image.py
---

# Plan 07-05 Summary — Real-OCR Integration + Latency Measurement

## What was built

- **Real-backend integration test** (`tests/integration/test_image_integration.py`): constructs a real `EasyOCRBackend`, extracts text from `text_login.png` (asserts recognizable tokens), and drives `/predict/image` end-to-end for a text image and a blank image. Guarded by `pytest.importorskip("easyocr"/"imagehash"/"cv2")` and `@pytest.mark.slow` so it skips cleanly where the heavy deps are absent.
- **Latency harness** (`scripts/measure_ocr_latency.py`): times `/predict/image` via `TestClient(app)` with the reader warmed at lifespan startup; reports p50/p95 per fixture and overall; flags the Null-backend path; always exits 0.
- **`LATENCY.md`**: records measured numbers and the documented <500ms exception.

## Measured latency (Apple M4 Pro, CPU torch, N=10/fixture, warmed reader)

| Fixture | p50 | p95 |
|---------|----:|----:|
| text_login.png | 160.5 ms | 803.5 ms (first-call warm spike) |
| blank.png | 78.4 ms | 87.4 ms |
| form_like.png | 169.0 ms | 186.2 ms |
| **Overall** | **160.5 ms** | **194.7 ms** |

Overall p95 194.7ms is **under** the 500ms reference budget. `/predict/image` stays synchronous with a startup-warmed reader (documented exception; hard budget preserved for url/email/sms).

## Bugs the real backend surfaced (and fixes)

1. **PIL.Image not accepted by EasyOCR** — `EasyOCRBackend.read_text` passed a `PIL.Image` straight to `reader.readtext`, which only accepts a path/bytes/ndarray, raising `ValueError` → endpoint returned 400 for every real request. Fixed by converting PIL → RGB numpy array in `read_text` (`_to_ocr_input`). The fake-backend unit tests could not catch this — exactly the failure class 07-05 exists to find.
2. **OpenMP dual-runtime segfault** — with easyocr installed, torch (EasyOCR) and xgboost (email ensemble) both load OpenMP; the full suite segfaulted on macOS. Fixed by `conftest.py` setting `KMP_DUPLICATE_LIB_OK=TRUE` before any heavy import.
3. **Isolation test false failure** — `test_extractors_module_imports_without_torch_easyocr_cv2` asserted torch absence from the shared `sys.modules`; once torch is installed, spaCy's `thinc` backend imports it transitively (via `text_features → spacy → thinc`), unrelated to Phase 7. Narrowed the assertion to Phase 7's own deps (easyocr/cv2/imagehash) and moved the check into a fresh subprocess. Renamed to `test_extractors_module_imports_without_easyocr_cv2`.

## Verification

- Integration test: **3 passed** (`-m slow`, real EasyOCR).
- Full suite: **414 passed, 1 skipped** (`.venv/bin/python -m pytest -q`), no segfault, no regressions.

## Deviations / observations

- **scikit-learn upgraded 1.6.1 → 1.8.0** as a side-effect of the heavy install; persisted models (trained under 1.6.1) now emit `InconsistentVersionWarning` but all model-backed tests still pass. Recorded in LATENCY.md as a known, non-blocking reproducibility note (a tighter `scikit-learn` pin in `requirements.txt` is the follow-up if strict reproducibility is required).
- Plan 07-05 was marked `autonomous: false` (human-verify checkpoint). The heavy ~2GB install and full real-OCR execution were explicitly authorized by the user via an interactive prompt in-session; the measurement was taken and recorded, satisfying the checkpoint.

## Requirements

- **INPUT-04** (image upload) and **INPUT-06** (OCR extraction) exercised end-to-end with the real backend.
