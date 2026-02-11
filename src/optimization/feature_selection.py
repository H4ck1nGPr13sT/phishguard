"""Feature selection using genetic algorithms.

This module implements GA-based feature selection for optimizing which URL features
contribute most to classification accuracy. Feature selection is implemented with:

- Binary representation (1 = feature selected, 0 = feature excluded)
- RF-based fitness evaluation for speed (selected features used by all classifiers)
- Minimum feature constraint to prevent degenerate solutions
- 5-fold CV F1-score as fitness metric to prevent overfitting

GA configuration:
- Population size: 30 (binary space simpler than hyperparameter search)
- Generations: 20 (binary representation converges faster)
- Crossover: Two-point (works well for binary)
- Mutation: Bit flip with indpb=1/n_features
- Selection: Tournament (tournsize=3)
"""

import logging
import random
from typing import Any, Dict, List, Tuple

import numpy as np
from deap import algorithms, base, creator, tools
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, make_scorer
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


def evaluate_feature_subset(
    individual: List[int],
    X_train: np.ndarray,
    y_train: np.ndarray,
    min_features: int = 5,
    classifier: str = 'rf'
) -> Tuple[float]:
    """Evaluate fitness of a feature subset using cross-validation.

    This function evaluates a binary individual (feature subset) by training
    a classifier on only the selected features and measuring F1-score with
    5-fold stratified cross-validation.

    Args:
        individual: Binary list where 1 = feature selected, 0 = feature excluded
        X_train: Training features (all features)
        y_train: Training labels
        min_features: Minimum number of features required (default: 5)
        classifier: Classifier to use for evaluation (default: 'rf')

    Returns:
        Tuple with single fitness value (mean F1-score from CV)
        Returns (0.0,) if fewer than min_features selected

    Example:
        >>> individual = [1, 0, 1, 1, 0, ...]  # Select features 0, 2, 3, ...
        >>> fitness = evaluate_feature_subset(individual, X_train, y_train)
        >>> print(f"F1-score: {fitness[0]:.4f}")
        F1-score: 0.9247
    """
    try:
        # Extract selected feature indices
        selected_indices = [i for i, selected in enumerate(individual) if selected == 1]

        # Enforce minimum features constraint
        if len(selected_indices) < min_features:
            logger.debug(
                f"Feature subset has only {len(selected_indices)} features "
                f"(minimum: {min_features}). Returning zero fitness."
            )
            return (0.0,)

        # Select features
        X_selected = X_train[:, selected_indices]

        # Create model (RF as proxy classifier - fast and robust)
        model = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', RandomForestClassifier(
                n_estimators=100,  # Fixed for speed
                class_weight='balanced',
                random_state=42,
                n_jobs=-1
            ))
        ])

        # Evaluate with 5-fold stratified CV using F1-score
        f1_scorer = make_scorer(f1_score, average='binary')
        cv_scores = cross_val_score(
            model, X_selected, y_train,
            cv=5,  # 5-fold stratified CV
            scoring=f1_scorer,
            n_jobs=1  # Avoid nested parallelism (RF uses n_jobs=-1)
        )

        # Return mean F1 as fitness (DEAP requires tuple)
        fitness_value = cv_scores.mean()
        logger.debug(
            f"Feature subset (n={len(selected_indices)}): "
            f"F1={fitness_value:.4f} (std={cv_scores.std():.4f})"
        )

        return (fitness_value,)

    except Exception as e:
        # Invalid configuration - return zero fitness
        logger.warning(
            f"Failed to evaluate feature subset: {e}. "
            "Returning zero fitness."
        )
        return (0.0,)


def setup_feature_selection_toolbox(
    X_train: np.ndarray,
    y_train: np.ndarray,
    min_features: int = 5
) -> base.Toolbox:
    """Setup DEAP toolbox for GA-based feature selection.

    Creates DEAP fitness type, individual type, and registers genetic operators
    for binary feature selection:
    - Binary individual (length = n_features)
    - Two-point crossover (works well for binary)
    - Bit-flip mutation (indpb=1/n_features)
    - Tournament selection (tournsize=3)

    Args:
        X_train: Training features
        y_train: Training labels
        min_features: Minimum number of features required (default: 5)

    Returns:
        Configured DEAP toolbox ready for evolution

    Example:
        >>> toolbox = setup_feature_selection_toolbox(X_train, y_train)
        >>> population = toolbox.population(n=30)
        >>> # Run evolution...
    """
    n_features = X_train.shape[1]

    # Define fitness (maximize F1-score)
    # Check if already created (DEAP creator is global)
    if not hasattr(creator, "FitnessMax"):
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    if not hasattr(creator, "Individual"):
        creator.create("Individual", list, fitness=creator.FitnessMax)

    # Setup toolbox
    toolbox = base.Toolbox()

    # Register binary attribute generator (0 or 1)
    toolbox.register("attr_bool", random.randint, 0, 1)

    # Create individual as list of n_features binary values
    toolbox.register(
        "individual",
        tools.initRepeat,
        creator.Individual,
        toolbox.attr_bool,
        n=n_features
    )

    # Create population
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    # Register fitness evaluation function with closure over data
    def fitness_wrapper(individual: List[int]) -> Tuple[float]:
        return evaluate_feature_subset(
            individual, X_train, y_train, min_features
        )

    toolbox.register("evaluate", fitness_wrapper)

    # Register genetic operators
    toolbox.register("mate", tools.cxTwoPoint)  # Two-point crossover for binary

    # Bit flip mutation with indpb=1/n_features
    # (On average, flip 1 bit per individual)
    toolbox.register(
        "mutate",
        tools.mutFlipBit,
        indpb=1.0 / n_features
    )

    # Tournament selection
    toolbox.register("select", tools.selTournament, tournsize=3)

    logger.info(
        f"Setup feature selection toolbox: {n_features} features, "
        f"min_features={min_features}"
    )

    return toolbox


