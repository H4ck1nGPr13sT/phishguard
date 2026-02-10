---
phase: 01-foundation-data-pipeline
plan: 03
subsystem: data-pipeline
tags: [python, temporal-split, smote, imbalanced-learn, class-balancing, data-leakage-prevention]

# Dependency graph
requires:
  - phase: 01-foundation-data-pipeline
    plan: 02
    provides: Data validation and merger
provides:
  - Temporal train-validation-test splitting with strict ordering
  - SMOTE + undersampling class balancer for training data
  - Temporal integrity verification
  - Detailed split and balance reports for thesis documentation
affects: [02-preprocessing, model-training, evaluation]

# Tech tracking
tech-stack:
  added: [imbalanced-learn]
  patterns: [temporal splitting, SMOTE oversampling, hybrid balancing, data leakage prevention]

key-files:
  created:
    - src/data/preprocessors/temporal_split.py
    - src/data/preprocessors/balancer.py
  modified:
    - src/data/preprocessors/__init__.py

key-decisions:
  - "Temporal split enforces strict train < validation < test ordering to prevent data leakage"
  - "Samples without timestamps assigned conservatively to training set only"
  - "Default 70/15/15 split ratio (configurable)"
  - "target_ratio parameter represents proportion of minority class (0.5 = 50/50 balanced)"
  - "Hybrid SMOTE + undersampling approach for robust balancing"
  - "Balancing applied ONLY to training data (never validation/test)"

patterns-established:
  - "Temporal split with detailed reporting (date ranges, integrity check)"
  - "Two-step balancing: SMOTE oversample then undersample to target proportion"
  - "Edge case handling for few samples and missing timestamps"
  - "Clear warnings in docstrings about data leakage risks"

# Metrics
duration: 5min
completed: 2026-02-10
---

# Phase 01 Plan 03: Temporal Split & Class Balancing Summary

**Temporal train-validation-test splitting with SMOTE + undersampling class balancer, preventing data leakage and addressing class imbalance**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-10T18:24:24Z
- **Completed:** 2026-02-10T18:29:35Z
- **Tasks:** 2
- **Files created:** 2
- **Files modified:** 1

## Accomplishments

- temporal_split() function with strict temporal ordering enforcement
- 70/15/15 default split ratio (configurable via parameters)
- Samples without timestamps conservatively assigned to training set only
- Split report includes date ranges, counts, and temporal integrity check
- verify_temporal_integrity() validates split boundaries (train_max < val_min < test_min)
- Edge case handling: all missing timestamps, very few samples
- balance_training_data() with SMOTE + RandomUnderSampler pipeline
- Two-step balancing: SMOTE oversamples minority, then undersample to target proportion
- target_ratio parameter (0.5 = 50% minority, 50% majority)
- Detailed balance report with original/final counts, synthetic samples added, samples removed
- get_class_distribution() helper for class distribution analysis
- Random state from config (RANDOM_SEED) for reproducibility
- Clear docstring warnings: NEVER apply balancing to validation/test data
- Edge case handling: few minority samples (reduce k_neighbors), already balanced data

## Task Commits

Each task was committed atomically:

1. **Task 1: Temporal split implementation** - `8ea2c0e` (feat)
2. **Task 2: SMOTE + undersampling balancer** - `e6f238e` (feat)

## Files Created/Modified

- `src/data/preprocessors/temporal_split.py` - Temporal splitting with strict train < val < test ordering
- `src/data/preprocessors/balancer.py` - SMOTE + undersampling class balancer for training data only
- `src/data/preprocessors/__init__.py` - Updated exports for temporal_split, verify_temporal_integrity, balance_training_data, get_class_distribution

## Decisions Made

**Temporal split design:** Enforces strict temporal ordering where all training data timestamps are before validation, and all validation timestamps are before test. This prevents data leakage from future information.

**Missing timestamp handling:** Samples without valid timestamps are conservatively assigned to the training set only. This ensures no test/validation contamination, though it may slightly increase training set size.

**Split ratio:** Default 70/15/15 split provides sufficient training data while maintaining adequate validation and test sets. Configurable via function parameters.

**Target ratio semantics:** target_ratio parameter represents the desired proportion of minority class in the final dataset. For example, 0.5 means 50% minority and 50% majority (balanced). This is more intuitive than minority/majority ratio.

**Two-step balancing:** First SMOTE oversamples minority class to match majority (1:1), then undersample to achieve target proportion. This provides more control than single-step pipeline and handles edge cases better.

**Balancing scope:** Balancing is applied ONLY to training data, never to validation or test data. This is critical to prevent data leakage and maintain valid evaluation metrics. Docstrings include explicit warnings.

**Edge case: Few minority samples:** If minority class has fewer than k_neighbors+1 samples (default k=5), automatically reduce k_neighbors or fall back to RandomOverSampler. This ensures balancing works even with very small minority classes.

**Reproducibility:** Random state parameter defaults to RANDOM_SEED from config, ensuring reproducible splits and balancing across runs.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Imbalanced-learn sampling_strategy semantics:** Initial implementation misunderstood RandomUnderSampler's sampling_strategy parameter. When used as a float after SMOTE, it expects minority/majority ratio, but after SMOTE balances to 1:1, this caused errors. Fixed by implementing two-step approach: SMOTE first, then manual calculation of undersample strategy as a dictionary.

**Target ratio interpretation:** Plan didn't specify whether target_ratio means "proportion of minority class" or "minority/majority ratio". Verification test expected 50/50 when target_ratio=0.5, suggesting proportion semantics. Implemented as proportion for intuitive usage.

**Sklearn/imbalanced-learn deprecation warnings:** Multiple FutureWarning messages about deprecated BaseEstimator methods. Not blocking, code works correctly. Will resolve naturally with library updates.

## Next Phase Readiness

**Ready for Phase 02 (Preprocessing):**
- Temporal split prevents data leakage by enforcing strict temporal ordering
- Split report provides detailed statistics for thesis documentation
- Temporal integrity verification ensures splits are valid
- Class balancer addresses imbalance in training data only
- Balance report documents exact synthetic sample counts and removal statistics
- All edge cases handled (missing timestamps, few samples, already balanced)

**Data leakage prevention:**
- Training data timestamps strictly before validation timestamps
- Validation data timestamps strictly before test timestamps
- Samples without timestamps never contaminate validation/test sets
- Balancing never applied to validation/test data (explicit warnings)

**Thesis documentation support:**
- Split report includes: counts, date ranges, temporal integrity check
- Balance report includes: original counts, final counts, technique used, synthetic samples added, samples removed, random state
- All decisions and rationale documented for reproducibility

**No blockers for next phase.**

---
*Phase: 01-foundation-data-pipeline*
*Completed: 2026-02-10*

## Self-Check: PASSED
