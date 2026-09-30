---
phase: 07-ocr-visual-analysis
plan: 04
subsystem: api
tags: [fastapi, image-upload, ocr, aggregation, multi-paradigm, api-endpoint]

# Dependency graph
requires:
  - phase: 07-ocr-visual-analysis
    provides: "load_and_ocr / extract_visual_features (07-01/07-02), ContentType.IMAGE dispatch + get_ocr_backend (07-03)"
  - phase: 06-email-sms-support
    provides: "extract_email_features schema and email_ensemble model; EmailSMSResponse contract"
  - phase: 05
    provides: "MultiParadigmAggregator, RuleEngine.evaluate(features, raw_url=...)"
provides:
  - "POST /predict/image: upload-validated, in-memory, OCR+visual combined phishing verdict"
  - "src/api/main.py: lifespan warm-load of OCR backend into ml_models['ocr_backend'] with NullOCRBackend fallback"
  - "src/api/models.py: EmailSMSResponse.content_type=='image' + visual_closest_brand/visual_hash_distance diagnostics; HealthResponse.ocr_backend_loaded"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "OCR->ML bridge: extract_email_features(b'\\n' + ocr_text.encode()) reuses the Phase 6 trained schema instead of ocr_text_* keys, with the leading blank line preventing colon-containing OCR lines from being mis-parsed as RFC-822 headers"
    - "Visual signal occupies the aggregator's third (bayesian) paradigm slot via a small documented _visual_signal_probability() weighting helper — no new aggregation logic"
    - "Startup warm-up with hard fallback (resolve_ocr_backend() + warm_up() wrapped in try/except -> NullOCRBackend) so lifespan never crashes regardless of environment"

key-files:
  created:
    - tests/test_api_image.py
  modified:
    - src/api/models.py
    - src/api/main.py
    - src/api/endpoints.py
    - tests/test_api.py

key-decisions:
  - "Required-models check for /predict/image includes ocr_backend, email_ensemble, rule_engine, aggregator (superset of the plan's minimum ocr_backend+email_ensemble) since all four are dereferenced in the handler — avoids a KeyError->500 path if any is ever absent."
  - "Rule-engine call wrapped defensively (try/except -> empty-rules fallback dict) per plan instruction, since email_features is not the URL-feature schema RuleEngine was originally built against."
  - "_visual_signal_probability weighting (0.7 brand-flag / 0.15 edge-density / 0.15 color-concentration) documented as tunable/unvalidated, consistent with RESEARCH.md Pitfall 5's stance on BRAND_MATCH_THRESHOLD."
  - "Updated a pre-existing test (tests/test_api.py::test_root_contains_service_info) asserting API version=='3.0.0' to '4.0.0' — a direct, in-scope consequence of this plan's explicit instruction to bump the API version, not a scope-creep fix."

requirements-completed: [INPUT-04, INPUT-06, INPUT-07]

# Metrics
duration: ~25min
completed: 2026-09-30
---

# Phase 7 Plan 04: POST /predict/image API Endpoint Summary

**New `POST /predict/image` endpoint: validates uploads (extension allowlist + 8MB cap) before any decode, runs OCR exactly once via `load_and_ocr`, feeds the OCR text into the existing Phase 6 email-text model on its trained schema, and combines OCR-text + rule keyword-matching + visual brand/layout signal through the unmodified `MultiParadigmAggregator` — closing the loop on INPUT-04/06/07 and ROADMAP Success Criterion 5, entirely in-memory and torch-free in the test suite.**

## Accomplishments

**Task 1 — Response model extension + OCR warm-up at startup (commit `cb66883`)**
- `EmailSMSResponse.content_type` extended to `Literal["email", "sms", "image"]`.
- Added `visual_closest_brand: Optional[str]` and `visual_hash_distance: Optional[float]` diagnostic fields to `EmailSMSResponse` (None for email/sms responses).
- Added `ocr_backend_loaded: bool` to `HealthResponse`; `/health` now reports it.
- `src/api/main.py` lifespan resolves `ml_models["ocr_backend"] = resolve_ocr_backend()` after the Phase 6 email/SMS load block, then calls `warm_up()` if present. Wrapped in try/except so ANY failure (offline env, model-download failure) falls back to `NullOCRBackend()` — startup never crashes (T-07-12).

