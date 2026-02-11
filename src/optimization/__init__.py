"""Genetic algorithm optimization module for hyperparameter tuning.

This module provides infrastructure for optimizing hyperparameters of all
7 classifiers using DEAP (Distributed Evolutionary Algorithms in Python)
with MLflow experiment tracking.

Key components:
- search_spaces: Defines bounded hyperparameter ranges for each classifier
- fitness: Evaluates individuals using 5-fold CV F1-score
- ga_optimizer: DEAP toolbox setup and evolution loop

Usage:
    >>> from src.optimization import SEARCH_SPACES, setup_toolbox, run_ga_optimization
    >>> toolbox = setup_toolbox('rf', X_train, y_train)
    >>> best, logbook, hof = run_ga_optimization(toolbox, population_size=50, n_generations=30)
"""

from .fitness import (
    create_fitness_function,
    create_model_from_params,
    evaluate_individual,
)
from .ga_optimizer import run_ga_optimization, setup_toolbox
from .search_spaces import (
    SEARCH_SPACES,
    decode_individual,
    get_search_space_size,
)

__all__ = [
    # Search spaces
    'SEARCH_SPACES',
    'decode_individual',
    'get_search_space_size',
    # Fitness evaluation
    'evaluate_individual',
    'create_fitness_function',
    'create_model_from_params',
    # GA optimizer
    'setup_toolbox',
    'run_ga_optimization',
]
