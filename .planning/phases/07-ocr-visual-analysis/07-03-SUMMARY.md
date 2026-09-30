---
phase: 07-ocr-visual-analysis
plan: 03
subsystem: features
tags: [dispatch, content-type, image-features, integration-seam]

# Dependency graph
requires:
  - phase: 07-ocr-visual-analysis
    provides: "extract_image_features(image_bytes, ocr_backend) — all-numeric, constant-length (Plans 07-01/07-02)"
provides:
  - "src/features/extractors.py: ContentType.IMAGE enum member + image dispatch branch in extract_features()"
  - "src/features/extractors.py: get_ocr_backend() module-level singleton getter (mirrors get_text_extractor())"
affects: [07-04-api-endpoint]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy import of extract_image_features and resolve_ocr_backend INSIDE the ContentType.IMAGE branch only (never at module top level) — preserves the torch/cv2-free module-load contract for src.features.extractors"
    - "Singleton-on-first-use OCR backend getter (get_ocr_backend), mirroring the existing get_text_extractor() pattern from Phase 6"

key-files:
  created:
    - tests/features/test_extractors_image.py
  modified:
    - src/features/extractors.py

key-decisions:
  - "Explicit TypeError (not silent str->bytes coercion) when non-bytes content is dispatched as ContentType.IMAGE, per the plan's threat mitigation T-07-06 — images are binary-only and ambiguous-as-text inputs must fail loudly."
  - "detect_content_type() auto-detection left unchanged; images are never auto-classified — they always arrive explicitly typed as ContentType.IMAGE from the API endpoint (Plan 07-04), since raw bytes are ambiguous versus .eml bytes."

requirements-completed: [INPUT-04, INPUT-06, INPUT-07]

# Metrics
duration: 3min
completed: 2026-09-30
---

# Phase 7 Plan 03: Unified Extractor Image Dispatch Summary

**ContentType.IMAGE registered as a first-class content type in the unified extractor, with a lazy-import dispatch branch routing image bytes to extract_image_features — the single integration seam connecting Plans 07-01/07-02's image feature module to Plan 07-04's API endpoint, keeping src.features.extractors torch/cv2-free at module load.**

## Performance

- **Duration:** ~3 min (measured from read to commit; excludes read/planning time)
- **Started:** 2026-09-30T15:16:00+02:00 (approx, first edit)
- **Completed:** 2026-09-30T15:19:03+02:00 (Task 1 commit)
- **Tasks:** 1 completed
- **Files modified:** 2 (1 modified, 1 created)

## Accomplishments
- `ContentType.IMAGE = "image"` added to the enum in `src/features/extractors.py`, alongside URL/EMAIL/EMAIL_FILE/SMS.
- `extract_features()` gained an `elif content_type == ContentType.IMAGE:` branch: validates `content` is `bytes` (raises `TypeError` otherwise — no silent coercion, closes threat T-07-06), lazily imports `extract_image_features` from `src.features.image_features` and resolves an OCR backend via the new `get_ocr_backend()` singleton getter, calls `extract_image_features(content, backend)`, and sets `features['content_type'] = 3`.
- `get_ocr_backend()` added as a module-level singleton getter mirroring `get_text_extractor()` — lazily imports `resolve_ocr_backend` from `src.features.ocr` inside the function body (never at module top level), caching the resolved backend (`EasyOCRBackend` or `NullOCRBackend`) across calls.
- `detect_content_type()` left unchanged for auto-detection; a docstring note clarifies images are never auto-classified — they arrive explicitly typed from the API endpoint.
- Verified empirically (not just by code inspection): `torch`, `easyocr`, and `cv2` are absent from `sys.modules` both immediately after `from src.features.extractors import ContentType` and after `importlib.reload()` of the module — the dependency-isolation contract holds.
- 4 new unit tests in `tests/features/test_extractors_image.py`: dispatch correctness (content_type==3, `ocr_text_*`/`visual_*` keys present, full all-numeric contract check across every returned key), `TypeError` on `str` + `ContentType.IMAGE`, torch/easyocr/cv2-free module import (including a reload check), and a visual-key-set sanity check.
- Full project test suite: 403 passed, 2 skipped (up from 399 passed, 2 skipped before this plan — the +4 delta is exactly this plan's new tests), no regressions, still fully torch-free.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ContentType.IMAGE and image dispatch branch with tests** - `b4b9b35` (feat)

_Single-task plan; no TDD gate required (plan frontmatter type is `execute`, not a per-task `tdd="true"` task) — implementation and tests were written and verified together before the one commit._

## Files Created/Modified
- `src/features/extractors.py` - Added `ContentType.IMAGE`, `get_ocr_backend()` singleton getter, and the IMAGE dispatch branch in `extract_features()`; updated docstrings (content_type mapping table, `detect_content_type` auto-detection note)
- `tests/features/test_extractors_image.py` - `FakeOCRBackend` test double (mirrors the one in `test_image_features.py`) + 4 unit tests covering the dispatch branch, TypeError guard, and import isolation

## Decisions Made
- Used a module-level singleton getter (`get_ocr_backend`) rather than resolving the backend fresh on every call, matching the project's existing `get_text_extractor()` pattern from Phase 6 and avoiding repeated (and, once EasyOCR is actually installed, expensive) backend resolution per request.
- Kept the `TypeError` message explicit and actionable ("ContentType.IMAGE requires bytes content...") rather than a generic type error, so API-layer callers (Plan 07-04) get a clear signal if they mishandle multipart/form upload decoding.

## Deviations from Plan

None - plan executed exactly as written. The single task's action items (enum member, dispatch branch with lazy imports, TypeError guard, unchanged auto-detection, test file with the three specified assertion groups) were all implemented as specified in `07-03-PLAN.md`.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. `easyocr`/`torch`/`cv2` remain uninstalled in this venv (per the mandatory dependency-isolation constraint carried over from Plans 07-01/07-02); `get_ocr_backend()` will resolve to `NullOCRBackend` in the current environment (empty-string OCR text, but a fully valid all-numeric feature dict via the existing graceful-degradation paths in `image_features.py`).

## Next Phase Readiness
- `extract_features(image_bytes, ContentType.IMAGE)` is now a stable, tested public entry point ready for Plan 07-04's `/predict/image` API endpoint to call directly, exactly mirroring how the endpoint would call `extract_features(email_bytes, ContentType.EMAIL_FILE)` or `extract_features(sms_text, ContentType.SMS)`.
- `get_ocr_backend()` is ready to be reused (or wired into a FastAPI `lifespan` warm-load step per RESEARCH.md Pattern 4) by Plan 07-04, once `easyocr`/`torch` are actually installed for end-to-end OCR.
- No blockers. Full suite remains torch-free (403 passed, 2 skipped) after this plan's changes.

---
*Phase: 07-ocr-visual-analysis*
*Completed: 2026-09-30*

## Self-Check: PASSED

Verified: `src/features/extractors.py` exists and contains `ContentType.IMAGE`, `get_ocr_backend`, and the IMAGE dispatch branch (grep-confirmed). `tests/features/test_extractors_image.py` exists on disk (57 lines by initial write, 4 tests, all passing per pytest run above). Commit hash `b4b9b35` confirmed present via `git log -1 --format=%aI b4b9b35` (2026-09-30T15:19:03+02:00).