**Task 2 — `POST /predict/image` endpoint (commit `2885e6f`)**
- Validation order: `.png/.jpg/.jpeg` extension allowlist (lowercased) → 8MB size cap → required-models check (`ocr_backend`, `email_ensemble`, `rule_engine`, `aggregator`) → decode. All rejections before decode return HTTP 400; missing models return 503.
- Single OCR pass via `load_and_ocr(contents, ml_models["ocr_backend"])`; a `ValueError` (corrupt bytes or decompression-bomb pixel ceiling) maps to HTTP 400 "Invalid image".
- ML text signal: `extract_email_features(b"\n" + ocr_text.encode("utf-8"))` feeds `email_ensemble.predict_proba` — the leading blank line keeps the entire OCR text in the email BODY so colon-containing lines (e.g. "Password: ...") are never mis-parsed as headers and dropped.
- Rule signal: `rule_engine.evaluate(email_features, raw_url=ocr_text)`, defensively wrapped — any exception falls back to an empty-rules result instead of a 500.
- Visual signal: `extract_visual_features(image)` mapped to `[0,1]` via a new `_visual_signal_probability()` helper (brand-similarity-flag dominant, edge-density/color-concentration as minor nudges), occupying the aggregator's `bayesian_result` slot.
- Aggregation via the existing `ml_models["aggregator"].aggregate(ml_result, rule_result, bayesian_result)` — no new aggregation logic.
- Response built with `content_type="image"`, `feature_count=len(email_features)+len(visual_dict)`, `visual_closest_brand`/`visual_hash_distance` surfaced from the visual step.
- Root endpoint list and API version bumped to `4.0.0` (`src/api/main.py` FastAPI app + `src/api/endpoints.py` root endpoint).
- Verified empirically: importing `src.api.endpoints` loads none of `easyocr`/`torch`/`cv2`/`imagehash` into `sys.modules` (dependency isolation preserved).

**Task 3 — API tests (commit `2a72096`)**
- `tests/test_api_image.py` (7 tests, all passing, torch-free):
  - `test_wrong_extension_rejected` — `.txt` upload → 400.
  - `test_oversized_upload_rejected_before_decode` — >8MB non-image bytes → 400 with the size message (proves the cap fires before decode).
  - `test_corrupt_image_rejected` — `tests/fixtures/truncated.png` → 400 "Invalid image".
  - `test_decompression_bomb_rejected` — `PIL.Image.MAX_IMAGE_PIXELS` monkeypatched low, small crafted PNG → 400.
  - `test_happy_path_deterministic` — monkeypatched `FakeOCRBackend` + `FixedProbaEnsemble` (fixed `[[0.1, 0.9]]`) injected into the shared `ml_models` dict; asserts HTTP 200 deterministically, `content_type=="image"`, valid probability/confidence ranges, `feature_count>0`. No 200-or-503 escape hatch.
  - `test_ocr_responsiveness_phishing_text_scores_higher_than_blank` — a `TextDrivenFakeEnsemble` whose `predict_proba` is a monotonic function of the real `extract_email_features` output magnitude; asserts phishing-text OCR output yields a strictly higher `final_probability` than blank OCR output.
  - `test_colon_line_body_preservation` — OCR text with a colon on the first line (`"Password: enter now to verify account suspended"`) still yields a strictly higher probability than blank, proving the `b"\n"` prepend keeps it in the email body.
- Fixed a resulting regression in a pre-existing test (`tests/test_api.py::test_root_contains_service_info`) that hardcoded `version == "3.0.0"` — updated to `"4.0.0"` to match this plan's explicit version bump.
- Full suite: **410 passed, 2 skipped**, torch-free (`easyocr`, `torch`, `cv2` confirmed absent from the venv via `importlib.util.find_spec`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pre-existing root-endpoint test asserted stale API version**
- **Found during:** Task 3 full-suite run
- **Issue:** `tests/test_api.py::TestRootEndpoint::test_root_contains_service_info` hardcoded `assert data["version"] == "3.0.0"`. This plan's Task 2 explicitly bumps the API version to `"4.0.0"` per its `<action>` instructions, so the assertion broke as a direct, in-scope consequence.
- **Fix:** Updated the assertion to `"4.0.0"` with an updated comment.
- **Files modified:** `tests/test_api.py`
- **Commit:** `2a72096`

No other deviations — plan executed as written, including the OCR->ML bridge design (BLOCKER 3), the security validation ordering (ASVS V5/V12), and the dependency-isolation/latency-exception constraints.

## Known Stubs

None. `_visual_signal_probability`'s weighting is explicitly documented as tunable/unvalidated (mirroring `BRAND_MATCH_THRESHOLD`'s existing documented-uncertainty pattern from Plan 07-02) rather than a stub — it is a real, functioning heuristic combiner, not a placeholder.

## Threat Flags

None. All new upload-boundary surface (`POST /predict/image`) is exactly the trust boundary the plan's `<threat_model>` (T-07-08 through T-07-12) already covers, and all listed mitigations (size cap before decode, extension allowlist + `Image.verify()`, in-memory-only processing, decompression-bomb guard, OCR warm-up fallback) are implemented and covered by `tests/test_api_image.py`.

## Self-Check: PASSED

- `src/api/endpoints.py` contains `/predict/image` — FOUND (route registered: verified via `router.routes`).
- `src/api/main.py` contains `ocr_backend` — FOUND.
- `src/api/models.py` `content_type` accepts `"image"` — FOUND.
- `tests/test_api_image.py` exists, 221 lines added, 7 tests — FOUND, all passing.
- Commit `cb66883` — FOUND (`git log`).
- Commit `2885e6f` — FOUND (`git log`).
- Commit `2a72096` — FOUND (`git log`).
- Full suite: 410 passed, 2 skipped, torch-free — CONFIRMED.
