---
phase: 04-genetic-algorithm-optimization
plan: 01
subsystem: optimization
tags: [genetic-algorithm, deap, mlflow, hyperparameter-tuning, cross-validation]

requires:
  - 03-01: 7 classifier configurations and ensemble infrastructure
  - 03-03: Ensemble prediction system with individual classifier access

provides:
  - GA optimization infrastructure with DEAP framework
  - Hyperparameter search spaces for all 7 classifiers
  - 5-fold CV fitness evaluation with F1-score
  - Evolution loop with elite preservation (HallOfFame)

affects:
  - 04-02: Feature selection optimization (will use same GA infrastructure)
  - 04-03: Ensemble weight optimization (will use search spaces pattern)

tech-stack:
  added:
    - deap: 1.4.3 (genetic algorithm framework)
    - mlflow: 3.1.4 (experiment tracking)
  patterns:
    - DEAP creator/toolbox pattern for GA setup
    - Type-aware hyperparameter encoding (int/float/categorical)
    - Cross-validation fitness to prevent overfitting
    - HallOfFame for elite preservation across generations
    - Tournament selection with tournsize=3 for balanced exploration

key-files:
  created:
    - src/optimization/__init__.py: Module exports
    - src/optimization/search_spaces.py: Hyperparameter ranges for 7 classifiers
    - src/optimization/fitness.py: CV-based fitness evaluation
    - src/optimization/ga_optimizer.py: DEAP toolbox setup and evolution loop
  modified:
    - requirements.txt: Added DEAP and MLflow dependencies

decisions:
  - decision: "Use DEAP 1.4.3 for GA implementation"
    rationale: "Industry standard framework with mature API, extensive documentation, and optimized genetic operators"
    alternatives: "Optuna, Hyperopt (less control over GA specifics), sklearn-genetic-opt (adds abstraction)"

  - decision: "F1-score as fitness metric with 5-fold stratified CV"
    rationale: "F1-score handles class imbalance, CV prevents overfitting to training set"
    alternatives: "Accuracy (biased for imbalanced data), single validation set (higher variance)"

  - decision: "Search spaces 2-3x wider than baseline ranges"
    rationale: "Enables exploration beyond local optima while preventing excessive computational cost"
    impact: "RF n_estimators: 50-300 (baseline: 200), max_depth: 5-30 (baseline: 15)"

  - decision: "Tournament selection with tournsize=3"
    rationale: "Balances selection pressure with diversity maintenance (per research recommendation)"
    alternatives: "Roulette wheel (too weak), tournsize=7 (premature convergence)"

  - decision: "Mutation probability 20% per gene (indpb=0.2)"
    rationale: "Higher than typical 10% to maintain population diversity and prevent premature convergence"
    alternatives: "indpb=0.1 (standard but risks premature convergence for hyperparameter tuning)"

  - decision: "n_jobs=1 in cross_val_score to avoid nested parallelism"
    rationale: "Classifiers already use n_jobs=-1; nested parallelism causes thread thrashing (research pitfall #4)"
    impact: "Each RF CV evaluation takes ~5 seconds; full GA (50×30) takes ~2 hours"

metrics:
  duration: 4 minutes
  completed: 2026-02-11
---

# Phase 04 Plan 01: GA Optimization Infrastructure Summary

**One-liner:** DEAP-based GA optimization with type-aware search spaces, 5-fold CV fitness, and HallOfFame elite preservation for 7 classifiers

## Objective Achieved

Set up complete genetic algorithm optimization infrastructure using DEAP framework and MLflow tracking. Defined bounded hyperparameter search spaces for all 7 classifiers (RF, SVM, MLP, XGBoost, LR, NB, DT) with proper type handling (int, float with log scale, categorical). Implemented fitness evaluation using 5-fold stratified cross-validation with F1-score to prevent overfitting. Created evolution loop with HallOfFame for elite preservation and tournament selection for balanced exploration/exploitation.

## What Was Built

### 1. Dependency Installation (Task 1)
- Added `deap>=1.4.3` to requirements.txt (genetic algorithm framework)
- Added `mlflow>=2.20.0` to requirements.txt (experiment tracking)
- Verified both packages install successfully (DEAP 1.4.3, MLflow 3.1.4)

### 2. Search Spaces and Fitness Module (Task 2)

