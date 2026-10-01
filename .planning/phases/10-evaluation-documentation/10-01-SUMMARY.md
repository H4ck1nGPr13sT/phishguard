---
phase: 10-evaluation-documentation
plan: 01
subsystem: testing
tags: [pytest, matplotlib, fastapi, openapi, mermaid, tdd-red-by-design]

# Dependency graph
requires: []
provides:
  - "tests/test_eval_report.py — RED-by-design contract for EVAL-05 (ablate_feature_groups/FEATURE_GROUPS) and EVAL-06 (export_pdf_report/export_csv_report + CLI smoke test)"
  - "tests/test_docs.py — RED-by-design structural contract for DOC-04/05/06/07 (13 expected docs files, Mermaid diagram-type sanity, internal link resolution)"
  - "tests/test_api.py::TestOpenAPI::test_openapi_routes_have_summaries — DOC-03 regression guard, data-driven over schema['paths']"
affects: [10-02-eval-tooling, 10-03-openapi-diagrams, 10-04-algorithm-docs, 10-05-algorithm-docs, 10-06-algorithm-docs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RED-by-design Wave 0 tests: under-test symbols imported inside test bodies (not module top) so pytest collection never ImportErrors before implementation lands"
    - "matplotlib.use('Agg') forced as the first two statements of a test module, before any pyplot import, to avoid the interactive macosx backend hanging collection/execution"
    - "stdlib-only docs structural tests (re + pathlib), no markdown-link-check dependency"

key-files:
  created:
    - tests/test_eval_report.py
    - tests/test_docs.py
  modified:
    - tests/test_api.py

key-decisions:
  - "Negative regression guard for Pitfall 1 reads cache/train_balanced.joblib's 'columns' key (35 entries including non-feature columns like url/content/label) and asserts it never equals the 30-col live feature_names list — proves the stale cache is structurally distinguishable from cache/url_training_data.joblib"
  - "test_openapi_routes_have_summaries turned out GREEN immediately rather than RED: FastAPI auto-derives a Title-Case summary from the route function name (e.g. 'Predict Multi Paradigm') even without an explicit summary= kwarg, so all 8 /predict*/explain routes already carry non-empty summaries today. Kept the test as-is since it still serves as a real regression guard for future un-named/lambda routes; documented the finding for Plan 10-03."

patterns-established:
  - "Wave 0 RED-by-design test authoring: write the full behavioral contract as tests before implementation, with module-top imports limited to stdlib/pytest/numpy/pandas/joblib so --collect-only never errors, and only import the not-yet-built symbols inside each test body"

requirements-completed: [EVAL-05, EVAL-06, DOC-03, DOC-04, DOC-05, DOC-06, DOC-07]

# Metrics
duration: 20min
completed: 2026-10-01
---

# Phase 10 Plan 01: Wave 0 RED-by-design Test Contracts Summary

**Authored three test files (two new, one extended) that lock the EVAL-05/06 ablation+export behavior and the DOC-03/04/05/06/07 structural contract as collectable pytest targets, with zero new dependencies, before any evaluation or documentation code exists.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-10-01T09:00:00Z (approx.)
- **Completed:** 2026-10-01T09:18:05Z
- **Tasks:** 3/3 completed
- **Files modified:** 3 (2 created, 1 extended)

## Accomplishments
- `tests/test_eval_report.py` created: 6 tests covering EVAL-05 (ablation-by-zeroing on the correct 30-col cache, visual-group N/A marker) and EVAL-06 (CSV/PDF export schema, end-to-end script smoke test). `matplotlib.use("Agg")` forced as the first two statements per Pitfall 2.
- `tests/test_docs.py` created: 3 tests covering DOC-04/05/06/07 — 13 expected docs files, Mermaid fenced-block diagram-type sanity, and internal Markdown link resolution, all stdlib-only (`re`/`pathlib`), glob scoped strictly to `docs/`.
- `tests/test_api.py::TestOpenAPI` extended with `test_openapi_routes_have_summaries`, a data-driven DOC-03 regression guard over `schema["paths"]`.
- All three files/edits collect cleanly under `pytest --collect-only`; full existing suite (452 passed, 1 skipped) shows zero regressions.

## Task Commits

Each task was committed atomically:

1. **Task 1: Author tests/test_eval_report.py (RED-by-design, EVAL-05 + EVAL-06)** - `3d3eea9` (test)
2. **Task 2: Author tests/test_docs.py (RED-by-design, DOC-04/05/06/07 structural)** - `ff1ff70` (test)
3. **Task 3: Extend tests/test_api.py with the DOC-03 OpenAPI summary guard** - `02f9e44` (test)

**Plan metadata:** (this commit, created after SUMMARY) — `docs(10-01): complete plan`

## Files Created/Modified
- `tests/test_eval_report.py` - RED-by-design EVAL-05/EVAL-06 contract: cache-schema guard (green now), ablation DataFrame shape test, visual-N/A marker test, CSV/PDF export schema tests, `@pytest.mark.slow` end-to-end script smoke test
- `tests/test_docs.py` - RED-by-design DOC-04/05/06/07 contract: expected-docs-exist (13 files), Mermaid diagram-type keyword sanity, internal Markdown link resolution
- `tests/test_api.py` - Added `test_openapi_routes_have_summaries` to the existing `TestOpenAPI` class

## Decisions Made
- Negative stale-cache guard reads `cache/train_balanced.joblib['columns']` (verified 35 entries: 30 UCI feature columns + `url`/`content`/`timestamp`/`source`/`label`) and asserts it is never equal to the live 30-col `feature_names` — gives the Pitfall 1 regression guard a concrete, verified assertion rather than a vague shape check.
- `test_openapi_routes_have_summaries` was written per-plan to be RED until Plan 10-03, but direct inspection of `app.openapi()` showed FastAPI already auto-populates `summary` from each route function's name (Title Case) even without an explicit `summary=` kwarg — all 8 `/predict*`/`/explain` routes are non-empty today. The test is kept exactly as specified (data-driven, no hardcoded route list) because it still guards against a future route with no discoverable name (e.g., `summary=""` explicitly set) and remains the correct regression contract for Plan 10-03's forthcoming `summary=`/`description=` enrichment.

## Deviations from Plan

### Auto-fixed Issues

**1. [Research-accuracy note, not a Rule 1-4 fix] DOC-03 guard is green-by-design, not RED-by-design as the plan predicted**
- **Found during:** Task 3 (OpenAPI summary guard)
- **Issue:** 10-RESEARCH.md assumed DOC-03's "gap" was that routes lack `summary=` metadata entirely; direct `app.openapi()` inspection shows FastAPI auto-derives a non-empty summary from the route function name regardless.
- **Fix:** No code change required — this is a test authored exactly per plan spec that happens to already pass. Documented here and in the test's own docstring for Plan 10-03's awareness.
- **Files modified:** tests/test_api.py (docstring note only)
- **Verification:** `.venv/bin/python -m pytest tests/test_api.py -k openapi -q` → 3 passed
- **Committed in:** 02f9e44 (Task 3 commit)

---

**Total deviations:** 1 documented finding (not a code fix — no Rule 1-4 applied)
**Impact on plan:** None on scope; Plan 10-03 should still add explicit `summary=`/`description=`/`response_description=` per the research's enrichment recommendation for Swagger UI quality, independent of this guard's current pass state.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `tests/test_eval_report.py` and `tests/test_docs.py` are ready as Wave 0 targets for Plan 10-02 (eval tooling) and Plans 10-03/04/05/06 (OpenAPI enrichment + docs) respectively.
- Full suite baseline before this plan: 452 passed, 1 skipped. After this plan: 452 passed, 1 skipped, 5 new RED failures (by design — `test_expected_docs_exist` and 4 of the 5 `test_eval_report.py` behavioral tests), 1 new green guard (`test_ablation_uses_correct_cache_schema`), 1 unexpectedly-green guard (`test_openapi_routes_have_summaries`). No regressions.
- No blockers for Plan 10-02.

---
*Phase: 10-evaluation-documentation*
*Completed: 2026-10-01*

## Self-Check: PASSED

- FOUND: tests/test_eval_report.py
- FOUND: tests/test_docs.py
- FOUND: .planning/phases/10-evaluation-documentation/10-01-SUMMARY.md
- FOUND: commit 3d3eea9
- FOUND: commit ff1ff70
- FOUND: commit 02f9e44
- FOUND: tests/test_api.py::TestOpenAPI::test_openapi_routes_have_summaries (line 268)