def run_feature_selection(
    toolbox: base.Toolbox,
    population_size: int = 30,
    n_generations: int = 20,
    cxpb: float = 0.5,
    mutpb: float = 0.2
) -> Tuple[Any, List[int], tools.Logbook]:
    """Run genetic algorithm feature selection.

    Executes DEAP evolutionary loop with:
    - Initial random population
    - HallOfFame to preserve elite individuals
    - Statistics tracking (avg, std, min, max fitness)
    - Tournament selection, two-point crossover, bit-flip mutation

    Args:
        toolbox: Configured DEAP toolbox from setup_feature_selection_toolbox()
        population_size: Number of individuals per generation (default: 30)
        n_generations: Number of generations to evolve (default: 20)
        cxpb: Crossover probability (default: 0.5)
        mutpb: Mutation probability (default: 0.2)

    Returns:
        Tuple of:
        - best_individual: Best feature subset found (binary list)
        - selected_indices: List of selected feature indices
        - logbook: Fitness statistics per generation

    Example:
        >>> toolbox = setup_feature_selection_toolbox(X_train, y_train)
        >>> best, selected_idx, logbook = run_feature_selection(
        ...     toolbox, population_size=30, n_generations=20
        ... )
        >>> print(f"Best F1-score: {best.fitness.values[0]:.4f}")
        >>> print(f"Selected {len(selected_idx)} features: {selected_idx}")
    """
    logger.info(
        f"Starting feature selection: population={population_size}, "
        f"generations={n_generations}, cxpb={cxpb}, mutpb={mutpb}"
    )

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
    logger.info("Beginning evolution...")
    population, logbook = algorithms.eaSimple(
        population, toolbox,
        cxpb=cxpb,           # Crossover probability
        mutpb=mutpb,         # Mutation probability
        ngen=n_generations,  # Number of generations
        stats=stats,
        halloffame=hof,
        verbose=True         # Print generation statistics
    )

    # Extract best individual
    best_individual = hof[0]
    best_fitness = best_individual.fitness.values[0]
    selected_indices = [i for i, selected in enumerate(best_individual) if selected == 1]

    logger.info(f"Evolution complete. Best fitness: {best_fitness:.4f}")
    logger.info(f"Selected {len(selected_indices)} features: {selected_indices}")

    # Log Hall of Fame summary
    logger.info(f"Hall of Fame (top {len(hof)} individuals):")
    for i, ind in enumerate(hof):
        n_selected = sum(ind)
        logger.info(
            f"  {i+1}. Fitness: {ind.fitness.values[0]:.4f}, "
            f"Features: {n_selected}"
        )

    return best_individual, selected_indices, logbook


def get_selected_features(
    individual: List[int],
    feature_names: List[str]
) -> Dict[str, Any]:
    """Convert binary individual to selected feature information.

    Args:
        individual: Binary list where 1 = feature selected, 0 = feature excluded
        feature_names: List of all feature names

    Returns:
        Dictionary with:
        - indices: List of selected feature indices
        - names: List of selected feature names
        - n_selected: Number of selected features

    Example:
        >>> individual = [1, 0, 1, 1, 0]
        >>> feature_names = ['f1', 'f2', 'f3', 'f4', 'f5']
        >>> result = get_selected_features(individual, feature_names)
        >>> print(result)
        {'indices': [0, 2, 3], 'names': ['f1', 'f3', 'f4'], 'n_selected': 3}
    """
    selected_indices = [i for i, selected in enumerate(individual) if selected == 1]
    selected_names = [feature_names[i] for i in selected_indices]

    return {
        'indices': selected_indices,
        'names': selected_names,
        'n_selected': len(selected_indices)
    }