**search_spaces.py:**
- `SEARCH_SPACES` dict defines bounded ranges for all 7 classifiers
- RF: 4 hyperparameters (n_estimators: 50-300, max_depth: 5-30, min_samples_split: 2-20, min_samples_leaf: 1-10)
- SVM: 3 hyperparameters (C: 0.1-100 log scale, gamma: 0.001-1.0 log scale, kernel: rbf/poly/sigmoid)
- XGBoost: 9 hyperparameters (most complex search space)
- MLP: 3 hyperparameters (hidden_layer_sizes: 50-200, alpha: 0.0001-0.1 log, learning_rate_init: 0.001-0.1 log)
- LR: 2 hyperparameters (C: 0.01-100 log, penalty: l2/none)
- NB: 1 hyperparameter (var_smoothing: 1e-12 to 1e-6 log)
- DT: 4 hyperparameters (max_depth: 5-30, min_samples_split: 2-20, min_samples_leaf: 1-10, criterion: gini/entropy)
- `decode_individual()` converts DEAP individual (list) to typed hyperparameter dict with bounds enforcement
- Handles int casting, float precision, categorical index→choice mapping

**fitness.py:**
- `create_model_from_params()` builds sklearn Pipeline with StandardScaler + classifier from hyperparameters
- Merges GA-optimized params with constant params (class_weight='balanced', random_state=42, etc.)
- `evaluate_individual()` decodes individual, creates model, runs 5-fold stratified CV with F1-score
- Returns tuple `(f1_mean,)` as required by DEAP fitness interface
- Uses `n_jobs=1` in `cross_val_score` to prevent nested parallelism (classifiers use `n_jobs=-1`)
- Gracefully handles invalid hyperparameters by returning `(0.0,)` fitness
- `create_fitness_function()` factory creates closure over training data for toolbox registration

### 3. GA Optimizer with DEAP (Task 3)

**ga_optimizer.py:**
- `setup_toolbox()` creates DEAP toolbox with:
  - `creator.FitnessMax` and `creator.Individual` types
  - Attribute generators for each hyperparameter (int: `random.randint`, float: `random.uniform` with log option, categorical: index)
  - Individual initialization using `tools.initCycle`
  - Population initialization using `tools.initRepeat`
  - Genetic operators: `tools.cxOnePoint` (crossover), `tools.mutUniformInt` (mutation with indpb=0.2), `tools.selTournament` (tournsize=3)
  - Fitness function registered with closure over training data
- `run_ga_optimization()` executes evolution with:
  - Initial random population (default: 50 individuals)
  - `HallOfFame(maxsize=10)` preserves top 10 individuals across generations
  - Statistics tracking (avg, std, min, max fitness)
  - `algorithms.eaSimple` runs evolution loop (default: 30 generations, cxpb=0.7, mutpb=0.2)
  - Returns best individual, logbook with generation stats, hall of fame
- Logging at INFO level for generation progress and final results

### Module Structure
```
src/optimization/
├── __init__.py         # Exports: SEARCH_SPACES, decode_individual, create_fitness_function, setup_toolbox, run_ga_optimization
├── search_spaces.py    # Hyperparameter definitions for 7 classifiers
├── fitness.py          # CV-based fitness evaluation
└── ga_optimizer.py     # DEAP toolbox setup and evolution
```

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add DEAP and MLflow dependencies | d6102a1 | requirements.txt |
| 2 | Create search spaces and fitness function | b4fac28 | src/optimization/__init__.py, search_spaces.py, fitness.py |
| 3 | Create GA optimizer with DEAP toolbox | db95250 | src/optimization/ga_optimizer.py, __init__.py |

## Decisions Made

### 1. DEAP 1.4.3 as GA Framework
**Context:** Multiple GA frameworks available (DEAP, Optuna, Hyperopt, sklearn-genetic-opt)

**Decision:** Use DEAP 1.4.3 directly without sklearn-genetic-opt wrapper

**Rationale:**
- Industry standard with mature API and extensive documentation
- Full control over GA specifics (tournament selection, crossover, mutation)
- sklearn-genetic-opt adds abstraction layer that hides internals
- Research recommends DEAP for academic work requiring transparency

**Tradeoffs:**
- More verbose setup code vs. sklearn-genetic-opt's simpler API
- Need to implement own encode/decode functions
- Benefit: Complete control over evolution process for thesis documentation

### 2. F1-Score with 5-Fold Stratified CV as Fitness
**Context:** Multiple fitness metrics possible (accuracy, F1, precision, recall)

**Decision:** Use F1-score with 5-fold stratified cross-validation

**Rationale:**
- F1-score balances precision and recall, handles class imbalance
- 5-fold CV prevents overfitting to training set (standard practice)
- Stratified CV maintains class distribution in each fold
- Single validation set would have higher variance

