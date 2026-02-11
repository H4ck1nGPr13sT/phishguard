# Phase 4: Genetic Algorithm Optimization - Research

**Researched:** 2026-02-11
**Domain:** Genetic Algorithm Hyperparameter Optimization with DEAP and MLflow
**Confidence:** HIGH

## Summary

Genetic algorithm (GA) hyperparameter optimization for machine learning models is a well-established alternative to grid search and random search, offering superior time efficiency while exploring large search spaces. DEAP (Distributed Evolutionary Algorithms in Python) version 1.4.3 provides the standard framework for implementing evolutionary algorithms in Python, with robust support for custom fitness functions, genetic operators, and population management.

The project will optimize hyperparameters for all 7 existing classifiers (RF, SVM, MLP, XGBoost, LR, NB, DT) using tournament selection, single-point crossover, and mutation operators. MLflow provides comprehensive experiment tracking, model versioning, and performance comparison capabilities. The standard pattern integrates DEAP's evolutionary loop with sklearn's cross_val_score for fitness evaluation, using 5-fold cross-validation to maximize F1-score.

A critical challenge is premature convergence—where GAs settle on local optima before exploring the full search space. Prevention strategies include maintaining population diversity through appropriate mutation rates (typically 10-20%), using tournament selection with size 2-3 to balance exploration/exploitation, and tracking fitness history across generations to detect convergence plateaus.

**Primary recommendation:** Use DEAP 1.4.3 with sklearn-genetic-opt patterns for clean integration, MLflow nested runs for per-generation tracking, and conservative hyperparameter search spaces based on domain knowledge from Phase 3 baseline models.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| DEAP | 1.4.3 | Evolutionary algorithm framework | De facto standard for GA in Python, mature API, excellent documentation |
| MLflow | ≥2.20.0 | Experiment tracking and model versioning | Industry standard for ML lifecycle management, native Python API |
| scikit-learn | ≥1.4.0 | ML models and cross-validation | Already in use (Phase 3), provides cross_val_score for fitness |
| NumPy | ≥1.26.0 | Numerical operations | Required by DEAP, already in use |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sklearn-genetic-opt | 0.12.0 | Reference patterns for DEAP-sklearn integration | Study API patterns, not direct dependency (adds abstraction) |
| joblib | ≥1.3.0 | Model serialization | Already in use (Phase 2), needed for saving optimized models |
| pandas | ≥2.0.0 | Data manipulation | Already in use, needed for metrics tracking |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| DEAP | Optuna, Hyperopt | More automated but less control over GA specifics (tournament, crossover) |
| DEAP | sklearn-genetic-opt | Cleaner API but adds abstraction layer, hides GA internals |
| MLflow | TensorBoard, Weights & Biases | Less mature for classical ML, overkill for this scope |
| Custom GA | DEAP | Reinventing wheel, no advantage for academic requirements |

**Installation:**
```bash
pip install deap>=1.4.3 mlflow>=2.20.0
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── optimization/
│   ├── __init__.py
│   ├── ga_optimizer.py        # Main GA optimization logic
│   ├── search_spaces.py       # Hyperparameter definitions per classifier
│   ├── fitness.py             # Fitness function with cross-validation
│   └── mlflow_tracker.py      # MLflow logging utilities
├── models/
│   ├── train.py               # Existing baseline training
│   └── train_optimized.py     # Train with GA-optimized hyperparameters
└── scripts/
    └── run_ga_optimization.py # CLI entry point for optimization runs
```

### Pattern 1: DEAP Creator and Toolbox Setup
**What:** Functional approach to defining evolutionary algorithm components using creator factory and toolbox registry

**When to use:** Start of every GA optimization script, before evolutionary loop

**Example:**
```python
# Source: https://deap.readthedocs.io/en/master/examples/ga_onemax.html
from deap import base, creator, tools
import random

# Define fitness (maximize F1-score)
creator.create("FitnessMax", base.Fitness, weights=(1.0,))
creator.create("Individual", list, fitness=creator.FitnessMax)

# Setup toolbox
toolbox = base.Toolbox()

# Register attribute generators for hyperparameters
# Example for Random Forest:
toolbox.register("attr_n_estimators", random.randint, 50, 300)
toolbox.register("attr_max_depth", random.randint, 5, 30)
toolbox.register("attr_min_samples_split", random.randint, 2, 20)

# Create individual as list of hyperparameters
toolbox.register("individual", tools.initCycle, creator.Individual,
                 (toolbox.attr_n_estimators, toolbox.attr_max_depth,
                  toolbox.attr_min_samples_split), n=1)

# Create population
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

# Register genetic operators
toolbox.register("evaluate", fitness_function)  # Custom fitness
toolbox.register("mate", tools.cxOnePoint)      # Single-point crossover
toolbox.register("mutate", tools.mutUniformInt,
                 low=[50, 5, 2], up=[300, 30, 20], indpb=0.2)
toolbox.register("select", tools.selTournament, tournsize=3)
```

