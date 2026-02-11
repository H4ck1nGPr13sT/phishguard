"""Genetic algorithm optimizer using DEAP framework.

This module implements GA-based hyperparameter optimization using DEAP
(Distributed Evolutionary Algorithms in Python). It provides:

- Toolbox setup with appropriate genetic operators for each parameter type
- Evolution loop with HallOfFame for elite preservation
- Statistics tracking for convergence monitoring

GA configuration based on Phase 4 research:
- Tournament selection (tournsize=3) balances exploration/exploitation
- Single-point crossover for hyperparameter recombination
- Mutation with 20% per-gene probability to maintain diversity
- HallOfFame preserves top 10 individuals across generations
"""

import logging
import random
from typing import Any, List, Tuple

import numpy as np
from deap import algorithms, base, creator, tools

from .fitness import create_fitness_function
from .search_spaces import SEARCH_SPACES

logger = logging.getLogger(__name__)


def setup_toolbox(
    classifier_name: str,
    X_train: np.ndarray,
    y_train: np.ndarray
) -> base.Toolbox:
    """Setup DEAP toolbox for GA optimization of classifier hyperparameters.

    Creates DEAP fitness type, individual type, and registers genetic operators:
    - Attribute generators for each hyperparameter (int, float, categorical)
    - Individual and population initialization
    - Fitness evaluation function with closure over training data
    - Genetic operators: mate (crossover), mutate, select

    Args:
        classifier_name: One of 'rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt'
        X_train: Training features
        y_train: Training labels

    Returns:
        Configured DEAP toolbox ready for evolution

    Example:
        >>> toolbox = setup_toolbox('rf', X_train, y_train)
        >>> population = toolbox.population(n=50)
        >>> # Run evolution...
    """
    if classifier_name not in SEARCH_SPACES:
        raise ValueError(
            f"Unknown classifier: {classifier_name}. "
            f"Valid options: {list(SEARCH_SPACES.keys())}"
        )

    search_space = SEARCH_SPACES[classifier_name]

    # Define fitness (maximize F1-score)
    # Check if already created (DEAP creator is global)
    if not hasattr(creator, "FitnessMax"):
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    if not hasattr(creator, "Individual"):
        creator.create("Individual", list, fitness=creator.FitnessMax)

    # Setup toolbox
    toolbox = base.Toolbox()

    # Register attribute generators for each hyperparameter
    attr_generators = []

    for param_name, param_spec in search_space.items():
        attr_name = f"attr_{param_name}"

        if param_spec['type'] == 'int':
            # Integer parameter
            toolbox.register(
                attr_name,
                random.randint,
                param_spec['low'],
                param_spec['high']
            )
        elif param_spec['type'] == 'float':
            # Float parameter (log scale handled in decode)
            if param_spec.get('log', False):
                # For log-scale params, sample in log space then exponentiate
                log_low = np.log10(param_spec['low'])
                log_high = np.log10(param_spec['high'])
                toolbox.register(
                    attr_name,
                    lambda: 10 ** random.uniform(log_low, log_high)
                )
            else:
                # Linear scale
                toolbox.register(
                    attr_name,
                    random.uniform,
                    param_spec['low'],
                    param_spec['high']
                )
        elif param_spec['type'] == 'categorical':
            # Categorical parameter - store as index into choices
            toolbox.register(
                attr_name,
                random.randint,
                0,
                len(param_spec['choices']) - 1
            )

        attr_generators.append(getattr(toolbox, attr_name))

    # Create individual as list of hyperparameters
    toolbox.register(
        "individual",
        tools.initCycle,
        creator.Individual,
        tuple(attr_generators),
        n=1
    )

    # Create population
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    # Register fitness evaluation function
    fitness_func = create_fitness_function(classifier_name, X_train, y_train)
    toolbox.register("evaluate", fitness_func)

    # Register genetic operators
    # Use cxBlend for float/continuous parameters (works with any number of genes, including 1)
    # alpha=0.5 allows offspring to be slightly outside parent range for exploration
    toolbox.register("mate", tools.cxBlend, alpha=0.5)

    # Register mutation operator
    # Use mutPolynomialBounded for mixed int/float parameters
    # eta=20.0 controls mutation spread (higher = more concentrated near original)
    # Build mutation bounds lists
    low_bounds = []
    up_bounds = []

    for param_name, param_spec in search_space.items():
        if param_spec['type'] == 'int':
            low_bounds.append(float(param_spec['low']))
            up_bounds.append(float(param_spec['high']))
        elif param_spec['type'] == 'float':
            low_bounds.append(param_spec['low'])
            up_bounds.append(param_spec['high'])
        elif param_spec['type'] == 'categorical':
            low_bounds.append(0.0)
            up_bounds.append(float(len(param_spec['choices']) - 1))

    toolbox.register(
        "mutate",
        tools.mutPolynomialBounded,
        low=low_bounds,
        up=up_bounds,
        eta=20.0,     # Mutation spread parameter
        indpb=0.2     # 20% chance to mutate each gene
    )

    # Register selection operator
    toolbox.register("select", tools.selTournament, tournsize=3)

    logger.info(
        f"Setup toolbox for {classifier_name} with "
        f"{len(search_space)} hyperparameters"
    )

    return toolbox


def run_ga_optimization(
    toolbox: base.Toolbox,
    population_size: int = 50,
    n_generations: int = 30,
    cxpb: float = 0.7,
    mutpb: float = 0.2
) -> Tuple[Any, tools.Logbook, tools.HallOfFame]:
    """Run genetic algorithm optimization.

    Executes DEAP evolutionary loop with:
    - Initial random population
    - HallOfFame to preserve elite individuals
    - Statistics tracking (avg, std, min, max fitness)
    - Tournament selection, crossover, mutation

    Args:
        toolbox: Configured DEAP toolbox from setup_toolbox()
        population_size: Number of individuals per generation (default: 50)
        n_generations: Number of generations to evolve (default: 30)
        cxpb: Crossover probability (default: 0.7)
        mutpb: Mutation probability (default: 0.2)

    Returns:
        Tuple of:
        - best_individual: Best hyperparameter set found
        - logbook: Fitness statistics per generation
        - hall_of_fame: Top 10 individuals across all generations

    Example:
        >>> toolbox = setup_toolbox('rf', X_train, y_train)
        >>> best, logbook, hof = run_ga_optimization(toolbox, population_size=50, n_generations=30)
        >>> print(f"Best F1-score: {best.fitness.values[0]:.4f}")
        >>> print(f"Best hyperparameters: {decode_individual('rf', best)}")
    """
    logger.info(
        f"Starting GA optimization: population={population_size}, "
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

    # Log final results
    best_individual = hof[0]
    best_fitness = best_individual.fitness.values[0]

    logger.info(f"Evolution complete. Best fitness: {best_fitness:.4f}")
    logger.info(f"Best individual: {best_individual}")

    # Log Hall of Fame summary
    logger.info(f"Hall of Fame (top {len(hof)} individuals):")
    for i, ind in enumerate(hof):
        logger.info(f"  {i+1}. Fitness: {ind.fitness.values[0]:.4f}, Params: {ind}")

    return best_individual, logbook, hof
