---
phase: 07-ocr-visual-analysis
plan: 01
subsystem: features
tags: [ocr, easyocr, pillow, image-processing, feature-extraction, tdd]

# Dependency graph
requires:
  - phase: 06-email-sms-support
    provides: "TextFeatureExtractor / get_text_extractor() singleton pattern and text_{k} prefixing convention (extractors.py)"
provides:
  - "src/features/ocr/backend.py: OCRBackend Protocol, NullOCRBackend, lazy EasyOCRBackend, resolve_ocr_backend() factory"
  - "src/features/image_features.py: _load_and_validate_image, _preprocess_for_ocr, load_and_ocr(), extract_image_features()"
  - "Deterministic Pillow-only test fixtures (text_login.png, blank.png, truncated.png, form_like.png)"
  - "Phase 7 dependency pins in requirements.txt (easyocr, imagehash, opencv-python-headless<5, pytesseract)"
affects: [07-02-visual-features, 07-03, 07-04-api-endpoint]

# Tech tracking
tech-stack:
  added: [easyocr>=1.7.2 (requirements-only, not installed), imagehash>=4.3.2 (requirements-only), "opencv-python-headless>=4.12.0,<5.0.0 (requirements-only)", pytesseract>=0.3.13 (requirements-only)]
  patterns:
    - "Pluggable lazy-loaded backend (OCRBackend Protocol) — heavy dep imported only inside _get_reader(), never at module top level"
    - "Single OCR entry point (load_and_ocr) reused by feature extraction and (later) the API endpoint to avoid double-OCR"
    - "Unconditional extract_all_features(ocr_text) call, even on empty string, to guarantee constant feature-dict key count"

key-files:
  created:
    - src/features/ocr/__init__.py
    - src/features/ocr/backend.py
    - src/features/image_features.py
    - tests/fixtures/__init__.py
    - tests/fixtures/make_fixtures.py
    - tests/fixtures/text_login.png
    - tests/fixtures/blank.png
    - tests/fixtures/truncated.png
    - tests/fixtures/form_like.png
    - tests/features/test_image_features.py
  modified:
    - requirements.txt

key-decisions:
  - "OCR backend uses structural typing.Protocol (not ABC) so any object with a compatible read_text(image) method satisfies it — makes FakeOCRBackend test doubles trivial to inject with zero inheritance boilerplate."
  - "_preprocess_for_ocr is a deliberate no-op/pass-through in this plan (cv2 denoise/contrast deferred to Plan 07-02) to keep the OCR-text path fully torch/cv2-free."
  - "load_and_ocr established as the single OCR call site now, ahead of Plan 07-04's API endpoint, so double-OCR is structurally prevented rather than relying on caller discipline."

patterns-established:
  - "Pattern: lazy heavy-dependency backend behind a Protocol interface + factory (resolve_ocr_backend), mirroring get_text_extractor() singleton style from Phase 6."
  - "Pattern: fixture generation script (tests/fixtures/make_fixtures.py) using only already-installed deps (Pillow), with a generate_all(target_dir) function and __main__ guard, committing the generated PNGs to the repo."

requirements-completed: [INPUT-06]

# Metrics
duration: 4min
completed: 2026-09-30
---

# Phase 7 Plan 01: OCR Backend & Image Feature Extraction Summary

**OCR backend abstraction (mockable, lazy easyocr import) plus extract_image_features() that reuses the existing Phase 6 TextFeatureExtractor pipeline on OCR-derived text — fully torch-free in the fast test suite.**

## Performance

- **Duration:** ~4 min (measured from first to last task commit; excludes read/planning time)
- **Started:** 2026-09-30T14:59:42+02:00 (Task 1 commit)
- **Completed:** 2026-09-30T15:03:27+02:00 (Task 3 GREEN commit)
- **Tasks:** 3 completed
- **Files modified:** 10 (1 modified, 9 created)

## Accomplishments
- `src/features/ocr/backend.py` implements `OCRBackend` (Protocol), `NullOCRBackend`, `EasyOCRBackend` (lazy `_get_reader()`), and `resolve_ocr_backend()` — importing `src.features.ocr` never requires torch/easyocr installed (verified empirically: `ModuleNotFoundError: No module named 'easyocr'` confirmed absent from the environment, and the module still imports cleanly).
- `src/features/image_features.py` implements the single OCR entry point (`load_and_ocr`) and `extract_image_features()`, which unconditionally feeds OCR text into `get_text_extractor().extract_all_features()` and prefixes `ocr_text_*` — mirroring `extract_email_features`'s `text_*` convention exactly.
- Decompression-bomb protection: `Image.DecompressionBombWarning` is promoted to an exception via `warnings.simplefilter("error", ...)` and mapped to `ValueError`, with `Image.MAX_IMAGE_PIXELS` left enabled (never disabled) — closes threat T-07-01.
- Deterministic Pillow-only fixture generator (`tests/fixtures/make_fixtures.py`) produces 4 PNGs used by the unit tests, committed to the repo.
- 5 new unit tests, all passing with a `FakeOCRBackend` test double (no easyocr/torch/cv2/imagehash import anywhere in the test file or its production dependencies).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Phase 7 dependencies to requirements.txt** - `e91a5fb` (feat)
2. **Task 2: Create OCR backend subpackage and test fixtures** - `5dac400` (feat)
3. **Task 3: Implement extract_image_features OCR-text path with unit tests (TDD)**
   - RED: `2ac0343` (test) — failing tests committed first, confirmed `ModuleNotFoundError` before implementation existed
   - GREEN: `4334919` (feat) — implementation + test-value fix, all 5 tests pass

