---
phase: 09-explainability-dashboard
plan: 01
subsystem: testing
tags: [pytest, shap, fastapi, testclient, tdd-wave0, explainability]

# Dependency graph
requires:
  - phase: 08-web-interface
    provides: src/web/templates/index.html, src/web/static/app.js, security_headers_middleware CSP, test_web_ui.py contract-test conventions
  - phase: 05-multi-paradigm
    provides: MultiParadigmAggregator, disagreement.py (calculate_paradigm_disagreement/get_disagreement_explanation), FiredRule/ParadigmContributions models
provides:
  - "tests/test_api_explain.py: RED-by-design POST /explain contract (13 tests) locking the consolidated response shape for 09-02"
  - "tests/test_web_ui.py: RED-by-design Explain-dashboard markup + chart-renderer + XSS/CSP contract for 09-03"
  - "tests/test_api_multiparadigm.py: guard that /predict/multi-paradigm schema is unmutated by /explain work"
  - "shap>=0.52.0 declared + installed runtime dependency"
affects: [09-02-backend-explain-endpoint, 09-03-frontend-dashboard, 09-04]

# Tech tracking
tech-stack:
  added: ["shap>=0.52.0 (TreeExplainer; pulls numba/llvmlite, not torch)"]
  patterns:
    - "Wave-0 RED-by-design test authoring: tests collect cleanly and encode the exact response contract before the endpoint exists; verify step is --collect-only, not pass/fail"
    - "monkeypatch.setitem(ml_models, ...) + monkeypatch.setattr('src.api.endpoints.<seam>', ...) to keep fast API tests shap-free, mirroring tests/test_api_image.py's FakeOCRBackend pattern"
    - "Graceful-degrade test: monkeypatch a lifespan warm-step to raise, assert app startup still succeeds and the dependent endpoint degrades to 503 instead of crashing the server"
    - "Regex-based no-external-script assertion (re.findall on <script src=\"...\">) instead of substring checks, to correctly reject protocol-relative CDN sources without false-positiving on legitimate /static/ paths"

key-files:
  created:
    - tests/test_api_explain.py
  modified:
    - requirements.txt
    - tests/test_web_ui.py
    - tests/test_api_multiparadigm.py

key-decisions:
  - "shap already present in .venv (0.52.0) from the research session — pip install was a no-op confirming the pin; no new install risk introduced"
  - "test_explain_503_when_shap_missing and test_explain_503_when_detector_missing deliberately omit the shap-free monkeypatch seams since they assert the absence/missing-model paths directly"
  - "test_app_starts_when_shap_warm_raises monkeypatches src.api.main.warm_shap_explainer with raising=False since that name does not exist yet in main.py (09-02 will add it) — this keeps the test collectable now and correctly RED (AttributeError-safe no-op patch target) until 09-02 lands the real warm-step"

requirements-completed: [EXPL-01, EXPL-02, EXPL-03, EXPL-04, EXPL-05, WEB-04, WEB-06]

# Metrics
duration: 25min
completed: 2026-10-01
---

# Phase 9 Plan 01: Wave 0 Test Contracts + shap Dependency Summary

**Locked the consolidated POST /explain response contract (13 RED-by-design tests) and the Explain-dashboard markup/JS contract (4 new web-UI tests) before any 09-02/09-03 implementation, plus added shap>=0.52.0 as a declared runtime dependency.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-10-01T07:56:31Z
- **Tasks:** 3/3
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- `shap>=0.52.0` pinned in `requirements.txt` under a new `# Phase 9 - Explainability` section, documented as pulling numba/llvmlite (not torch); verified importable in `.venv`
- New `tests/test_api_explain.py` (13 tests) fully specifies the `/explain` payload: `url`, `final_prediction`, `final_probability`, `confidence`, `individual_predictions` (7 classifiers), `paradigm_contributions` (ml_ensemble/rules/bayesian), `shap` (top-10 features descending `|shap_value|`, `content_type="url"`, `model="rf"`), `active_rules`, `disagreement`, `disagreement_explanation`, `explanation`, `processing_time_ms` — plus 422 validation, two distinct 503 paths (detector missing, shap_explainer missing), a graceful-degrade-on-shap-warm-failure test, and a `@pytest.mark.slow` real-TreeExplainer test
- `tests/test_web_ui.py` extended with 4 new tests: dashboard markup presence (`explain-btn`/`dashboard`/`classifier-chart`/`shap-chart` ids), new chart-renderer function names + `createElementNS` usage, an extended XSS-sink ban, and a regex-based no-external-`<script src>` check (catches protocol-relative CDN sources, not just `http://`)
- `tests/test_api_multiparadigm.py` extended with `TestMultiParadigmUnchangedByExplain` guarding that `/predict/multi-paradigm`'s existing schema is untouched by the new `/explain` work