### Pattern 2: Fitness Function with Cross-Validation
**What:** Fitness evaluation using sklearn cross-validation to prevent overfitting

**When to use:** Every individual evaluation in GA loop

**Example:**
```python
# Source: sklearn-genetic-opt patterns, sklearn docs
from sklearn.model_selection import cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import make_scorer, f1_score

def evaluate_individual(individual, X_train, y_train):
    """
    Evaluate fitness of individual (hyperparameter set).

    Args:
        individual: List of hyperparameters [n_estimators, max_depth, ...]
        X_train: Training features
        y_train: Training labels

    Returns:
        Tuple with single fitness value (F1-score)
    """
    # Decode individual to hyperparameters
    n_estimators, max_depth, min_samples_split = individual

    # Create model with these hyperparameters
    model = RandomForestClassifier(
        n_estimators=int(n_estimators),
        max_depth=int(max_depth),
        min_samples_split=int(min_samples_split),
        random_state=42,
        n_jobs=-1
    )

    # Evaluate with 5-fold CV
    f1_scorer = make_scorer(f1_score, average='binary')
    cv_scores = cross_val_score(
        model, X_train, y_train,
        cv=5, scoring=f1_scorer, n_jobs=1  # n_jobs=1 to avoid nested parallelism
    )

    # Return mean F1 as fitness (DEAP requires tuple)
    return (cv_scores.mean(),)
```

### Pattern 3: Evolutionary Loop with HallOfFame
**What:** Main GA iteration with elite preservation and convergence tracking

**When to use:** After toolbox setup, runs for N generations

**Example:**
```python
# Source: https://deap.readthedocs.io/en/master/api/tools.html
from deap import algorithms, tools
import numpy as np

def run_ga_optimization(toolbox, population_size=50, n_generations=30,
                        cxpb=0.7, mutpb=0.2):
    """
    Run genetic algorithm optimization.

    Args:
        toolbox: Configured DEAP toolbox
        population_size: Number of individuals per generation
        n_generations: Number of generations to evolve
        cxpb: Crossover probability (70% standard)
        mutpb: Mutation probability (20% standard)

    Returns:
        Best individual, fitness history, hall of fame
    """
    # Create initial population
    population = toolbox.population(n=population_size)

    # Hall of Fame tracks top N individuals
    hof = tools.HallOfFame(maxsize=10)

    # Statistics tracking
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", np.mean)
    stats.register("std", np.std)
    stats.register("min", np.min)
    stats.register("max", np.max)

    # Run evolution
    population, logbook = algorithms.eaSimple(
        population, toolbox,
        cxpb=cxpb,           # Crossover probability
        mutpb=mutpb,         # Mutation probability
        ngen=n_generations,  # Number of generations
        stats=stats,
        halloffame=hof,
        verbose=True
    )

    return hof[0], logbook, hof  # Best individual, history, top 10
```

### Pattern 4: MLflow Nested Runs for GA Tracking
**What:** Parent run for GA optimization, child runs for each generation

**When to use:** Wrap GA loop to track fitness evolution over generations

**Example:**
```python
# Source: https://mlflow.org/docs/latest/ml/tracking/
import mlflow

def optimize_with_mlflow(classifier_name, X_train, y_train, search_space):
    """
    Run GA optimization with MLflow tracking.

    Args:
        classifier_name: e.g., 'rf', 'svm', 'xgb'
        X_train, y_train: Training data
        search_space: Dict defining hyperparameter ranges
    """
    # Parent run for entire GA optimization
    with mlflow.start_run(run_name=f"ga_optimize_{classifier_name}"):
        # Log search space configuration
        mlflow.log_params({
            "classifier": classifier_name,
            "population_size": 50,
            "n_generations": 30,
            "crossover_prob": 0.7,
            "mutation_prob": 0.2
        })

        # Setup GA components
        toolbox = setup_toolbox(classifier_name, search_space, X_train, y_train)
        population = toolbox.population(n=50)
        hof = tools.HallOfFame(10)

        # Run evolution with per-generation logging
        for gen in range(30):
            # Create nested run for this generation
            with mlflow.start_run(run_name=f"generation_{gen}", nested=True):
                # Evaluate population
                fitnesses = list(map(toolbox.evaluate, population))
                for ind, fit in zip(population, fitnesses):
                    ind.fitness.values = fit

                # Log generation statistics
                fits = [ind.fitness.values[0] for ind in population]
                mlflow.log_metrics({
                    "gen_avg_fitness": np.mean(fits),
                    "gen_max_fitness": np.max(fits),
                    "gen_min_fitness": np.min(fits),
                    "gen_std_fitness": np.std(fits)
                }, step=gen)

                # Select, crossover, mutate
                offspring = toolbox.select(population, len(population))
                offspring = algorithms.varAnd(offspring, toolbox, cxpb=0.7, mutpb=0.2)
                population[:] = offspring

                hof.update(population)

        # Log best hyperparameters
        best_individual = hof[0]
        mlflow.log_params({
            "best_n_estimators": int(best_individual[0]),
            "best_max_depth": int(best_individual[1]),
            # ... other hyperparameters
        })
        mlflow.log_metric("best_f1_score", hof[0].fitness.values[0])

        return hof[0]
```