_TDD task (Task 3) produced two commits (test → feat) per the RED/GREEN gate. No REFACTOR commit was needed — implementation matched the interface contract on first pass._

## Files Created/Modified
- `requirements.txt` - Added Phase 7 section (easyocr, imagehash, opencv-python-headless<5.0.0, pytesseract) with lower-bound pins
- `src/features/ocr/__init__.py` - Re-exports OCRBackend, NullOCRBackend, EasyOCRBackend, resolve_ocr_backend
- `src/features/ocr/backend.py` - OCR backend Protocol + implementations; easyocr imported only inside `EasyOCRBackend._get_reader()`
- `src/features/image_features.py` - `_load_and_validate_image`, `_preprocess_for_ocr`, `load_and_ocr`, `extract_image_features` (with a marked insertion point for Plan 07-02's visual features)
- `tests/fixtures/make_fixtures.py` - Pillow-only fixture generator (`generate_all(target_dir)` + `__main__` guard)
- `tests/fixtures/__init__.py` - Empty, enables pytest import of the fixtures package
- `tests/fixtures/text_login.png`, `blank.png`, `truncated.png`, `form_like.png` - Generated deterministic fixtures
- `tests/features/test_image_features.py` - `FakeOCRBackend` test double + 5 unit tests covering the `<behavior>` block

## Decisions Made
- Used `typing.Protocol` (with `@runtime_checkable`) rather than an ABC for `OCRBackend`, matching the plan's interface spec and keeping test-double injection dependency-free.
- Kept `_preprocess_for_ocr` a pure pass-through in this plan per the plan's explicit instruction (cv2 preprocessing deferred to Plan 07-02), preserving the torch/cv2-free constraint for this plan's unit tests.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected ocr_char_count expected test value**
- **Found during:** Task 3 GREEN phase, first test run
- **Issue:** The plan's `<behavior>` block specified `ocr_char_count == 24` for the string `"URGENT verify your account"`, but `len("URGENT verify your account")` is actually 26 (verified via `python3 -c "print(len(...))"`). The RED test (committed in `2ac0343`) had copied the plan's incorrect example value verbatim.
- **Fix:** Corrected the test assertion from `24` to `26` with an inline comment showing the `len()` computation; `extract_image_features`'s implementation (`float(len(ocr_text))`) was correct from the start and required no change.
- **Files modified:** tests/features/test_image_features.py
- **Verification:** `.venv/bin/python -m pytest tests/features/test_image_features.py -v` — all 5 tests pass
- **Committed in:** `4334919` (Task 3 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug — incorrect example value in plan's behavior spec, carried into RED test)
**Impact on plan:** Trivial test-assertion correction; no production code or architectural impact.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. Note for a future plan/session: `easyocr`/`torch` are declared in `requirements.txt` but deliberately NOT installed in this plan's venv (per the mandatory dependency-isolation constraint); installing them is required before `EasyOCRBackend` can be exercised end-to-end (Plan 07-04 or later), and per 07-RESEARCH.md Pitfall 3, EasyOCR's first-ever `Reader` construction will download ~64MB+ of model weights over the network.

## Next Phase Readiness
- `extract_image_features(image_bytes, ocr_backend)` and `load_and_ocr(image_bytes, ocr_backend)` are stable, documented public entry points ready for Plan 07-02 (visual features — perceptual hash + layout/color heuristics) to merge into via the marked insertion point in `image_features.py`, and for Plan 07-04 (API endpoint) to call directly.
- `resolve_ocr_backend()` is ready to be wired into a FastAPI `lifespan` warm-load step in a later plan (Pattern 4 in 07-RESEARCH.md), once `easyocr`/`torch` are actually installed.
- No blockers. The fast unit suite (393 passed, 1 skipped) remains fully torch-free after this plan's changes.

---
*Phase: 07-ocr-visual-analysis*
*Completed: 2026-09-30*

## Self-Check: PASSED

All 11 claimed files found on disk; all 4 claimed commit hashes (e91a5fb, 5dac400, 2ac0343, 4334919) found in `git log --oneline --all`.
