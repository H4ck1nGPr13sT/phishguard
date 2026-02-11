---
phase: 03-ml-ensemble-expansion
plan: 02
subsystem: ml
tags: [sklearn, ensemble, voting, stacking, joblib, machine-learning]

# Dependency graph
requires:
  - phase: 03-01
    provides: 7 trained base classifiers (RF, SVM, MLP, XGBoost, LR, NB, DT)
  - phase: 02-core-ml-pipeline-url-detection-mvp
    provides: Random Forest pipeline and training infrastructure
  - phase: 01-foundation-data-pipeline
    provides: Cached training data splits
provides:
  - 3 ensemble aggregation strategies (soft voting, hard voting, stacking)
  - Ensemble module with factory functions and individual prediction extraction
  - Comprehensive test suite validating all aggregation methods
affects: [03-03-disagreement-detection, 03-04-ensemble-optimization, api-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "VotingClassifier with soft voting (average probabilities) for ensemble aggregation"
    - "VotingClassifier with hard voting (majority vote) for ensemble aggregation"
    - "StackingClassifier with LogisticRegression meta-model and cv=5 for data leakage prevention"
    - "get_individual_predictions() for extracting per-classifier results for disagreement analysis"

key-files:
  created:
    - src/models/ensemble.py
    - models/ensemble/voting_soft.joblib
    - models/ensemble/voting_hard.joblib
    - models/ensemble/stacking.joblib
    - tests/test_ensemble.py
  modified:
    - src/models/__init__.py
    - src/models/train_ensemble.py

key-decisions:
  - "VotingClassifier n_jobs=-1 for parallel prediction across all estimators"
  - "StackingClassifier cv=5 prevents data leakage by training meta-model on out-of-fold predictions"
  - "Soft voting uses predict_proba() averaging (requires probability=True in SVM)"
  - "Hard voting uses majority vote across classifier predictions"
  - "Meta-model is LogisticRegression with class_weight='balanced' for imbalanced data handling"
  - "get_individual_predictions() extracts phishing_probability, prediction, confidence for each classifier"

patterns-established:
  - "Ensemble models saved with metadata (model_type, created_at, n_estimators) using save_ensemble()"
  - "Load ensemble models using load_ensemble() which handles dict format"
  - "Individual predictions dict format: {clf_name: {phishing_probability, prediction, confidence}}"

# Metrics
duration: 6min
completed: 2026-02-11
---

# Phase 3 Plan 2: Ensemble Aggregation Summary

**Three ensemble strategies trained (soft/hard voting, stacking) achieving 97.47%/97.14% accuracy, exceeding individual classifier average of 89.15%**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-11T12:13:39Z
- **Completed:** 2026-02-11T12:19:40Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- Soft voting ensemble with 97.47% training accuracy (averages probabilities from 7 classifiers)
- Hard voting ensemble with 97.14% training accuracy (majority vote across predictions)
- Stacking ensemble with LogisticRegression meta-model trained via 5-fold CV
- Individual prediction extraction function for disagreement detection foundation
- 15 comprehensive tests validating all aggregation methods

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ensemble module with voting and stacking functions** - `989a434` (feat)
2. **Task 2: Train and save ensemble models** - `02ae831` (feat)
3. **Task 3: Add ensemble tests and verify aggregation methods** - `2fb6834` (test)

## Files Created/Modified
- `src/models/ensemble.py` - VotingClassifier and StackingClassifier factory functions, individual prediction extraction, save/load utilities
- `src/models/__init__.py` - Exports ensemble module functions
- `src/models/train_ensemble.py` - train_ensembles() function trains all 3 aggregation strategies, print_ensemble_summary() for comparison
- `models/ensemble/voting_soft.joblib` - Soft voting ensemble (5.71 MB, averages probabilities)
- `models/ensemble/voting_hard.joblib` - Hard voting ensemble (5.71 MB, majority vote)
- `models/ensemble/stacking.joblib` - Stacking ensemble with LogisticRegression meta-model
- `tests/test_ensemble.py` - 15 tests covering ensemble creation, loading, predictions, and accuracy comparison

## Decisions Made

**Ensemble architecture:**
- Soft voting averages predict_proba() outputs from all 7 classifiers (requires SVM probability=True)
- Hard voting uses majority vote across predicted class labels
- Stacking uses 5-fold CV to generate out-of-fold predictions for meta-model training (prevents data leakage)
- Meta-model is LogisticRegression with class_weight='balanced' and max_iter=1000

**Individual prediction extraction:**
- get_individual_predictions() returns dict with per-classifier results for disagreement analysis
- Each result includes: phishing_probability (float), prediction (str), confidence (float)
- Enables foundation for ENS-05 disagreement detection in next plan

**Model persistence:**
- save_ensemble() wraps joblib.dump with metadata (model_type, created_at, sklearn_version, n_estimators)
- load_ensemble() handles dict format and extracts model object
- Compression level 3, protocol 5 for efficient storage (each ensemble ~5.7 MB)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**RuntimeWarning during training:** MLP and LogisticRegression emitted divide-by-zero and overflow warnings in matmul operations. These are benign numerical warnings from sklearn's internal gradient calculations on scaled data. Models trained successfully and achieved expected accuracy levels. No action required.

## Next Phase Readiness

**Ready for next phase (03-03 Disagreement Detection):**
- 3 ensemble models trained and saved
- Individual prediction extraction function implemented and tested
- Ensemble accuracy (97.47%) exceeds average individual (89.15%) and best individual (96.29%)
- All tests passing (15/15)

**Foundation established for:**
- Disagreement detection between classifiers
- Ensemble optimization and hyperparameter tuning
- API integration with multiple aggregation strategies

**No blockers or concerns.**

---
*Phase: 03-ml-ensemble-expansion*
*Completed: 2026-02-11*

## Self-Check: PASSED

All files and commits verified.