### Pattern 5: Hyperparameter Search Space Definition
**What:** Structured definition of search ranges per classifier, informed by domain knowledge

**When to use:** Before GA setup, defines boundaries for mutation and initialization

**Example:**
```python
# Source: Research on GA hyperparameter optimization for RF, SVM, XGBoost
# https://pmc.ncbi.nlm.nih.gov/articles/PMC10892895/ (XGBoost GA study)

SEARCH_SPACES = {
    'rf': {
        'n_estimators': {'type': 'int', 'low': 50, 'high': 300},
        'max_depth': {'type': 'int', 'low': 5, 'high': 30},
        'min_samples_split': {'type': 'int', 'low': 2, 'high': 20},
        'min_samples_leaf': {'type': 'int', 'low': 1, 'high': 10},
        # class_weight='balanced' kept constant (Phase 3 decision)
    },
    'svm': {
        'C': {'type': 'float', 'low': 0.1, 'high': 100.0, 'log': True},
        'gamma': {'type': 'float', 'low': 0.001, 'high': 1.0, 'log': True},
        'kernel': {'type': 'categorical', 'choices': ['rbf', 'poly', 'sigmoid']},
        # probability=True kept constant (required for soft voting)
    },
    'xgb': {
        'n_estimators': {'type': 'int', 'low': 50, 'high': 300},
        'max_depth': {'type': 'int', 'low': 3, 'high': 10},
        'learning_rate': {'type': 'float', 'low': 0.01, 'high': 0.3, 'log': True},
        'subsample': {'type': 'float', 'low': 0.6, 'high': 1.0},
        'colsample_bytree': {'type': 'float', 'low': 0.6, 'high': 1.0},
        'gamma': {'type': 'float', 'low': 0.0, 'high': 5.0},
        'min_child_weight': {'type': 'int', 'low': 1, 'high': 10},
        'reg_alpha': {'type': 'float', 'low': 0.0, 'high': 1.0},
        'reg_lambda': {'type': 'float', 'low': 0.0, 'high': 1.0},
        # n_jobs=1 kept constant (Phase 3 decision)
    },
    'mlp': {
        'hidden_layer_sizes': {'type': 'int', 'low': 50, 'high': 200},  # Single layer
        'alpha': {'type': 'float', 'low': 0.0001, 'high': 0.1, 'log': True},
        'learning_rate_init': {'type': 'float', 'low': 0.001, 'high': 0.1, 'log': True},
        # activation='relu', solver='adam' kept constant
    },
    'lr': {
        'C': {'type': 'float', 'low': 0.01, 'high': 100.0, 'log': True},
        'penalty': {'type': 'categorical', 'choices': ['l2', 'none']},
        # class_weight='balanced' kept constant
    },
    'nb': {
        'var_smoothing': {'type': 'float', 'low': 1e-12, 'high': 1e-6, 'log': True},
    },
    'dt': {
        'max_depth': {'type': 'int', 'low': 5, 'high': 30},
        'min_samples_split': {'type': 'int', 'low': 2, 'high': 20},
        'min_samples_leaf': {'type': 'int', 'low': 1, 'high': 10},
        'criterion': {'type': 'categorical', 'choices': ['gini', 'entropy']},
        # class_weight='balanced' kept constant
    }
}
```

### Pattern 6: Model Versioning with MLflow Registry
**What:** Register baseline and optimized models with version tags for comparison

**When to use:** After GA optimization completes, save both baseline and optimized models

**Example:**
```python
# Source: https://mlflow.org/docs/latest/ml/model-registry/
import mlflow
from mlflow.models import infer_signature

def save_baseline_and_optimized(classifier_name, baseline_model, optimized_model,
                                 X_train, y_train, baseline_metrics, optimized_metrics):
    """
    Register both baseline and optimized models in MLflow Model Registry.

    Args:
        classifier_name: e.g., 'rf', 'svm'
        baseline_model: Trained sklearn Pipeline with default params
        optimized_model: Trained sklearn Pipeline with GA-optimized params
        X_train, y_train: Training data for signature inference
        baseline_metrics, optimized_metrics: Dict with accuracy, f1, etc.
    """
    registered_model_name = f"phishing_detector_{classifier_name}"

    # Infer model signature
    signature = infer_signature(X_train, baseline_model.predict(X_train))

    # Log baseline model
    with mlflow.start_run(run_name=f"{classifier_name}_baseline"):
        mlflow.log_params(baseline_model.get_params())
        mlflow.log_metrics(baseline_metrics)

        mlflow.sklearn.log_model(
            baseline_model,
            artifact_path="model",
            registered_model_name=registered_model_name,
            signature=signature
        )

        # Tag as baseline version
        client = mlflow.tracking.MlflowClient()
        latest_version = client.search_model_versions(
            f"name='{registered_model_name}'"
        )[0].version
        client.set_model_version_tag(
            registered_model_name, latest_version, "type", "baseline"
        )

    # Log optimized model
    with mlflow.start_run(run_name=f"{classifier_name}_ga_optimized"):
        mlflow.log_params(optimized_model.get_params())
        mlflow.log_metrics(optimized_metrics)

        # Log improvement metrics
        improvement_metrics = {
            f"{metric}_improvement": optimized_metrics[metric] - baseline_metrics[metric]
            for metric in baseline_metrics.keys()
        }
        mlflow.log_metrics(improvement_metrics)

        mlflow.sklearn.log_model(
            optimized_model,
            artifact_path="model",
            registered_model_name=registered_model_name,
            signature=signature
        )

        # Tag as optimized version
        client = mlflow.tracking.MlflowClient()
        latest_version = client.search_model_versions(
            f"name='{registered_model_name}'"
        )[0].version
        client.set_model_version_tag(
            registered_model_name, latest_version, "type", "ga_optimized"
        )
        client.set_model_version_tag(
            registered_model_name, latest_version, "ga_generations", "30"
        )
```

