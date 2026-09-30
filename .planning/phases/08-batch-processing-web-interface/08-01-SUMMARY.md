---
phase: 08-batch-processing-web-interface
plan: 01
subsystem: testing
tags: [pytest, fastapi, testclient, tdd, wave0]

# Dependency graph
requires: []
provides:
  - "tests/test_web_ui.py: executable WEB-01/02/03/08 + CSP/security-header + Swagger-survival + root-move contracts"
  - "tests/test_batch_api.py: executable INPUT-05/WEB-07 batch upload/polling/isolation contracts"
  - "tests/fixtures/batch_sample.csv: valid type,content sample (url/sms/email rows) reused as shipped static/sample.csv"
  - "monkeypatch seam contract: src.api.batch._dispatch_row (string path) for per-row dispatch stubbing"
affects: [08-02, 08-03, 08-04, 08-05, 08-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wave 0 TDD scaffolding: RED-by-design test files precede implementation plans; verify step is collect-only, not pass"
    - "Monkeypatch via dotted string path (monkeypatch.setattr('module.path', fn)) so tests collect cleanly before the target module exists"

key-files:
  created:
    - tests/test_web_ui.py
    - tests/test_batch_api.py
    - tests/fixtures/batch_sample.csv
  modified: []

key-decisions:
  - "Followed 08-RESEARCH.md locked decisions: JSON root moves to /api/info, GET / becomes HTML (test_root_moved_to_api_info encodes both halves)"
  - "test_polling inserts a partial job directly into src.api.batch.JOBS (imported lazily inside the test body) to deterministically test offset slicing without depending on TestClient background-task timing"
  - "Oversized-file test targets ~1.2MB (6000 x 200-byte rows) to safely clear the 1MB cap with margin"

patterns-established:
  - "Wave 0 plans: module-top imports limited to app + TestClient + stdlib; feature-specific seams (e.g. src.api.batch) imported lazily inside test bodies so collection never fails before implementation lands"

requirements-completed: [INPUT-05, WEB-01, WEB-02, WEB-03, WEB-07, WEB-08]

# Metrics
duration: 12min
completed: 2026-09-30
---

# Phase 08 Plan 01: Wave 0 Test Scaffolding Summary

**Two RED-by-design pytest files (test_web_ui.py, test_batch_api.py) plus a sample CSV fixture that lock in every Phase 8 HTML/static-asset/security-header/batch-upload/polling contract before any implementation exists.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-09-30T18:00Z (approx)
- **Completed:** 2026-09-30T18:12Z (approx)
- **Tasks:** 2
- **Files modified:** 3 (all new)

## Accomplishments
- `tests/test_web_ui.py` (114 lines, 8 test functions) encodes served-HTML form/file-input contracts, the `severityBand` XSS-safe app.js contract with 0.25/0.5/0.75 thresholds, responsive CSS markers, security headers (nosniff/DENY/CSP `default-src 'self'`), Swagger survival, and the root-move to `/api/info`.
- `tests/test_batch_api.py` (180 lines, 11 test functions) encodes the full `/batch` upload-validation matrix (bad extension, bad/missing header, >500 rows, >1MB file, >5000-char cell, case-insensitive header, empty CSV), job-id issuance, offset-based polling via direct `JOBS` insertion, 404 on unknown job, and per-row error isolation with no traceback leak.
- `tests/fixtures/batch_sample.csv` created and verified to parse correctly via `csv.DictReader` with `utf-8-sig` — the quoted multi-line email cell preserves `From:`/`Subject:` lines required by `EmailTextRequest`.
- Both files verified to `pytest --collect-only` cleanly, individually and as part of the full 434-test suite (no ImportError introduced).

## Task Commits

Each task was committed atomically:

1. **Task 1: Write tests/test_web_ui.py** - `70cd143` (test)
2. **Task 2: Write tests/test_batch_api.py + sample CSV fixture** - `51a293a` (test)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `tests/test_web_ui.py` - 8 Wave 0 tests for served HTML, static assets, XSS guard, CSP/security headers, Swagger survival, root→/api/info move
- `tests/test_batch_api.py` - 11 Wave 0 tests for CSV upload validation, job polling/offset slicing, 404, case-insensitive header, per-row error isolation
- `tests/fixtures/batch_sample.csv` - type,content sample with url/sms/email rows (multi-line quoted email cell)

## Decisions Made
- Mirrored `tests/test_api_image.py`'s `with TestClient(app) as c:` lifespan pattern and `tests/test_api.py`'s existing root-endpoint test style for consistency.
- Used the dotted-string monkeypatch form (`monkeypatch.setattr("src.api.batch._dispatch_row", fn)`) exactly as specified in the interfaces contract, so the seam resolves at call time and collection never depends on `src/api/batch.py` existing yet.
- For `test_polling`, imported `src.api.batch` inside the test body (not module top) per the plan's explicit collection-safety instruction; this test will error (not just fail assertions) until 08-04 ships, which is correct RED behavior — the `--collect-only` verification step does not execute test bodies, so this does not block collection.

## Deviations from Plan

None - plan executed exactly as written. Both test files implement every named test function listed in the plan's task actions, using only the interfaces/contracts already pinned in 08-RESEARCH.md and the plan's `<interfaces>` block. No production code was added.

## Issues Encountered
None - both `--collect-only` verifications and the fixture header/parse checks passed on the first attempt.

## Known Stubs
None - this plan authors tests and a fixture only; there is no UI/data-rendering code in scope that could stub out a data source.

## Threat Flags
None - no new network endpoints, auth paths, file-access patterns, or schema changes were introduced. This plan only writes tests that encode the controls (XSS guard, CSP, upload caps, error-message isolation) which 08-02/08-03/08-04 will implement and which this plan's own threat_model table already documents.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Wave 0 scaffolding complete: 08-02 (index/static mounting + root move), 08-03 (app.js/style.css), and 08-04 (src/api/batch.py) each have pre-existing failing tests to turn GREEN.
- `tests/fixtures/batch_sample.csv` is ready to be copied/served as `static/sample.csv` in a later plan (08-03 or 08-05 per the interfaces contract).
- No blockers. `src.api.batch` and `src/web/` do not exist yet — this is the expected RED state per the plan's objective.

---
*Phase: 08-batch-processing-web-interface*
*Completed: 2026-09-30*

## Self-Check: PASSED

- FOUND: tests/test_web_ui.py
- FOUND: tests/test_batch_api.py
- FOUND: tests/fixtures/batch_sample.csv
- FOUND: .planning/phases/08-batch-processing-web-interface/08-01-SUMMARY.md
- FOUND: commit 70cd143
- FOUND: commit 51a293a
