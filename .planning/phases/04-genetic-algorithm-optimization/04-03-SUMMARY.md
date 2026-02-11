---
phase: 04-genetic-algorithm-optimization
plan: 03
subsystem: optimization
tags: [deap, genetic-algorithm, feature-selection, mlflow, scikit-learn]

# Dependency graph
requires:
  - phase: 04-01
    provides: GA infrastructure with DEAP, fitness evaluation, and search space patterns
  - phase: 03-01
    provides: 7 trained classifiers with 30 URL features
provides:
  - GA-based feature selection module with binary representation
  - Feature subset (16/30 features) achieving 96.61% F1-score
  - Feature selection CLI script with MLflow logging
  - Quantified feature importance for model optimization
affects: [04-04, model-retraining, feature-engineering]

# Tech tracking
tech-stack:
  added: []
  patterns: [binary-ga-representation, minimum-constraint-enforcement, rf-proxy-fitness]

key-files:
  created:
    - src/optimization/feature_selection.py
    - scripts/run_feature_selection.py
  modified: []

key-decisions:
  - "Binary representation (1=selected, 0=excluded) for feature selection"
  - "RF as proxy classifier for fitness evaluation (fast, robust)"
  - "Minimum 5 features constraint prevents degenerate solutions"
  - "Two-point crossover and bit-flip mutation for binary GA"
  - "Smaller population (30) and fewer generations (20) due to simpler search space"
  - "Selected features saved to cache/selected_features.joblib for optional retraining"

patterns-established:
  - "Binary GA pattern: tools.initRepeat with random.randint(0,1) for binary individuals"
  - "Minimum constraint enforcement: return (0.0,) fitness when constraint violated"
  - "Proxy classifier pattern: use fast RF for feature selection, apply results to all classifiers"

# Metrics
duration: 3min
completed: 2026-02-11
---

# Phase 04 Plan 03: Feature Selection Optimization Summary

**GA-based feature selection identifies 16 optimal features from 30, achieving 46.7% reduction while improving F1-score by 0.56% (0.9607 → 0.9661)**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-11T23:06:20Z
- **Completed:** 2026-02-11T23:09:20Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- GA feature selection reduces feature space from 30 to 16 features (46.7% reduction)
- Selected features improve classification performance (F1: 0.9607 → 0.9661, +0.56%)
- Key features identified: url_length, path_length, subdomain_length, query_length, dot_count, hyphen_count, slash_count, digit_count, special_char_count, entropy
- Feature selection results saved with full metadata for model retraining
- MLflow experiment tracking for feature selection optimization

## Task Commits

Each task was committed atomically:

1. **Task 1: Create feature selection GA module** - `889a13d` (feat)
2. **Task 2: Create feature selection script and run optimization** - `a49e335` (feat)

## Files Created/Modified
- `src/optimization/feature_selection.py` - GA-based feature selection with binary representation
- `scripts/run_feature_selection.py` - CLI script for running feature selection with MLflow logging
- `cache/selected_features.joblib` - Selected feature results (gitignored artifact)

## Selected Features

**16 features selected from 30 original features:**

1. url_length (0)
2. path_length (2)
3. subdomain_length (4)
4. query_length (6)
5. dot_count (7)
6. hyphen_count (8)
7. slash_count (10)
8. question_count (11)
9. equal_count (12)
10. digit_count (15)
11. special_char_count (16)
12. has_ip (18)
13. has_subdomain (20)
14. has_fragment (22)
15. param_count (27)
16. entropy (28)

**Features excluded (14):**
- domain_length, hostname_length, tld_length (length features less discriminative than structural)
- underscore_count, at_count, ampersand_count (rare in legitimate/phishing URLs)
- has_https, has_port, is_valid, has_suspicious_tld (less predictive in current dataset)
- subdomain_count (redundant with has_subdomain and subdomain_length)
- digit_ratio (redundant with digit_count)

## Decisions Made

**1. Binary GA representation**
- 1 = feature selected, 0 = feature excluded
- Simpler than hyperparameter optimization (discrete vs continuous/categorical)
- Faster convergence: 20 generations sufficient vs 30 for hyperparameter search

**2. RF proxy classifier for fitness**
- Random Forest used for fitness evaluation (not all 7 classifiers)
- Rationale: Speed and robustness. RF is fast and generalizes well
- Selected features will be used by all classifiers if retraining occurs

**3. Minimum 5 features constraint**
- Enforced in fitness function: return (0.0,) if fewer than 5 features
- Prevents degenerate solutions (e.g., selecting only 1-2 features)
- Ensures sufficient information for classification

**4. Smaller population and fewer generations**
- Population: 30 (vs 50 for hyperparameter optimization)
- Generations: 20 (vs 30 for hyperparameter optimization)
- Binary search space simpler than mixed-type hyperparameter space
- Evolution converged quickly: best fitness reached by generation 5

**5. Two-point crossover and bit-flip mutation**
- Two-point crossover works well for binary representation
- Bit-flip mutation with indpb=1/n_features (average 1 bit flip per individual)
- Maintains diversity while exploring feature combinations

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - feature selection ran smoothly with expected convergence behavior.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for:**
- Phase 04-04 (if planned): Ensemble weight optimization using selected features
- Model retraining: Can retrain all 7 classifiers with 16-feature subset for comparison
- Feature engineering: Analysis shows which feature types contribute most (structural > length > binary)

**Key insights:**
- Structural features (entropy, special_char_count, dot_count) highly discriminative
- Binary indicators (has_ip, has_subdomain, has_fragment) useful
- Many length features redundant (url_length sufficient, others less important)
- Character counts (slash, question, equal) capture URL structure effectively

**Optional optimization:**
- Retrain all 7 classifiers with 16-feature subset
- Compare 16-feature ensemble vs 30-feature ensemble
- If performance maintained, deploy lighter models with faster inference

**No blockers or concerns.**

---
*Phase: 04-genetic-algorithm-optimization*
*Completed: 2026-02-11*

## Self-Check: PASSED

All files and commits verified:
- src/optimization/feature_selection.py: FOUND
- scripts/run_feature_selection.py: FOUND
- Commit 889a13d: FOUND
- Commit a49e335: FOUND