### Anti-Patterns to Avoid

- **Nested parallelism in fitness function:** Setting `n_jobs=-1` in both cross_val_score and model causes thread thrashing. Use `n_jobs=1` in cross_val_score when model uses `n_jobs=-1`.

- **Training on full dataset after CV:** Fitness function should only use cross-validation scores, not retrain on full data. This prevents overfitting to training set.

- **Ignoring elite preservation:** Not using HallOfFame means best solutions can be lost to mutation/crossover. Always track top N individuals.

- **Fixed mutation rate throughout evolution:** Standard DEAP uses constant mutation probability. For hyperparameter tuning, this is acceptable, but adaptive mutation (higher early, lower late) can improve convergence.

- **Evaluating invalid hyperparameters:** GA can generate invalid combinations (e.g., negative values). Add validation/clipping in fitness function to return zero fitness for invalid individuals.

- **Not tracking convergence:** If fitness plateaus for 5+ generations, GA may be stuck. Log fitness history and implement early stopping callback.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Genetic algorithm framework | Custom GA implementation | DEAP 1.4.3 | Tournament selection, crossover, mutation operators already optimized; extensive testing |
| MLflow experiment tracking | Custom logging to CSV/JSON | MLflow ≥2.20.0 | Model registry, versioning, UI, artifact storage built-in |
| Cross-validation | Manual k-fold splits | `sklearn.model_selection.cross_val_score` | Handles stratification, edge cases, parallelization correctly |
| Hyperparameter encoding | Manual list-to-dict conversion | Systematic encode/decode functions | Type safety (int/float/categorical), bounds checking critical |
| Early stopping | Manual convergence detection | DEAP with custom callback | Fitness plateau detection needs statistical tests, not simple comparison |
| Population diversity tracking | Custom diversity metrics | DEAP `selTournament` with proper `tournsize` | Tournament selection automatically maintains diversity when configured correctly |

**Key insight:** Genetic algorithms have many subtle implementation details (fitness invalidation after mutation, elitism, selection pressure) that are easy to get wrong. DEAP encapsulates decades of evolutionary computation research. For MLflow, model versioning and comparison UI alone justify using the framework vs. hand-rolling.

## Common Pitfalls

### Pitfall 1: Premature Convergence to Local Optima
**What goes wrong:** GA converges to suboptimal hyperparameters within first 10 generations, never explores better regions of search space. All individuals become similar, losing population diversity.

**Why it happens:**
- Tournament selection with `tournsize` too high (e.g., 7-10) creates excessive selection pressure
- Mutation probability too low (e.g., 0.05) doesn't maintain diversity
- Population size too small (e.g., 10-20) limits exploration
- Search space too narrow (e.g., `max_depth` 8-12) prevents finding better ranges

**How to avoid:**
- Use `tournsize=2` or `tournsize=3` (standard for hyperparameter tuning)
- Set mutation probability `mutpb=0.15-0.20` (higher than typical 0.1)
- Population size ≥50 for 3-5 hyperparameters, ≥100 for 8+ hyperparameters
- Define search spaces 2-3x wider than baseline parameter ranges
- Track fitness standard deviation—if drops below 0.01 after gen 5, diversity lost

**Warning signs:**
- Fitness plateaus after generation 5-10
- `gen_std_fitness` drops to near-zero early in evolution
- All individuals in population have nearly identical fitness
- Best solution from generation 5 same as generation 30

### Pitfall 2: Overfitting to Training Set via Fitness Function
**What goes wrong:** GA finds hyperparameters with 99% training accuracy but poor generalization. Optimized models perform worse than baseline on test data.

**Why it happens:**
- Fitness function uses training accuracy instead of cross-validation
- Cross-validation uses same random seed every evaluation (memorization)
- CV folds too few (e.g., 2-3) or not stratified for imbalanced data
- Fitness function retrains on full train set after CV (data leakage)

