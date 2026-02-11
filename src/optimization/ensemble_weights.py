"""GA-based ensemble weight optimization.

This module implements genetic algorithm optimization for ensemble classifier weights.
Instead of equal-weight soft voting (1/7 for each classifier), GA finds optimal weights
that reflect classifier reliability and improve overall ensemble accuracy.

Weight representation:
- Individual = array of 7 floats (one per classifier)
- Normalized to sum to 1.0
- Minimum weight 0.01 to preserve diversity

GA configuration:
- Population: 30 (smaller than hyperparameter optimization)
- Generations: 20 (quick convergence expected)
- Crossover: cxBlend (alpha=0.5) for continuous weight space
- Mutation: mutGaussian (sigma=0.1, indpb=0.3)
- Selection: Tournament (tournsize=3)
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
from deap import base, creator, tools
from sklearn.ensemble import VotingClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)


def normalize_weights(individual: List[float]) -> List[float]:
    """Normalize weights to sum to 1.0 with minimum 0.01 per classifier.

    Ensures:
    - All weights >= 0.01 (minimum contribution for diversity)
    - Sum equals 1.0 (valid probability distribution)

    Args:
        individual: List of 7 float values (can be any positive values)

    Returns:
        Normalized weights summing to 1.0

    Example:
        >>> weights = [0.5, 0.3, 0.1, 0.05, 0.02, 0.02, 0.01]
        >>> normalized = normalize_weights(weights)
        >>> assert abs(sum(normalized) - 1.0) < 0.001
        >>> assert all(w >= 0.01 for w in normalized)
    """
    # Apply minimum weight
    weights = [max(0.01, w) for w in individual]

    # Normalize to sum to 1.0
    total = sum(weights)
    normalized = [w / total for w in weights]

    return normalized


def setup_weight_optimization_toolbox(
    classifiers: Dict[str, Pipeline],
    X_train: np.ndarray,
    y_train: np.ndarray
) -> base.Toolbox:
    """Setup DEAP toolbox for GA-based ensemble weight optimization.

    Creates fitness type, individual type, and genetic operators for
    optimizing 7 classifier weights (continuous values 0.0-1.0).

    Args:
        classifiers: Dict mapping classifier names to fitted pipelines
        X_train: Training features
        y_train: Training labels

    Returns:
        Configured DEAP toolbox ready for evolution

    Example:
        >>> classifiers = {'rf': rf_pipeline, 'svm': svm_pipeline, ...}
        >>> toolbox = setup_weight_optimization_toolbox(classifiers, X_train, y_train)
        >>> population = toolbox.population(n=30)
    """
    # Create fitness type (maximize F1-score)
    if not hasattr(creator, "FitnessMax"):
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    if not hasattr(creator, "Individual"):
        creator.create("Individual", list, fitness=creator.FitnessMax)

    toolbox = base.Toolbox()

    # Register attribute generator: random float in [0.0, 1.0]
    # Will be normalized in fitness function
    toolbox.register("attr_weight", np.random.uniform, 0.0, 1.0)

    # Individual = 7 weights (one per classifier)
    toolbox.register(
        "individual",
        tools.initRepeat,
        creator.Individual,
        toolbox.attr_weight,
        n=7
    )

    # Population
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    # Register fitness evaluation
    def evaluate_weighted_ensemble(individual):
        """Evaluate weighted voting ensemble with given weights.

        Args:
            individual: List of 7 weights

        Returns:
            Tuple of (f1_score,) for DEAP
        """
        # Normalize weights
        weights_normalized = normalize_weights(individual)

        # Create weighted voting ensemble
        estimators = [(name, clf) for name, clf in classifiers.items()]

        # VotingClassifier expects weights in same order as estimators
        ensemble = VotingClassifier(
            estimators=estimators,
            voting='soft',
            weights=weights_normalized,
            n_jobs=1  # Prevent nested parallelism
        )

        # Evaluate with 5-fold CV
        try:
            cv_scores = cross_val_score(
                ensemble, X_train, y_train,
                cv=5,
                scoring='f1',
                n_jobs=1  # Cross-validation in single thread
            )
            f1_mean = cv_scores.mean()

            logger.debug(f"Weights: {[f'{w:.3f}' for w in weights_normalized]}, F1: {f1_mean:.4f}")

            return (f1_mean,)
        except Exception as e:
            logger.error(f"Error evaluating ensemble: {e}")
            return (0.0,)  # Failed evaluation

    toolbox.register("evaluate", evaluate_weighted_ensemble)

    # Register genetic operators
    # Blend crossover: offspring can be outside parent range (alpha=0.5)
    toolbox.register("mate", tools.cxBlend, alpha=0.5)

    # Gaussian mutation: sigma=0.1 (10% change), indpb=0.3 (30% genes mutated)
    toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=0.1, indpb=0.3)

    # Bounds checking: ensure weights stay in [0.0, 1.0]
    def checkBounds(min_val, max_val):
        def decorator(func):
            def wrapper(*args, **kargs):
                offspring = func(*args, **kargs)
                for child in offspring:
                    for i in range(len(child)):
                        child[i] = max(min_val, min(max_val, child[i]))
                return offspring
            return wrapper
        return decorator

    toolbox.decorate("mate", checkBounds(0.0, 1.0))
    toolbox.decorate("mutate", checkBounds(0.0, 1.0))

    # Tournament selection
    toolbox.register("select", tools.selTournament, tournsize=3)

    logger.info("Setup weight optimization toolbox for 7 classifiers")

    return toolbox


def run_weight_optimization(
    toolbox: base.Toolbox,
    population_size: int = 30,
    n_generations: int = 20
) -> Tuple[List[float], tools.Logbook]:
    """Run genetic algorithm weight optimization.

    Args:
        toolbox: Configured DEAP toolbox
        population_size: Number of individuals per generation
        n_generations: Number of generations to evolve

    Returns:
        Tuple of:
        - best_weights: Optimal normalized weights (sum to 1.0)
        - logbook: Fitness statistics per generation

    Example:
        >>> toolbox = setup_weight_optimization_toolbox(classifiers, X_train, y_train)
        >>> best_weights, logbook = run_weight_optimization(toolbox)
        >>> print(f"Best weights: {best_weights}")
    """
    logger.info(f"Starting weight optimization: pop={population_size}, gen={n_generations}")

    # Create initial population
    population = toolbox.population(n=population_size)

    # Hall of Fame
    hof = tools.HallOfFame(maxsize=10)

    # Statistics
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", np.mean)
    stats.register("std", np.std)
    stats.register("min", np.min)
    stats.register("max", np.max)

    # Run evolution
    from deap import algorithms

    population, logbook = algorithms.eaSimple(
        population, toolbox,
        cxpb=0.6,  # Crossover probability
        mutpb=0.3,  # Mutation probability (higher for continuous space)
        ngen=n_generations,
        stats=stats,
        halloffame=hof,
        verbose=True
    )

    # Get best weights
    best_individual = hof[0]
    best_weights = normalize_weights(best_individual)
    best_fitness = best_individual.fitness.values[0]

    logger.info(f"Optimization complete. Best F1: {best_fitness:.4f}")
    logger.info(f"Best weights: {[f'{w:.3f}' for w in best_weights]}")

    return best_weights, logbook


def create_weighted_ensemble(
    weights: Dict[str, float],
    classifier_paths: Dict[str, Path]
) -> VotingClassifier:
    """Create weighted voting ensemble with optimized weights.

    Args:
        weights: Dict mapping classifier name to weight
        classifier_paths: Dict mapping classifier name to model path

    Returns:
        VotingClassifier configured with optimized weights

    Example:
        >>> weights = {'rf': 0.20, 'svm': 0.18, ...}
        >>> paths = {'rf': Path('models/optimized/rf_optimized.joblib'), ...}
        >>> ensemble = create_weighted_ensemble(weights, paths)
        >>> ensemble.fit(X_train, y_train)
    """
    # Load classifiers
    estimators = []
    weight_list = []

    for name in ['rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt']:
        if name not in classifier_paths:
            raise ValueError(f"Missing classifier path for: {name}")

        # Load classifier
        clf_data = joblib.load(classifier_paths[name])

        # Handle both dict format and direct Pipeline format
        if isinstance(clf_data, dict) and 'model' in clf_data:
            clf = clf_data['model']
        else:
            clf = clf_data

        estimators.append((name, clf))
        weight_list.append(weights[name])

        logger.info(f"Loaded {name}: weight={weights[name]:.3f}")

    # Create weighted voting ensemble
    ensemble = VotingClassifier(
        estimators=estimators,
        voting='soft',
        weights=weight_list,
        n_jobs=-1
    )

    logger.info(f"Created weighted ensemble with {len(estimators)} classifiers")

    return ensemble