## Task Commits

Each task was committed atomically:

1. **Task 1: Add shap dependency and install into the project venv** - `74edb6a` (chore)
2. **Task 2: Author tests/test_api_explain.py (RED-by-design, mocked + slow real-SHAP)** - `9a00a83` (test)
3. **Task 3: Extend web-UI and multiparadigm tests for the dashboard contract** - `29137ab` (test)

_No TDD micro-cycle applies here — this plan itself IS the Wave-0 RED-authoring step for 09-02/09-03; each task is a single `test`/`chore` commit._

## Files Created/Modified
- `requirements.txt` - added pinned `shap>=0.52.0` under a Phase 9 section with a numba/llvmlite-not-torch note
- `tests/test_api_explain.py` - new file: 13 RED-by-design tests locking the full `/explain` contract
- `tests/test_web_ui.py` - added `test_index_has_explain_dashboard`, `test_app_js_defines_chart_renderers`, `test_app_js_contract_dashboard`, `test_index_no_external_scripts`
- `tests/test_api_multiparadigm.py` - added `TestMultiParadigmUnchangedByExplain::test_multiparadigm_unchanged_by_explain`

## Decisions Made
- shap was already installed in `.venv` (0.52.0) from the 09-RESEARCH.md research session — `pip install` was a confirming no-op, not a fresh install; no new supply-chain exposure introduced beyond what research already audited (`[OK]`/Approved via slopcheck + PyPI registry, per the threat register's T-09-SC disposition)
- For `test_app_starts_when_shap_warm_raises`, monkeypatched `src.api.main.warm_shap_explainer` with `raising=False` since that attribute does not exist in `main.py` yet (09-02's job to add) — keeps the test collectable today and correctly exercises the intended seam name once 09-02 lands it
- `test_explain_503_when_shap_missing` and `test_explain_503_when_detector_missing` intentionally skip the shap-free monkeypatch helper since they test the *absence* paths directly (popping/clearing `ml_models`)

## Deviations from Plan

None - plan executed exactly as written, including both checker-warning fixes already specified in the plan (regex no-external-script test via `re.findall`, and the graceful-degrade `test_app_starts_when_shap_warm_raises` test).

## Issues Encountered

None. Both verification commands (`--collect-only` for the new/extended files, and the full `-m "not slow"` wave gate) ran as specified in `<verification>`.

## User Setup Required

None - no external service configuration required. shap is a pure pip dependency, already installed locally.

## Next Phase Readiness

- `tests/test_api_explain.py` is the acceptance target for 09-02 (backend `/explain` endpoint + `src/api/endpoints.py::shap_top_features` seam + `src/api/main.py::warm_shap_explainer` lifespan step)
- `tests/test_web_ui.py`'s 4 new assertions are the acceptance target for 09-03 (dashboard markup in `index.html` + `renderDashboard`/`renderClassifierChart`/`renderShapChart` in `app.js`)
- Full suite verified green except the 14 expected-RED tests (12 in `test_api_explain.py`, 2 in `test_web_ui.py`) — confirmed via `pytest -m "not slow" -q`: **434 passed, 1 skipped, 4 deselected (slow), 14 failed (all RED-by-design, zero regressions)**
- No blockers for 09-02/09-03

---
*Phase: 09-explainability-dashboard*
*Completed: 2026-10-01*

## Self-Check: PASSED

- FOUND: tests/test_api_explain.py
- FOUND: .planning/phases/09-explainability-dashboard/09-01-SUMMARY.md
- FOUND: shap pin in requirements.txt
- FOUND commit: 74edb6a (chore: add shap dependency)
- FOUND commit: 9a00a83 (test: author /explain contract tests)
- FOUND commit: 29137ab (test: extend web-UI and multiparadigm tests)