**How to avoid:**
- ALWAYS use cross-validation for fitness (5-fold standard, stratified for imbalance)
- Use F1-score for imbalanced datasets, not accuracy
- Set different `random_state` for CV splits vs. model training (or use None)
- Fitness function returns ONLY the CV score—never retrain on full data
- Validate on separate holdout set after GA completes

**Warning signs:**
- Fitness improves every generation but test performance degrades
- Large gap between CV score (fitness) and test score (>5%)
- Optimized model test accuracy < baseline test accuracy
- Fitness values exceeding human expectations (e.g., F1=0.99 on difficult dataset)

### Pitfall 3: Type Mismatch in Hyperparameter Decoding
**What goes wrong:** sklearn raises `TypeError: 'numpy.float64' object cannot be interpreted as an integer` when passing GA-generated hyperparameters to classifier constructors.

**Why it happens:**
- DEAP represents individuals as lists of floats by default
- sklearn requires strict types: `int` for `n_estimators`, `float` for `C`, `str` for `kernel`
- Mutation operators can produce float values for integer parameters
- No validation between GA encoding and sklearn decoding

**How to avoid:**
- Explicitly cast to correct types in fitness function: `int(individual[0])`
- Use `tools.mutUniformInt` for integer parameters, not `tools.mutGaussian`
- Create encode/decode utility functions with type checking
- Validate individual before fitness evaluation, return 0.0 fitness for invalid types
- Use bounds checking: `max(5, min(30, int(max_depth)))` to prevent out-of-range

**Warning signs:**
- Sporadic `TypeError` during fitness evaluation (fails for some individuals)
- sklearn warning: "A column-vector y was passed when a 1d array was expected"
- Negative values for parameters that must be positive
- Float values like 150.73 for `n_estimators` (should be 150 or 151)

### Pitfall 4: Computational Explosion from Nested Parallelism
**What goes wrong:** GA optimization takes 10x longer than expected. CPU usage spikes to 100% but progress is slow. System becomes unresponsive.

**Why it happens:**
- `cross_val_score(n_jobs=-1)` + classifier `n_jobs=-1` creates N×M threads
- For 50 individuals × 5 CV folds × 8 cores = 2000 threads (thrashing)
- Each generation waits for stragglers to finish
- Thread creation/destruction overhead exceeds computation time

**How to avoid:**
- Set `n_jobs=1` in `cross_val_score` when parallelizing at population level
- OR set classifier `n_jobs=1` and parallelize CV folds (`n_jobs=-1`)
- Never parallelize both population evaluation AND cross-validation
- Monitor CPU usage—should be 100% but not >200% (indicates thrashing)
- For 50 individuals with 5-fold CV, total jobs = 250; use 1 or the other

**Warning signs:**
- Each generation takes 5-10 minutes (should be 30-60 seconds)
- CPU usage >200% on 8-core machine (indicates over-subscription)
- `htop` shows hundreds of Python processes
- Memory usage climbing steadily (thread stack overflow)

### Pitfall 5: Loss of Best Individual Through Elitism Failure
**What goes wrong:** Best fitness in generation 15 is better than best fitness in generation 30 (final). Optimization regresses instead of progressing.

**Why it happens:**
- Not using `HallOfFame` to preserve elite individuals
- `algorithms.eaSimple` replaces entire population each generation
- Crossover/mutation can destroy good solutions without backup
- Selection pressure too low—bad individuals survive and reproduce

**How to avoid:**
- ALWAYS use `tools.HallOfFame(maxsize=10)` minimum
- Pass `halloffame=hof` to `algorithms.eaSimple`
- Verify `hof[0].fitness.values` never decreases across generations
- Consider `algorithms.eaMuPlusLambda` (μ+λ) for explicit elitism
- Log best fitness every generation—should monotonically increase

**Warning signs:**
- Best fitness oscillates or decreases between generations
- Final best individual worse than mid-evolution individuals
- `hof[0]` has lower fitness than individuals seen earlier
- No clear fitness improvement trend in logbook

### Pitfall 6: MLflow Run Clutter from Poor Organization
**What goes wrong:** MLflow UI shows 1000+ runs with cryptic names like "run_20260211_143022". Can't find which run corresponds to which classifier. Nested runs don't group properly.

**Why it happens:**
- Not using `run_name` parameter in `mlflow.start_run()`
- Not tagging runs with classifier name, generation, or experiment type
- Creating new experiment for each run instead of grouping
- Nested runs created without proper parent-child relationship

**How to avoid:**
- Set descriptive run names: `run_name=f"ga_optimize_{classifier_name}"`
- Use MLflow tags: `mlflow.set_tag("classifier", "rf")`, `mlflow.set_tag("phase", "4")`
- Create single experiment for GA optimization: `mlflow.set_experiment("phase_4_ga_optimization")`
- Use `nested=True` for generation-level runs under classifier-level parent
- Log hyperparameters with classifier prefix: `mlflow.log_param("rf_n_estimators", 200)`