**Implementation:**
```python
f1_scorer = make_scorer(f1_score, average='binary')
cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring=f1_scorer, n_jobs=1)
return (cv_scores.mean(),)
```

**Tradeoffs:**
- 5x slower than single train/val split
- More robust fitness estimate (lower variance)
- Each individual evaluation takes ~5 seconds for RF

### 3. Search Spaces 2-3x Wider Than Baseline
**Context:** Must balance exploration (wide ranges) vs. computation (narrow ranges)

**Decision:** Define search spaces 2-3x wider than Phase 3 baseline parameters

**Examples:**
- RF n_estimators: 50-300 (baseline: 200) → 150% wider on each side
- RF max_depth: 5-30 (baseline: 15) → 200% wider
- SVM C: 0.1-100 log scale (baseline: 1.0) → 100x range
- XGBoost learning_rate: 0.01-0.3 (baseline: 0.1) → 30x range

**Rationale:**
- Research recommends 2-3x wider to escape local optima
- Prevents premature convergence within first 10 generations
- Log scale for C, gamma, alpha enables exploration of orders of magnitude
- Upper bounds prevent computational explosion (e.g., n_estimators=1000)

**Tradeoffs:**
- Wider ranges → longer convergence time
- Benefit: More likely to find global optima vs. local optima near baseline

### 4. Tournament Selection with tournsize=3
**Context:** Selection pressure affects exploration/exploitation balance

**Decision:** Use `tools.selTournament` with `tournsize=3`

