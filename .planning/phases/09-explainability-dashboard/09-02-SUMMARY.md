---
phase: 09-explainability-dashboard
plan: 02
subsystem: backend-api
tags: [shap, fastapi, explainability, treeexplainer, pydantic]

# Dependency graph
requires:
  - phase: 09-explainability-dashboard
    plan: 01
    provides: tests/test_api_explain.py (RED-by-design contract), shap>=0.52.0 dependency
  - phase: 05-multi-paradigm
    provides: MultiParadigmAggregator, disagreement.py (get_disagreement_explanation), predict_url_multi
  - phase: 03-ensemble
    provides: get_individual_predictions (7-classifier comparison)
provides:
  - "src/explainability/shap_explain.py: warm_shap_explainer() + shap_top_features(url, top_n) — URL-only SHAP TreeExplainer on the representative RF Pipeline"
  - "POST /explain: consolidated EXPL-01/02/03/04/05 response in one call"
  - "src/api/models.py: FeatureContribution, ShapExplanation, ExplainResponse Pydantic models"
affects: [09-03-frontend-dashboard, 09-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level idempotent cache (dict) for a warm-started heavy object (SHAP TreeExplainer) — second warm call is a no-op read, not a rebuild"
    - "Lifespan graceful-degrade try/except (mirrors the Phase 7 OCR warm-up pattern): a missing/broken optional heavy dependency leaves a ml_models[] key unset rather than crashing startup; the dependent endpoint 503s instead"
    - "Monkeypatch seam at the importing module's namespace (src.api.endpoints.shap_top_features), not the defining module's, so tests can swap it out without touching real shap"
    - "New dedicated response model (ExplainResponse) instead of extending a tested existing schema (MultiParadigmResponse) when the new endpoint is a separate, slower code path"

key-files:
  created:
    - src/explainability/__init__.py
    - src/explainability/shap_explain.py
  modified:
    - src/api/models.py
    - src/api/endpoints.py
    - src/api/main.py

key-decisions:
  - "SHAP explains only ml_models['phishing_detector'] (RF Pipeline), never ml_models['voting_soft'] (heterogeneous VotingClassifier) — per 09-RESEARCH.md Pitfall 2, this is the only model with a fast, exact TreeExplainer path"
  - "Background sample is cache/url_training_data.joblib['X_train'] (30 cols), asserted against clf.n_features_in_ at warm time; the stale 35-col caches (train_balanced/test/validation.joblib) are never referenced anywhere in the new code"
  - "warm_shap_explainer() built as idempotent via a plain module-level dict cache (not a class/singleton) — keeps repeated TestClient lifespan entries in the same pytest process cheap and matches the plan's WARNING-1 fix requirement"
  - "An unexpected SHAP failure AT REQUEST TIME (post-warm) degrades the shap block to available=False + a note rather than a 500; a missing explainer ENTIRELY (never warmed) is a 503 before any work starts — these are two different failure classes handled at two different points"
  - "/api/info endpoint list updated to include /explain for consistency with every other router addition in this file (not plan-mandated, applied as a small Rule-2-style completeness fix)"

requirements-completed: [EXPL-02, EXPL-03, EXPL-04, EXPL-05]

# Metrics
duration: ~35min
completed: 2026-10-01
---

# Phase 9 Plan 02: SHAP Explainer + Consolidated /explain Endpoint Summary

**New `src/explainability/` module computes URL-only SHAP feature importance via `shap.TreeExplainer` on the representative GA-optimized RF Pipeline (warmed once at FastAPI lifespan startup), and a new `POST /explain` endpoint consolidates it with the 7-classifier comparison, fuller paradigm-disagreement text, and a SHAP-enriched natural-language verdict into a single response.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-10-01T08:08:26Z
- **Tasks:** 2/2
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments

- `src/explainability/shap_explain.py`: `warm_shap_explainer(pipeline=None)` builds the `shap.TreeExplainer` against the RF classifier (unwrapped from the Pipeline) using the scaler-transformed 30-col `cache/url_training_data.joblib` background, with a loud `ValueError` on any column-count mismatch against `clf.n_features_in_`. It is IDEMPOTENT via a module-level cache — a second call returns the cached explainer without re-importing `shap` or rebuilding. `shap_top_features(url, top_n=10)` extracts URL features, scaler-transforms, calls `shap_values`, branches on `ndim` (3 → class-1 slice, 2 → direct) and returns top-N `{feature, shap_value, raw_value}` dicts ordered by descending `|shap_value|`.
- `src/api/main.py` lifespan: warms the SHAP explainer right after the OCR block, mirroring its graceful-degrade `try/except` — any failure (missing `shap`, bad cache) prints a warning and leaves `ml_models["shap_explainer"]` unset instead of crashing startup.
- `src/api/models.py`: added `FeatureContribution`, `ShapExplanation`, and `ExplainResponse` — a new dedicated response model reusing the existing `ClassifierResult`/`FiredRule`/`ParadigmContributions`/`ParadigmDisagreementInfo` nested models. `MultiParadigmResponse` was not touched.
- `src/api/endpoints.py`: `POST /explain` reuses `URLRequest` validation, 503s when any of `phishing_detector`/`voting_soft`/`rule_engine`/`bayesian`/`aggregator`/`shap_explainer` is missing, calls `predict_url_multi` (catching `ModelsNotLoaded` → 503), builds all 7 individual predictions via `get_individual_predictions`, computes SHAP top-10 through the `shap_top_features` monkeypatch seam (wrapped so an unexpected runtime SHAP failure degrades to `available=False` + a note instead of a 500), surfaces the fuller `get_disagreement_explanation` text, and appends a sentence naming the top SHAP feature to the NL `explanation`.

## Task Commits

| Task | Commit | Summary |
|------|--------|---------|
| 1 | `d159e02` | SHAP explainer module + lifespan warm-up (URL-only, RF) |
| 2 | `51e55a4` | Consolidated POST /explain endpoint + ExplainResponse models |

## Verification

- Task 1 direct module verify: `SHAP_MODULE_OK 10` + idempotency check (`warm_shap_explainer()` called twice returns the identical object) — both passed.
- `pytest tests/test_api_explain.py tests/test_api_multiparadigm.py -x -m "not slow" -q` → **25 passed, 1 deselected**.
- `pytest tests/test_api_explain.py -x -m slow -q` (real SHAP, no monkeypatch) → **1 passed** — proves the EXPL-05 enrichment sentence against a real `TreeExplainer` run, not just the canned mock.
- `pytest tests/test_api_multiparadigm.py tests/test_api.py tests/test_api_email_sms.py -x -q` → **68 passed** — no regression in existing endpoint schemas.
- Full wave gate `pytest -m "not slow" -q` → **446 passed, 2 failed, 1 skipped, 4 deselected**. The 2 failures (`test_web_ui.py::test_index_has_explain_dashboard`, `test_web_ui.py::test_app_js_defines_chart_renderers`) are the RED-by-design frontend dashboard contract tests authored in 09-01 explicitly reserved for **Plan 09-03** (WEB-04/WEB-06 — `index.html` Explain button/dashboard markup, `app.js` SVG chart renderers). They are out of scope for this backend-only plan (`files_modified` in 09-02-PLAN.md does not touch `src/web/`) and were already failing before this plan's changes; they are not a regression introduced here.

## Deviations from Plan

### Auto-fixed Issues

None required beyond what the plan already specified in detail — the plan's checker-fixed action blocks (idempotent warm, module-level verify, graceful lifespan degrade) were followed as written and all automated verifies passed on the first attempt.

### Minor additions (Rule 2 — completeness, not correctness-critical)

**1. [Rule 2 - completeness] Added `/explain` to the `GET /api/info` endpoint list**
- **Found during:** Task 2
- **Issue:** Every other router addition in `src/api/endpoints.py`'s history updates the `/api/info` `endpoints` list; `/explain` was initially missing from it, which would make the API's self-description endpoint silently stale.
- **Fix:** Added `"/explain"` to the list, directly after `"/predict/image"`.
- **Files modified:** `src/api/endpoints.py`
- **Commit:** `51e55a4`

## Known Stubs

None. All data paths are wired to real computation (real SHAP TreeExplainer, real aggregator output, real 7-classifier ensemble) — no hardcoded empty/placeholder values flow into the response.

## Threat Flags

None. All new surface (the `POST /explain` endpoint, the SHAP compute path, the `cache/url_training_data.joblib` background load) was already enumerated and dispositioned in the plan's `<threat_model>` (T-09-01 through T-09-04, T-09-SC) and implemented exactly per those mitigations: input validation reuses `URLRequest` (T-09-02), the background column-count assertion guards the stale-cache risk (T-09-03), and the lifespan `try/except` prevents a missing-`shap` crash (T-09-04).

## Self-Check: PASSED

- `src/explainability/__init__.py` — FOUND
- `src/explainability/shap_explain.py` — FOUND
- `src/api/models.py` (ExplainResponse present) — FOUND
- `src/api/endpoints.py` (`/explain` route present) — FOUND
- `src/api/main.py` (`shap_explainer` warm-up present) — FOUND
- Commit `d159e02` — FOUND in `git log`
- Commit `51e55a4` — FOUND in `git log`