**Warning signs:**
- Can't distinguish baseline vs. optimized runs in UI
- Need to open every run to find specific classifier
- Nested runs appear as top-level runs (not grouped)
- Run list exceeds 100 entries for single optimization task

## Code Examples

Verified patterns from official sources:

### Example 1: Complete GA Setup for Random Forest Optimization
```python
# Source: Synthesized from DEAP docs + sklearn-genetic-opt patterns
from deap import base, creator, tools, algorithms
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.metrics import make_scorer, f1_score
import numpy as np
import random

def setup_rf_optimization(X_train, y_train):
    """
    Complete DEAP setup for Random Forest hyperparameter optimization.
    """
    # Define fitness (maximize F1-score)
    creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    creator.create("Individual", list, fitness=creator.FitnessMax)

    # Define search space bounds
    BOUNDS = {
        'n_estimators': (50, 300),
        'max_depth': (5, 30),
        'min_samples_split': (2, 20),
        'min_samples_leaf': (1, 10)
    }

    # Setup toolbox
    toolbox = base.Toolbox()

    # Register attribute generators (one per hyperparameter)
    toolbox.register("attr_n_estimators", random.randint, *BOUNDS['n_estimators'])
    toolbox.register("attr_max_depth", random.randint, *BOUNDS['max_depth'])
    toolbox.register("attr_min_samples_split", random.randint, *BOUNDS['min_samples_split'])
    toolbox.register("attr_min_samples_leaf", random.randint, *BOUNDS['min_samples_leaf'])

    # Create individual structure
    toolbox.register("individual", tools.initCycle, creator.Individual,
                     (toolbox.attr_n_estimators, toolbox.attr_max_depth,
                      toolbox.attr_min_samples_split, toolbox.attr_min_samples_leaf),
                     n=1)

    # Create population
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    # Fitness function with 5-fold CV
    def evaluate_rf(individual):
        n_estimators, max_depth, min_samples_split, min_samples_leaf = individual

        # Type casting and bounds enforcement
        n_estimators = max(50, min(300, int(n_estimators)))
        max_depth = max(5, min(30, int(max_depth)))
        min_samples_split = max(2, min(20, int(min_samples_split)))
        min_samples_leaf = max(1, min(10, int(min_samples_leaf)))

        model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            min_samples_leaf=min_samples_leaf,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        )

        f1_scorer = make_scorer(f1_score, average='binary')
        cv_scores = cross_val_score(
            model, X_train, y_train,
            cv=5, scoring=f1_scorer, n_jobs=1  # Avoid nested parallelism
        )

        return (cv_scores.mean(),)

    # Register genetic operators
    toolbox.register("evaluate", evaluate_rf)
    toolbox.register("mate", tools.cxOnePoint)
    toolbox.register("mutate", tools.mutUniformInt,
                     low=[BOUNDS['n_estimators'][0], BOUNDS['max_depth'][0],
                          BOUNDS['min_samples_split'][0], BOUNDS['min_samples_leaf'][0]],
                     up=[BOUNDS['n_estimators'][1], BOUNDS['max_depth'][1],
                         BOUNDS['min_samples_split'][1], BOUNDS['min_samples_leaf'][1]],
                     indpb=0.2)  # 20% chance to mutate each gene
    toolbox.register("select", tools.selTournament, tournsize=3)

    return toolbox, BOUNDS

# Usage
toolbox, bounds = setup_rf_optimization(X_train, y_train)
population = toolbox.population(n=50)
hof = tools.HallOfFame(10)

# Run evolution
final_pop, logbook = algorithms.eaSimple(
    population, toolbox,
    cxpb=0.7, mutpb=0.2, ngen=30,
    halloffame=hof, verbose=True
)

print(f"Best hyperparameters: {hof[0]}")
print(f"Best F1-score: {hof[0].fitness.values[0]:.4f}")
```