**Rationale:**
- Tournament size 2-3 is standard for hyperparameter tuning (research recommendation)
- Lower than typical 5-7 used for structural GA problems
- Maintains population diversity while still favoring better individuals
- Prevents premature convergence (pitfall #1 in research)

**Alternatives considered:**
- Roulette wheel: Too weak, doesn't apply enough selection pressure
- tournsize=7: Too strong, causes premature convergence to local optima
- tournsize=2: Slightly weaker, but 3 is more standard

### 5. Mutation Probability 20% Per Gene
**Context:** Mutation rate affects population diversity

**Decision:** Use `indpb=0.2` (20% chance to mutate each gene)

**Rationale:**
- Higher than typical 10% mutation rate for hyperparameter tuning
- Maintains diversity to prevent premature convergence
- Research pitfall #1 warning: "mutation probability too low (e.g., 0.05) doesn't maintain diversity"
- For 4-parameter RF, expected 0.8 mutations per individual (healthy churn)

**Tradeoffs:**
- Higher mutation → slower convergence
- Benefit: More robust exploration of search space
- Lower risk of getting stuck in local optima

### 6. Avoid Nested Parallelism
**Context:** Both sklearn classifiers and cross_val_score support parallelization

**Decision:** Set `n_jobs=1` in `cross_val_score`, keep `n_jobs=-1` in classifiers

**Rationale:**
- Research pitfall #4: "Nested parallelism causes thread thrashing"
- 50 individuals × 5 CV folds × 8 cores = 2000 threads (system overload)
- Parallelizing at classifier level more efficient (lower overhead)
- Prevents CPU thrashing and memory issues

**Implementation:**
```python
cv_scores = cross_val_score(
    model, X_train, y_train,
    cv=5, scoring=f1_scorer,
    n_jobs=1  # Serial CV, parallel within classifier
)
```

**Performance impact:**
- Each RF evaluation: ~5 seconds
- Full GA (50 population × 30 generations): ~2 hours wallclock time

## Verification Results

All verification commands passed:

1. **Dependencies installed:**
   ```
   DEAP OK
   MLflow 3.1.4 OK
   ```

2. **Module imports:**
   ```
   Search spaces for 7 classifiers
   RF decoded: {'n_estimators': 200, 'max_depth': 15, 'min_samples_split': 10, 'min_samples_leaf': 5}
   Search spaces and fitness module OK
   ```

3. **GA smoke test (2 generations):**
   ```
   gen	nevals	avg     	std      	min    	max
   0  	10    	0.399834	0.0191908	0.36911	0.442999
   1  	7     	0.387104	0.0418134	0.317564	0.439954
   2  	8     	0.406864	0.0287696	0.360501	0.457097
   Best individual: [231, 14, 4, 3]
   Best fitness: 0.4571
   GA optimizer OK
   ```

4. **Comprehensive import test:**
   ```
   All exports available
   Classifiers with search spaces: ['rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt']
   ```

## Technical Highlights

### 1. Type-Aware Hyperparameter Encoding
Search spaces specify parameter types with validation:
```python
'n_estimators': {'type': 'int', 'low': 50, 'high': 300}
'C': {'type': 'float', 'low': 0.1, 'high': 100.0, 'log': True}
'kernel': {'type': 'categorical', 'choices': ['rbf', 'poly', 'sigmoid']}
```

Decode function enforces types and bounds:
```python
if param_spec['type'] == 'int':
    value = max(param_spec['low'], min(param_spec['high'], int(value)))
```

Prevents sklearn `TypeError: 'numpy.float64' object cannot be interpreted as an integer`

### 2. Log-Scale Sampling for Order-of-Magnitude Parameters
For C, gamma, alpha (vary across orders of magnitude):
```python
if param_spec.get('log', False):
    log_low = np.log10(param_spec['low'])
    log_high = np.log10(param_spec['high'])
    toolbox.register(attr_name, lambda: 10 ** random.uniform(log_low, log_high))
```

Enables uniform exploration in log space (e.g., C: 0.1, 1.0, 10, 100)

### 3. Graceful Handling of Invalid Hyperparameters
GA can generate invalid combinations (e.g., min_samples_leaf > min_samples_split):
```python
try:
    model = create_model_from_params(classifier_name, params)
    cv_scores = cross_val_score(...)
    return (cv_scores.mean(),)
except Exception as e:
    logger.warning(f"Failed to evaluate: {e}. Returning zero fitness.")
    return (0.0,)
```

Prevents evolution crash, naturally selects against invalid individuals

### 4. HallOfFame for Elite Preservation
Tracks top 10 individuals across all generations:
```python
hof = tools.HallOfFame(maxsize=10)
population, logbook = algorithms.eaSimple(
    population, toolbox, ...,
    halloffame=hof
)
```

Prevents research pitfall #5: "Loss of best individual through elitism failure"

## Integration Points

### With Phase 3 (ML Ensemble)
- Uses `CLASSIFIER_CONFIGS` from `src/models/classifiers.py` as baseline
- Fitness evaluation creates same Pipeline structure (StandardScaler + classifier)
- Constant parameters (class_weight='balanced', probability=True) preserved

### For Phase 4 Plan 02 (Feature Selection)
- Same `setup_toolbox()` and `run_ga_optimization()` functions reusable
- Feature selection will have binary search space (0/1 per feature)
- Fitness function will need to filter features before CV evaluation

### For Phase 4 Plan 03 (Ensemble Weight Optimization)
- Can reuse search space pattern for weight ranges (0.0-1.0 per classifier)
- Fitness function will evaluate weighted ensemble predictions
- Smaller search space (7 weights vs. 9 hyperparameters for XGBoost)

## Deviations from Plan

None - plan executed exactly as written.

All 3 tasks completed:
1. DEAP and MLflow dependencies installed
2. Search spaces and fitness module created with all exports
3. GA optimizer implemented with toolbox setup and evolution loop

All verification commands passed on first attempt.

## Next Phase Readiness

**Phase 4 Plan 02 (Feature Selection Optimization) is READY:**
- GA infrastructure complete and tested
- Can immediately proceed to binary feature selection search space
- Estimated effort: 1-2 hours (simpler search space than hyperparameters)

**Dependencies satisfied:**
- DEAP framework operational
- Cross-validation fitness evaluation proven
- HallOfFame elite preservation working
- Search space pattern established

**Computational considerations for future plans:**
- Each classifier GA run: ~2 hours (50 population × 30 generations × 5s per evaluation)
- Feature selection GA: faster (~30 min, simpler models with reduced features)
- Ensemble weight GA: fastest (~15 min, no model training, just weighted voting)
- Total Phase 4 computational budget: ~16 hours for all optimizations

**Open questions for Plan 02:**
- Should feature selection use wrapper (evaluate model performance) or filter (correlation-based) approach?
- Recommendation: Wrapper method with GA for consistency with hyperparameter optimization

**Open questions for Plan 03:**
- Should ensemble weights be normalized to sum to 1.0, or allowed any positive values?
- Recommendation: Unnormalized weights (sklearn VotingClassifier handles normalization internally)

## Self-Check: PASSED

All created files exist:
```
FOUND: src/optimization/__init__.py
FOUND: src/optimization/search_spaces.py
FOUND: src/optimization/fitness.py
FOUND: src/optimization/ga_optimizer.py
```

All commits exist:
```
FOUND: d6102a1 (Task 1: dependencies)
FOUND: b4fac28 (Task 2: search spaces and fitness)
FOUND: db95250 (Task 3: GA optimizer)
```
