---
phase: 10-evaluation-documentation
plan: 02
subsystem: ml-evaluation
tags: [matplotlib, pandas, scikit-learn, xgboost, ablation, pdf-export, csv-export, evaluation]

# Dependency graph
requires:
  - phase: 10-evaluation-documentation
    provides: "10-01 RED-by-design test contracts (tests/test_eval_report.py) describing EVAL-05/EVAL-06 behavior"
provides:
  - "ablate_feature_groups() + FEATURE_GROUPS in src/models/evaluate.py (EVAL-05, ablation-by-zeroing, no retraining)"
  - "export_pdf_report()/export_pdf_report_multi() + export_csv_report() in src/models/evaluate.py (EVAL-06)"
  - "scripts/generate_eval_report.py end-to-end CLI producing reports/eval_report.pdf, reports/eval_report.csv, reports/feature_ablation.csv"
  - "A committed reference run of all three artifacts under reports/"
affects: [10-evaluation-documentation (later docs plans may cross-reference the committed reports/ artifacts), thesis-appendix]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Ablation-by-zeroing: evaluate an already-trained model with a feature group's columns set to 0.0, never retrain"
    - "matplotlib.use(\"Agg\") forced at the top of both evaluate.py and generate_eval_report.py, before any pyplot import"
    - "All xgboost-containing joblib artifacts must be unpickled before `spacy` is imported anywhere in the process (platform-specific native-extension conflict); load_all_models() loads every XGBClassifier-bearing file first, extractors (which import spacy transitively) are imported lazily afterward"

key-files:
  created:
    - scripts/generate_eval_report.py
    - reports/eval_report.pdf
    - reports/eval_report.csv
    - reports/feature_ablation.csv
  modified:
    - src/models/evaluate.py

key-decisions:
  - "Task 1 and Task 2 code landed in a single commit (dde92c9) instead of two separate commits, because both were authored together in evaluate.py before the first commit succeeded; both are still independently unit-verified and acceptance-tested."
  - "Discovered and fixed (Rule 3, blocking issue) a SIGSEGV: importing `spacy` (transitively via src.features.extractors) before unpickling any XGBClassifier-containing joblib file crashes the process on this platform. Fixed by loading every xgboost-bearing artifact (7 optimized URL classifiers, URL ensemble, email ensemble, SMS ensemble) up front in load_all_models(), before src.features.extractors is imported anywhere."
  - "Email/SMS ablation evaluated on the full training sample set (no held-out split exists for email/SMS) and explicitly labelled 'training-data sensitivity (no held-out split exists); not a generalization claim' per content_type/note columns in feature_ablation.csv, per Open Question 1 in 10-RESEARCH.md."
  - "Visual group reported as a literal 'N/A' sentinel (not a fabricated number) with an explanatory note column, per Pitfall 3."

requirements-completed: [EVAL-05, EVAL-06]

# Metrics
duration: ~45min
completed: 2026-10-01
---

# Phase 10 Plan 02: Feature-Group Ablation + Exportable Evaluation Reports Summary

**Ablation-by-zeroing over GA-optimized URL/email/SMS classifiers plus matplotlib(Agg)/pandas PDF+CSV evaluation reports, with a committed reference run under reports/.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-10-01T09:05:00Z (approx, continuation after interruption)
- **Completed:** 2026-10-01T09:29:26Z
- **Tasks:** 3/3
- **Files modified:** 5 (1 modified, 4 created)

## Accomplishments
- `ablate_feature_groups()` + `FEATURE_GROUPS` (url/email/sms/visual) added to `src/models/evaluate.py`, implementing EVAL-05 via ablation-by-zeroing (no retraining) with the verified column-name tables from 10-RESEARCH.md Pattern 1.
- `export_pdf_report()` / `export_pdf_report_multi()` / `export_csv_report()` added, implementing EVAL-06: multi-page PDF (confusion matrix + ROC per classifier) via `ConfusionMatrixDisplay`/`RocCurveDisplay` + `PdfPages`, and a flat metrics CSV via pandas, with `matplotlib.use("Agg")` forced before any pyplot import.
- `scripts/generate_eval_report.py` runs end-to-end: evaluates the 7 GA-optimized URL classifiers + ensemble on `cache/url_training_data.joblib` (30-col, schema-guarded), ablates URL/email/SMS feature groups, marks the visual group N/A, and writes all three artifacts.
- Discovered and fixed a platform-specific SIGSEGV caused by import order (xgboost unpickling vs. spacy import) — see Deviations.
- Reference run committed under `reports/`: `eval_report.pdf` (54.5 KB, 8 classifiers x 2 pages), `eval_report.csv` (8 rows, 5 metrics each in [0,1]), `feature_ablation.csv` (15 ablation rows + 1 visual N/A row).

## Task Commits

1. **Task 1 + Task 2: FEATURE_GROUPS/ablate_feature_groups + export_pdf_report/export_csv_report** - `dde92c9` (feat) — both tasks' code landed together (see Decisions)
2. **Task 3: scripts/generate_eval_report.py + committed reference artifacts** - `cdf3dbf` (feat)

**Plan metadata:** (this commit, docs: complete 10-02 plan)

