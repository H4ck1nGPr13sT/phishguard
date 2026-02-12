---
phase: 05-alternative-detection-paradigms
plan: 03
subsystem: ml-paradigms
tags: [multi-paradigm, aggregation, weighted-voting, disagreement-detection, entropy]

# Dependency graph
requires:
  - phase: 05-01-rule-based-expert-system
    provides: Rule-based detection with weighted scoring and fired rules list
  - phase: 05-02-bayesian-probabilistic-classifier
    provides: Bayesian classifier with posterior probability extraction
  - phase: 03-ml-ensemble-expansion
    provides: ML ensemble with 7 classifiers and weighted voting
provides:
  - MultiParadigmAggregator combining ML ensemble, rules, and Bayesian predictions
  - Cross-paradigm disagreement detection using normalized Shannon entropy
  - Configurable paradigm weights with validation (default: ML=0.5, Rules=0.3, Bayesian=0.2)
  - Comprehensive aggregation output with contributions, confidence, and explanations
affects: [06-integration-layer, 08-api-endpoints, 09-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Multi-paradigm fusion with weighted aggregation across detection approaches"
    - "Cross-paradigm disagreement detection extending Phase 3 entropy approach to 3 paradigms"
    - "Dataclass-based configuration with validation and serialization"
    - "Structured aggregation output for interpretability and debugging"

key-files:
  created:
    - src/paradigms/aggregation/__init__.py
    - src/paradigms/aggregation/weights.py
    - src/paradigms/aggregation/disagreement.py
    - src/paradigms/aggregation/aggregator.py
    - tests/test_aggregation.py
  modified: []

key-decisions:
  - "Default weights ML=0.5, Rules=0.3, Bayesian=0.2 based on Phase 5 research (ML dominant but not overwhelming)"
  - "Weights must sum to 1.0 with 1e-6 tolerance, soft warnings for out-of-bounds (not errors)"
  - "Normalized Shannon entropy for disagreement: max_H = log2(3) for 3 paradigms"
  - "Disagreement threshold 0.7 consistent with Phase 3 classifier disagreement"
  - "Confidence calculated as 0.5 + |probability - 0.5| (distance from threshold)"
  - "Explanation includes paradigm scores, active rules, and disagreement warnings"

patterns-established:
  - "ParadigmWeights dataclass with validation, to_dict/from_dict for serialization"
  - "Disagreement detection returns structured dict with score, edge case flag, variance, spread"
  - "Aggregator returns 7-key result: prediction, probability, confidence, contributions, disagreement, rules, explanation"
  - "Human-readable explanations with confidence levels (high/moderate/low)"

# Metrics
duration: 4min
completed: 2026-02-12
---

# Phase 05 Plan 03: Multi-Paradigm Aggregation Layer Summary

**One-liner:** Weighted aggregation of ML ensemble (0.5), rule-based (0.3), and Bayesian (0.2) predictions with cross-paradigm disagreement detection using normalized entropy.

## What Was Delivered

### Core Components

1. **ParadigmWeights Management** (`src/paradigms/aggregation/weights.py`)
   - Dataclass with configurable weights for 3 paradigms
   - Validation ensures sum to 1.0 (±1e-6 tolerance)
   - Soft warnings for out-of-range weights (not hard errors)
   - Default: ML ensemble=0.5, Rules=0.3, Bayesian=0.2
   - Serialization: `to_dict()` and `from_dict()` methods

2. **Cross-Paradigm Disagreement Detection** (`src/paradigms/aggregation/disagreement.py`)
   - Extends Phase 3 classifier disagreement approach to 3 paradigms
   - Normalized Shannon entropy: H / log2(3) for [0, 1] scale
   - Returns: score, edge case flag, vote distribution, variance, spread
   - Threshold 0.7 for edge case detection (consistent with Phase 3)
   - `get_disagreement_explanation()` for human-readable output

3. **MultiParadigmAggregator** (`src/paradigms/aggregation/aggregator.py`)
   - `aggregate()` method combines predictions from all 3 paradigms
   - Weighted probability: sum of (weight × paradigm_probability)
   - Final prediction: phishing if probability > 0.5
   - Confidence: 0.5 + |probability - 0.5| (distance from threshold)
   - Returns: prediction, probability, confidence, contributions, disagreement, active_rules, explanation
   - `update_weights()` for dynamic weight adjustment

4. **Test Suite** (`tests/test_aggregation.py`)
   - 20 test cases covering all aggregation functionality
   - TestParadigmWeights: validation, serialization (5 tests)
   - TestParadigmDisagreement: entropy, variance, spread (5 tests)
   - TestDisagreementExplanation: human output (2 tests)
   - TestMultiParadigmAggregator: weighted aggregation, contributions (8 tests)
   - All tests pass in 0.38s

### Requirements Fulfilled

**AGG-01: Multi-paradigm combination**
- ✓ `aggregate()` accepts ml_result, rule_result, bayesian_result
- ✓ Combines probabilities from all three paradigms
- ✓ Paradigm contributions tracked individually

**AGG-02: Disagreement detection**
- ✓ Normalized entropy calculation for 3 paradigms
- ✓ `is_edge_case` flag when score > 0.7
- ✓ Identifies disagreeing paradigms vs majority
- ✓ Calculates probability variance and spread

**AGG-03: Final prediction with confidence**
- ✓ `final_prediction`: 'phishing' or 'legitimate'
- ✓ `final_probability`: weighted sum of paradigm probabilities
- ✓ `confidence`: distance from 0.5 threshold, scaled to [0.5, 1.0]

**AGG-04: Paradigm contributions**
- ✓ Shows each paradigm's probability, weight, weighted_contribution
- ✓ Includes prediction from each paradigm
- ✓ Rule paradigm includes rule_count
- ✓ Active rules list from rule engine

## Task Breakdown

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create paradigm weights management | 96f315f | `weights.py`, `__init__.py` |
| 2 | Create cross-paradigm disagreement detection | b4f32c3 | `disagreement.py` |
| 3 | Implement MultiParadigmAggregator | 12924d3 | `aggregator.py` |
| 4 | Create aggregation test suite | 0ccd6bc | `test_aggregation.py` |

**All tasks completed in 4 minutes.**

## Technical Decisions

### 1. Default Weight Distribution
**Decision:** ML ensemble=0.5, Rules=0.3, Bayesian=0.2

**Rationale:**
- ML ensemble proven most accurate in Phase 4 (96.47% F1 after GA optimization)
- Rules provide interpretability and expert knowledge (30% contribution)
- Bayesian adds probabilistic reasoning (20% as complement)
- Total maintains balance without overwhelming any single paradigm

### 2. Soft Warnings for Weight Bounds
**Decision:** Warn but don't error when weights outside recommended ranges

**Rationale:**
- Hard errors would prevent experimentation
- Users may have domain-specific reasons for unusual weights
- Validation ensures sum=1.0 (critical), bounds are guidance only

### 3. Normalized Entropy for Disagreement
**Decision:** H / log2(3) normalization for 3 paradigms

**Rationale:**
- Consistent with Phase 3 classifier disagreement approach
- Normalized to [0, 1] for easy interpretation
- Max entropy log2(3) = 1.585 for 3 paradigms (vs log2(7) = 2.807 for 7 classifiers)
- Threshold 0.7 remains meaningful for edge case detection

### 4. Confidence as Distance from Threshold
**Decision:** confidence = 0.5 + |probability - 0.5|

**Rationale:**
- Probability near 0.5 indicates low confidence (minimum 0.5)
- Probability near 0.0 or 1.0 indicates high confidence (maximum 1.0)
- Simple, interpretable formula
- Scales linearly with distance from decision boundary

## Integration Points

### Input from Previous Plans
- **05-01 (Rules):** `rule_result` with score, prediction, fired_rules, rule_count
- **05-02 (Bayesian):** `bayesian_result` with posterior_phishing, prediction, confidence
- **03-03 (ML Ensemble):** `ml_result` with ensemble_probability, prediction

### Output Structure
```python
{
    'final_prediction': 'phishing' | 'legitimate',
    'final_probability': float,  # 0-1
    'confidence': float,  # 0.5-1.0
    'paradigm_contributions': {
        'ml_ensemble': {
            'probability': float,
            'weight': float,
            'weighted_contribution': float,
            'prediction': str
        },
        'rules': {
            'probability': float,
            'weight': float,
            'weighted_contribution': float,
            'prediction': str,
            'rule_count': int
        },
        'bayesian': {
            'probability': float,
            'weight': float,
            'weighted_contribution': float,
            'prediction': str
        }
    },
    'disagreement': {
        'score': float,  # 0-1 normalized entropy
        'is_edge_case': bool,
        'vote_distribution': dict,
        'probability_variance': float,
        'disagreeing_paradigms': list,
        'probability_spread': float,
        'paradigm_probabilities': dict
    },
    'active_rules': list,  # From rule engine
    'explanation': str  # Human-readable summary
}
```

### Future Phase Readiness

**For Phase 06 (Integration Layer):**
- ✓ Aggregator ready to integrate with all three paradigms
- ✓ Structured output provides all needed info for API responses
- ✓ Explanation field ready for user-facing display
- ✓ Disagreement detection enables edge case routing

**For Phase 08 (API Endpoints):**
- ✓ Single `aggregate()` method simplifies API design
- ✓ Result dict directly JSON-serializable
- ✓ Explanation field ready for immediate display

**For Phase 09 (Frontend):**
- ✓ Paradigm contributions enable detailed breakdown UI
- ✓ Active rules list shows which rules fired
- ✓ Disagreement warning can trigger manual review prompt

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created all modules simultaneously to avoid import errors**

- **Found during:** Task 1 verification
- **Issue:** `__init__.py` imports `aggregator.py` which didn't exist yet, causing ModuleNotFoundError
- **Fix:** Created stub versions of `disagreement.py` and `aggregator.py` alongside `weights.py`
- **Files modified:** Created all 3 core modules in parallel instead of sequentially
- **Commit:** 96f315f (all modules included)
- **Rationale:** Python module imports are eager, so all dependencies must exist before any can be imported

**2. [Rule 1 - Bug] Fixed numpy boolean comparison in test**

- **Found during:** Task 4 test execution
- **Issue:** `assert result['is_edge_case'] is False` failed due to numpy.False_ != Python False
- **Fix:** Changed `is False` to `== False` for numpy compatibility
- **Files modified:** `tests/test_aggregation.py`
- **Commit:** 0ccd6bc
- **Rationale:** numpy returns numpy.bool_ type which fails identity comparison but passes equality comparison

## Validation Results

### Import Verification
```bash
from src.paradigms.aggregation import MultiParadigmAggregator, ParadigmWeights
# ✓ All modules import successfully
```

### Weight Validation
```bash
ParadigmWeights(0.5, 0.3, 0.2)
# ✓ Default weights sum to 1.0
# ✓ Validation passes
```

### Disagreement Detection
```bash
# Unanimous agreement: score=0.00, edge_case=False
# 2-1 split: score=0.58, dissenters=['rules']
# ✓ Entropy calculation correct
# ✓ Edge case detection working
```

### Full Integration Test
```bash
aggregator = MultiParadigmAggregator()
result = aggregator.aggregate(ml_result, rule_result, bayesian_result)
# ✓ AGG-01: Combines all three paradigms
# ✓ AGG-02: Disagreement detection with edge case flag
# ✓ AGG-03: Final prediction with confidence
# ✓ AGG-04: Paradigm contributions with weights
```

### Test Suite
- 20 tests, all passing in 0.38s
- 100% coverage of core aggregation functionality

## Next Phase Readiness

**Phase 06 (Integration Layer) Prerequisites:**
- ✓ Rule-based system operational (05-01)
- ✓ Bayesian classifier trained (05-02)
- ✓ ML ensemble with 7 classifiers (03-03)
- ✓ Aggregation layer ready to combine all three

**Remaining Phase 5 Work:**
None - Phase 5 complete with all three plans delivered.

**Blockers/Concerns:**
None identified. All three paradigms (ML ensemble, rules, Bayesian) are operational and aggregation layer is ready for integration.

**Phase 6 Can Begin:** Integration layer can now orchestrate feature extraction → 3 paradigms → aggregation → final verdict.

## Self-Check: PASSED

All created files verified:
- ✓ src/paradigms/aggregation/__init__.py
- ✓ src/paradigms/aggregation/weights.py
- ✓ src/paradigms/aggregation/disagreement.py
- ✓ src/paradigms/aggregation/aggregator.py
- ✓ tests/test_aggregation.py

All commits verified:
- ✓ 96f315f: feat(05-03): create paradigm weights management
- ✓ b4f32c3: feat(05-03): create cross-paradigm disagreement detection
- ✓ 12924d3: feat(05-03): implement MultiParadigmAggregator
- ✓ 0ccd6bc: test(05-03): create aggregation test suite