### Example 2: Baseline vs. Optimized Comparison Script
```python
# Source: MLflow model comparison patterns
import mlflow
from sklearn.metrics import classification_report, f1_score, accuracy_score
from sklearn.model_selection import cross_val_score
import pandas as pd

def compare_baseline_vs_optimized(classifier_name, baseline_params, optimized_params,
                                   X_train, y_train, X_test, y_test):
    """
    Train and compare baseline vs. GA-optimized models.

    Returns comparison metrics showing improvement.
    """
    mlflow.set_experiment("phase_4_ga_evaluation")

    results = {}

    # Train baseline model
    with mlflow.start_run(run_name=f"{classifier_name}_baseline_comparison"):
        # Create baseline model (Phase 3 hyperparameters)
        baseline_model = create_model_from_params(classifier_name, baseline_params)
        baseline_model.fit(X_train, y_train)

        # Evaluate baseline
        baseline_train_acc = baseline_model.score(X_train, y_train)
        baseline_test_acc = baseline_model.score(X_test, y_test)
        baseline_f1 = f1_score(y_test, baseline_model.predict(X_test))

        # 5-fold CV on training set
        baseline_cv = cross_val_score(baseline_model, X_train, y_train, cv=5, scoring='f1').mean()

        mlflow.log_params(baseline_params)
        mlflow.log_metrics({
            "train_accuracy": baseline_train_acc,
            "test_accuracy": baseline_test_acc,
            "test_f1": baseline_f1,
            "cv_f1": baseline_cv
        })
        mlflow.set_tag("model_type", "baseline")

        results['baseline'] = {
            'train_acc': baseline_train_acc,
            'test_acc': baseline_test_acc,
            'test_f1': baseline_f1,
            'cv_f1': baseline_cv
        }

    # Train optimized model
    with mlflow.start_run(run_name=f"{classifier_name}_ga_optimized_comparison"):
        # Create optimized model (GA-tuned hyperparameters)
        optimized_model = create_model_from_params(classifier_name, optimized_params)
        optimized_model.fit(X_train, y_train)

        # Evaluate optimized
        optimized_train_acc = optimized_model.score(X_train, y_train)
        optimized_test_acc = optimized_model.score(X_test, y_test)
        optimized_f1 = f1_score(y_test, optimized_model.predict(X_test))

        # 5-fold CV on training set
        optimized_cv = cross_val_score(optimized_model, X_train, y_train, cv=5, scoring='f1').mean()

        mlflow.log_params(optimized_params)
        mlflow.log_metrics({
            "train_accuracy": optimized_train_acc,
            "test_accuracy": optimized_test_acc,
            "test_f1": optimized_f1,
            "cv_f1": optimized_cv
        })
        mlflow.set_tag("model_type", "ga_optimized")

        # Log improvement metrics
        improvements = {
            "accuracy_improvement": optimized_test_acc - baseline_test_acc,
            "f1_improvement": optimized_f1 - baseline_f1,
            "cv_f1_improvement": optimized_cv - baseline_cv
        }
        mlflow.log_metrics(improvements)

        results['optimized'] = {
            'train_acc': optimized_train_acc,
            'test_acc': optimized_test_acc,
            'test_f1': optimized_f1,
            'cv_f1': optimized_cv
        }
        results['improvement'] = improvements

    # Print comparison table
    print(f"\n{'='*80}")
    print(f"{classifier_name.upper()} - Baseline vs. GA-Optimized Comparison")
    print(f"{'='*80}")
    print(f"{'Metric':<25} {'Baseline':<15} {'Optimized':<15} {'Improvement':<15}")
    print(f"{'-'*80}")
    print(f"{'Test Accuracy':<25} {results['baseline']['test_acc']:<15.4f} "
          f"{results['optimized']['test_acc']:<15.4f} "
          f"{results['improvement']['accuracy_improvement']:<15.4f}")
    print(f"{'Test F1-Score':<25} {results['baseline']['test_f1']:<15.4f} "
          f"{results['optimized']['test_f1']:<15.4f} "
          f"{results['improvement']['f1_improvement']:<15.4f}")
    print(f"{'CV F1-Score':<25} {results['baseline']['cv_f1']:<15.4f} "
          f"{results['optimized']['cv_f1']:<15.4f} "
          f"{results['improvement']['cv_f1_improvement']:<15.4f}")
    print(f"{'='*80}\n")

    return results
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Grid search for hyperparameters | Genetic algorithms, Bayesian optimization | 2018-2020 | 10x faster for large search spaces, better exploration |
| Single optimization run | Multiple runs with different random seeds | 2020-2022 | Captures variance, identifies robust hyperparameters |
| Manual hyperparameter tuning | Automated optimization (GA, Optuna) | 2019-2021 | Democratizes ML—no manual expertise needed |
| CSV logging for experiments | MLflow, Weights & Biases | 2020-2023 | Reproducibility, model versioning, collaboration |
| Static hyperparameters | Meta-learning, transfer learning from past optimizations | 2023-2025 | Warm-start optimization, faster convergence |
| Accuracy-only fitness | Multi-objective optimization (accuracy + latency + fairness) | 2022-2024 | Production-ready models, not just accuracy |

**Deprecated/outdated:**
- **Grid search for >5 hyperparameters:** Exponential growth makes it infeasible (e.g., 10^6 combinations). Use GA or Bayesian optimization instead.
- **sklearn-deap library:** Unmaintained since 2018, doesn't support sklearn 1.x. Use sklearn-genetic-opt (active) or raw DEAP.
- **Training accuracy as fitness:** Leads to severe overfitting. Always use cross-validation or separate validation set.
- **Fixed 30 generations:** Modern practice uses early stopping when fitness plateaus for 5+ generations.

## Open Questions

### Question 1: Ensemble Weight Optimization Scope
**What we know:** Phase 3 uses soft voting (equal weights), hard voting, and stacking. GA-03 requires optimizing classifier weights in ensemble.

**What's unclear:** Should GA optimize individual classifier hyperparameters first (GA-01), THEN optimize ensemble weights as separate step? Or joint optimization where each individual represents both hyperparameters and weights?

**Recommendation:** Two-stage approach—(1) optimize individual classifiers, (2) optimize ensemble weights with fixed optimized classifiers. Joint optimization has 50+ dimensional search space (too large for GA with 30 generations). Two-stage is standard practice in literature.

### Question 2: Feature Selection Integration Timeline
**What we know:** GA-02 requires feature selection optimization. Current system uses all 30 features.

**What's unclear:** Should feature selection happen BEFORE hyperparameter tuning, AFTER, or SIMULTANEOUSLY? Feature selection changes data dimensionality, which affects optimal hyperparameters.

**Recommendation:** Feature selection as FIRST step, then hyperparameter tuning on selected features. Rationale: reduced feature space makes hyperparameter tuning faster, and optimal hyperparameters depend on feature set. Use `GAFeatureSelectionCV` pattern from sklearn-genetic-opt.

### Question 3: Computational Budget for 7 Classifiers
**What we know:** Optimizing 7 classifiers with 30 generations, population 50, 5-fold CV = 52,500 model evaluations total.

**What's unclear:** Is this computationally feasible within Phase 4 timeline? Each RF evaluation takes ~5 seconds (5-fold CV), so RF alone = 7,500 seconds = 2 hours. Across 7 classifiers = 14+ hours if serial.

**Recommendation:** Parallelize across classifiers (run 7 optimization jobs concurrently). On 8-core machine, each classifier gets 1 core, completes in 2-3 hours. Total wallclock time: 3 hours. Log to separate MLflow runs per classifier. Consider reducing generations to 20 if >3 hours is prohibitive.

### Question 4: Test Set Usage for Final Evaluation
**What we know:** Current system uses train/val/test splits from Phase 1. GA fitness uses 5-fold CV on training set.

**What's unclear:** Should test set be used during GA optimization for early stopping? Or held out completely until final evaluation?

**Recommendation:** Hold out test set completely—use ONLY for final comparison in EVAL-04. Early stopping based on CV score plateau (if avg fitness doesn't improve >0.01 for 5 generations). Prevents any information leakage from test set into optimization process.

## Sources

### Primary (HIGH confidence)
- DEAP 1.4.3 official documentation: https://deap.readthedocs.io/en/master/
- DEAP PyPI: https://pypi.org/project/deap/ (version 1.4.3, released 2025-05-04)
- DEAP Genetic Algorithm Tutorial: https://deap.readthedocs.io/en/master/examples/ga_onemax.html
- DEAP API Reference (Tools): https://deap.readthedocs.io/en/master/api/tools.html
- MLflow Model Registry: https://mlflow.org/docs/latest/ml/model-registry/
- MLflow Tracking: https://mlflow.org/docs/latest/ml/tracking/
- sklearn-genetic-opt documentation: https://sklearn-genetic-opt.readthedocs.io/
- sklearn cross-validation: https://scikit-learn.org/stable/modules/cross_validation.html

### Secondary (MEDIUM confidence)
- Hyperparameter Optimization with GA and XGBoost (2024 study): https://pmc.ncbi.nlm.nih.gov/articles/PMC10892895/
- sklearn-genetic-opt GitHub: https://github.com/rodrigo-arenas/Sklearn-genetic-opt
- DEAP GitHub: https://github.com/DEAP/deap
- Feature Selection with GA article: https://towardsdatascience.com/feature-selection-with-genetic-algorithms-7dd7e02dd237/
- Tune sklearn Model Using Evolutionary Algorithms: https://towardsdatascience.com/tune-your-scikit-learn-model-using-evolutionary-algorithms-30538248ac16/
- DEAP GA Feature Selection Tutorial: https://viktorsapozhok.github.io/deap-genetic-algorithm/

### Tertiary (LOW confidence - community patterns, needs validation)
- Premature convergence discussions: Wikipedia, ResearchGate threads
- Ensemble weight optimization papers (IEEE, Springer) - paywalled, abstracts only
- GA hyperparameter tuning blog posts - various authors, not peer-reviewed

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - DEAP and MLflow are industry standards with extensive documentation
- Architecture: HIGH - Patterns verified from official DEAP examples and sklearn-genetic-opt source code
- Search spaces: MEDIUM - Based on research papers but not validated on this specific dataset
- Pitfalls: HIGH - Common issues documented in DEAP FAQ and sklearn-genetic-opt issues tracker
- Code examples: HIGH - Synthesized from official documentation, tested patterns

**Research date:** 2026-02-11
**Valid until:** 2026-04-11 (60 days - DEAP and MLflow are mature, stable libraries with infrequent breaking changes)

**Key dependencies verified:**
- DEAP 1.4.3 compatible with Python 3.9-3.13 (project uses >=3.9)
- MLflow >=2.20.0 compatible with scikit-learn >=1.4.0 (already in requirements)
- No conflicts with existing dependencies (pandas, numpy, joblib)
