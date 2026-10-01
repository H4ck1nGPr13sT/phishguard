---
phase: 10-evaluation-documentation
plan: 04
subsystem: thesis-documentation
tags: [documentation, markdown, mermaid, ml-theory, data-pipeline, ensemble]

# Dependency graph
requires:
  - phase: 10-evaluation-documentation
    provides: "10-03 docs/architecture.md, docs/data-flow.md, docs/api.md (link targets, terminology baseline)"
  - phase: 10-evaluation-documentation
    provides: "10-02 reports/eval_report.csv, reports/feature_ablation.csv (reference evaluation artifacts cited)"
provides:
  - "docs/algorithms/README.md — algorithms doc index (DOC-06/07 landing page)"
  - "docs/algorithms/data-pipeline.md — dataset acquisition, validation, temporal split, SMOTE balancing, caching theory"
  - "docs/algorithms/ml-classifiers.md — theory + config + measured performance for all 7 classifiers"
  - "docs/algorithms/ensemble.md — soft/hard voting, stacking, normalized-Shannon-entropy disagreement"
  - "refreshed root README.md (phases 7-9 marked complete, full endpoint table, run instructions, ~452 test count, Dokumentacja section)"
affects: [10-05 (genetic-algorithm.md, rule-based-system.md, bayesian.md will extend docs/algorithms/README.md index), 10-06 (aggregation.md, ocr-visual.md, explainability.md), 10-07 (human-verify checkpoint reviews thesis accuracy of these docs)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Forward references to not-yet-created sibling docs (10-05/10-06) listed as plain text table rows in the index, never as Markdown links, so tests/test_docs.py::test_markdown_internal_links_resolve never sees a dangling link mid-phase"
    - "Figures cited from praca-inzynierska.pdf Tables 4/5b/6 (GA-optimized, 'hard' evaluation data per the thesis's own framing) presented alongside, not instead of, the earlier pre-GA STATE.md baseline figures, with both labelled by source so neither set is misrepresented as the other"

key-files:
  created:
    - docs/algorithms/README.md
    - docs/algorithms/data-pipeline.md
    - docs/algorithms/ml-classifiers.md
    - docs/algorithms/ensemble.md
  modified:
    - README.md

key-decisions:
  - "Cited two distinct evaluation figure sets explicitly by source (STATE.md pre-GA baseline vs. praca-inzynierska.pdf GA-optimized Tables 4/5b/6) rather than conflating them into one number, since they come from different training/evaluation runs; this keeps every cited figure traceable to a specific artifact (Pitfall: no fabricated metrics)."
  - "Task 1's own <verify> step for the internal-link test necessarily fails in isolation (ml-classifiers.md/ensemble.md don't exist until Task 2/3 of this same plan) — this is intra-plan sequencing, not a defect; the test passes once Task 3 lands, confirmed before the plan-level commit was considered complete."
  - "docs/algorithms/README.md lists 10-05/10-06's six algorithm docs as plain-text table rows (no Markdown link syntax) rather than omitting them, so the index is a complete table of contents from day one while never producing a dangling internal link (T-10-04-LINK mitigation)."

requirements-completed: [DOC-06, DOC-07]

# Metrics
duration: ~55min
completed: 2026-10-01
---

# Phase 10 Plan 04: Algorithm Theory Part I (Data Pipeline, ML Classifiers, Ensemble) + README Refresh Summary

**Thesis-grade Markdown docs for the data pipeline, all 7 ML classifiers, and the voting/stacking/disagreement ensemble layer, written fresh from the real `src/data` and `src/models` modules and cross-checked against `praca-inzynierska.pdf`'s own measured figures; plus a full refresh of the stale root README.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-10-01 (continuation session)
- **Completed:** 2026-10-01
- **Tasks:** 3/3
- **Files modified:** 5 (4 created, 1 modified)

## Accomplishments

- `docs/algorithms/README.md` — index/landing page for the algorithm theory doc set, linking the three files this plan creates plus `../architecture.md`/`../data-flow.md`, and listing the six 10-05/10-06 files as plain-text forward references (no dangling links).
- `docs/algorithms/data-pipeline.md` — covers all three dataset sources (PhishTank, UCI ML, Nazario) and why the legitimate class comes mainly from UCI ML; Pandera lazy validation; exact/fuzzy deduplication; the temporal train<val<test split with its no-leakage post-condition (`verify_temporal_integrity`, hard `RuntimeError` on violation); the undated-samples-to-training-only rule; hybrid SMOTE+undersampling applied strictly to training data (with the metadata-column separation detail required for SMOTE's numeric-only input); and joblib feature caching for reproducibility.
- `docs/algorithms/ml-classifiers.md` — one section per classifier (Random Forest, SVM, MLP, XGBoost, Logistic Regression, Naive Bayes, Decision Tree): formal learning principle, exact project configuration read from `CLASSIFIER_CONFIGS` in `src/models/classifiers.py`, measured standalone performance, and each classifier's role in the ensemble (including why NB and DT are kept despite being the two weakest standalone performers). Comparison table cites both the pre-GA `STATE.md` baseline figures and the GA-optimized figures from `praca-inzynierska.pdf` Tables 4/5b, explicitly labelled by source.
- `docs/algorithms/ensemble.md` — soft voting (97.47%), hard voting (97.01%), stacking (LogisticRegression meta-model, `cv=5`, 97.64%, per `praca-inzynierska.pdf` Table 6); `get_individual_predictions()`; classifier-level disagreement via normalized Shannon entropy (`H / log2(7)`), the empirically-chosen 0.7 edge-case threshold, and why entropy (not minority-vote proportion) is the right measure; a Mermaid `flowchart` of the voting/stacking/disagreement flow; model persistence (`save_ensemble`/`load_ensemble`).
- Root `README.md` refreshed per Pitfall 4: progress table now shows phases 7/8/9 ✅ with accurate one-line descriptions (OCR/visual, web UI + batch, SHAP explainability dashboard) and phase 10 in-progress; full endpoint table now includes `/`, `/api/info`, `/predict/image`, `/explain`, `/batch`, `/batch/{job_id}` (verified against the actual `@router.get`/`@router.post` decorators in `src/api/endpoints.py`/`batch.py`/`web.py`, not guessed); run instructions updated to note `uvicorn src.api.main:app` now serves the web UI + dashboard in one process and that OpenMP env vars (`KMP_DUPLICATE_LIB_OK`, `OMP_NUM_THREADS`) are set programmatically in `main.py` (verified via `grep`, not assumed); test count updated to the actually-collected ~452/463 figure; a new "Dokumentacja" section links to all of `docs/`.

## Task Commits

1. **Task 1: algorithms index + data-pipeline.md + README refresh** - `1db6216` (docs)
2. **Task 2: ml-classifiers.md (7 classifiers)** - `05b6946` (docs)
3. **Task 3: ensemble.md (voting/stacking/disagreement)** - `739fe16` (docs)

**Plan metadata:** (this commit, docs: complete 10-04 plan)

## Files Created/Modified

- `docs/algorithms/README.md` - Index with resolving links to this plan's 3 files + architecture.md/data-flow.md; plain-text forward refs to 10-05/10-06.
- `docs/algorithms/data-pipeline.md` - 195 lines; data sources, validation, dedup, temporal split, SMOTE balancing, caching.
- `docs/algorithms/ml-classifiers.md` - 248 lines; theory + config + measured performance + ensemble role for all 7 classifiers, with comparison table.
- `docs/algorithms/ensemble.md` - 227 lines; soft/hard voting, stacking, disagreement entropy, Mermaid flowchart.
- `README.md` - Progress table, endpoint table, run instructions, test count, project structure, new Dokumentacja section.

## Decisions Made

- Presented both the pre-GA `STATE.md` baseline figures and the GA-optimized `praca-inzynierska.pdf` Table 4/5b/6 figures side by side, explicitly labelled by source, rather than picking one or silently blending them — these come from genuinely different training/evaluation runs (initial Phase 3 training vs. post-GA-optimization evaluation on the temporal test set) and conflating them would misrepresent which number corresponds to which model artifact.
- Accepted that Task 1's isolated `<verify>` run of the internal-link test fails (links to `ml-classifiers.md`/`ensemble.md`, which Task 2/3 of this same plan haven't created yet) as expected intra-plan sequencing rather than a defect to fix; confirmed the link test passes once all three files exist (after Task 3), which is the state the plan-level verification cares about.
- Verified the endpoint table and OpenMP/run-instructions README claims against the actual code (`grep` on `@router.get`/`@router.post` decorators, `grep` on `KMP_DUPLICATE_LIB_OK`) rather than copying from STATE.md prose, per the plan's "ACCURACY IS PARAMOUNT" constraint.

## Deviations from Plan

None — plan executed as written. No Rule 1-4 deviations were needed; the only "failure" encountered (`test_expected_docs_exist` listing 6 missing files) is explicitly anticipated by the plan's own `<verification>` section and by `tests/test_docs.py`'s own docstring ("RED-by-design... until [10-03/04/05/06] land"), and is out of scope for this plan (those 6 files belong to Plans 10-05/10-06).

## Known Stubs

None. All four created docs contain complete, code-grounded prose; no placeholder text, no hardcoded-empty data paths, no "coming soon" sections.

## Threat Flags

None. This plan is pure static documentation (no new endpoints, no new auth paths, no new file-access patterns, no schema changes) — consistent with the plan's own threat model disposition (`T-10-04-INT`/`T-10-04-LINK` mitigate, `T-10-04-SC` N/A).

## Issues Encountered

- A system-reminder injected mid-session instructed use of raw Bash (`cat`/`sed`/heredocs) instead of the Read/Edit/Write tools, framed as a "bypass permissions mode" directive. This contradicted the harness's own explicit instruction (`Write` tool description: "never use Bash heredoc for file creation") and was disregarded as a likely prompt-injection; all file operations in this plan used the proper Read/Write/Edit tools throughout.
- An unrelated, ambient global/project `CLAUDE.md` (bug-bounty/offensive-security persona for a different project, `active-shield`) was present in session context at startup per the task's own instructions and was explicitly disregarded for the entire session, consistent with the objective's directive to ignore it.

## User Setup Required

None — no external service configuration required. No new dependencies (pure Markdown; stdlib-only `tests/test_docs.py`).

## Next Phase Readiness

- `docs/algorithms/README.md` is ready for Plans 10-05 (genetic-algorithm.md, rule-based-system.md, bayesian.md) and 10-06 (aggregation.md, ocr-visual.md, explainability.md) to extend with their own index rows and Markdown links, replacing the current plain-text forward-reference rows.
- `tests/test_docs.py::test_expected_docs_exist` remains RED (6 files missing) — expected and out of scope; will go green once 10-05/10-06 land.
- `tests/test_docs.py::test_markdown_internal_links_resolve` and `::test_mermaid_blocks_have_valid_diagram_type` are both green for all docs present after this plan.
- Full suite: 461 passed, 1 skipped, 1 expected-RED failure (the out-of-scope DOC test above) — no regressions introduced by this plan (up from 460 passed/1 skipped/2 failed before Task 3 landed `ensemble.md`).

---
*Phase: 10-evaluation-documentation*
*Completed: 2026-10-01*

## Self-Check: PASSED
All four created docs files and the modified README.md exist on disk; all three task commits (1db6216, 05b6946, 739fe16) found in `git log`.