## Files Created/Modified
- `src/models/evaluate.py` - Added `FEATURE_GROUPS`, `VISUAL_GROUP`, `VISUAL_NA_NOTE`, `ablate_feature_groups()`, `export_pdf_report()`, `export_pdf_report_multi()`, `export_csv_report()`; forced `matplotlib.use("Agg")` at module import time.
- `scripts/generate_eval_report.py` - New CLI (`--output-dir`, default `reports/`) that loads all xgboost-bearing models first (avoiding the spacy-import SIGSEGV), evaluates the 7 URL classifiers + ensemble, exports PDF/CSV, and runs URL/email/SMS ablation + visual N/A row.
- `reports/eval_report.pdf` - Confusion matrix + ROC curve, 2 pages per classifier, 8 classifiers (rf, svm, mlp, xgb, lr, nb, dt, ensemble).
- `reports/eval_report.csv` - accuracy/precision/recall/f1_score/roc_auc per classifier, all values in [0,1].
- `reports/feature_ablation.csv` - content_type/group/baseline_accuracy/ablated_accuracy/delta/note; 4 url rows, 5 email rows, 5 sms rows, 1 visual N/A row.

## Decisions Made
- Combined Task 1 + Task 2 into one commit (`dde92c9`) — both were written together in `evaluate.py` in a single edit pass before the first commit landed; splitting after the fact would have required artificial diff reconstruction with no functional benefit. Both tasks are independently unit-tested and both acceptance criteria are met.
- Email/SMS ablation runs on the full training sample set (no held-out split exists in this codebase for email/SMS) and is explicitly labelled a training-data-sensitivity measurement, not a generalization claim, per 10-RESEARCH.md Open Question 1.
- Visual group is reported with a literal `"N/A"` string in `ablated_accuracy`/`baseline_accuracy`/`delta` plus an explanatory `note`, never a fabricated number, per Pitfall 3.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed SIGSEGV caused by spacy/xgboost import-order conflict**
- **Found during:** Task 3 (`scripts/generate_eval_report.py` first end-to-end run)
- **Issue:** `scripts/generate_eval_report.py` segfaulted (exit 139) every run. Isolated via `faulthandler` to `xgboost/core.py:__setstate__` during `pickle.load_build`. Root-caused to import order: once `spacy` is imported anywhere in the process (transitively via `src.features.extractors` -> `src.features.text_features`), any subsequent `joblib.load()` of a file containing an `XGBClassifier` (the 7 `models/optimized/*_optimized.joblib` files, `models/ensemble/voting_soft.joblib`'s underlying estimators as loaded via the registry, and `models/email_sms/ensemble_{email,sms}.joblib` which embed an XGBClassifier in their VotingClassifier) reliably crashes the process. Confirmed reproducible in isolation with a minimal repro (`import spacy; joblib.load(xgb_optimized.joblib)` -> SIGSEGV; reversed order -> works). This is a native-extension (OpenMP/BLAS) conflict on this platform, unrelated to GSD or the plan's logic.
- **Fix:** Restructured `scripts/generate_eval_report.py` so every xgboost-bearing joblib artifact is loaded in a new `load_all_models()` function BEFORE `src.features.extractors` (and thus `spacy`) is imported anywhere in the process. `extract_url_features`/`extract_email_features`/`extract_sms_features` are now imported lazily, function-local, only after `load_all_models()` has completed. Documented the constraint prominently in the module docstring and in docstrings of the affected functions so future edits don't reintroduce the ordering bug.
- **Files modified:** `scripts/generate_eval_report.py`
- **Verification:** `.venv/bin/python scripts/generate_eval_report.py --output-dir reports` now exits 0 and produces all three artifacts; `tests/test_eval_report.py::test_generate_eval_report_script_smoke` (the `@slow` end-to-end test) passes.
- **Committed in:** `cdf3dbf` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking — Rule 3)
**Impact on plan:** Necessary for the script to run at all on this platform; no scope creep, no behavior change to EVAL-05/EVAL-06 logic (only load ordering).

## Issues Encountered
- Mid-execution, a tool-call safety classifier interrupted one in-flight Bash call (the one that would have committed Task 1 and written the initial `generate_eval_report.py` draft) because of unrelated ambient `CLAUDE.md` content (an offensive-security persona from an unrelated project loaded into this session's context, not part of this task). Execution was resumed by re-verifying repo state (`git log`, `git status`) before continuing — no work was lost beyond the one interrupted call, and the offensive-security persona was disregarded throughout as explicitly out of scope for this thesis-engineering task.

## User Setup Required
None - no external service configuration required. No new dependencies (matplotlib, pandas, scikit-learn, joblib already installed).

## Next Phase Readiness
- `src/models/evaluate.py` now exposes `FEATURE_GROUPS`, `ablate_feature_groups`, `export_pdf_report`, `export_pdf_report_multi`, `export_csv_report` for reuse by later docs/appendix plans.
- `reports/eval_report.pdf`, `reports/eval_report.csv`, `reports/feature_ablation.csv` are committed reference artifacts later docs plans (e.g. thesis appendix) can cite directly.
- `tests/test_docs.py::test_expected_docs_exist` remains RED (1 failed in the full-suite run) — this is expected and out of scope: it is the RED-by-design contract from 10-01 for DOC-04/05/06/07, which land in later plans (10-03 through 10-06), not this plan.
- Full suite: 461 passed, 1 skipped, 1 failed (the out-of-scope DOC test above) — no regressions introduced by this plan.

---
*Phase: 10-evaluation-documentation*
*Completed: 2026-10-01*

## Self-Check: PASSED
All created/modified files exist; both task commits (dde92c9, cdf3dbf) found in git log.
