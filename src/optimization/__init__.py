"""Genetic Algorithm Optimization Module.

Provides GA-based optimization for:
- Hyperparameter tuning (GA-01)
- Feature selection (GA-02)
- Ensemble weight optimization (GA-03)

Uses DEAP framework with tournament selection, single-point crossover,
and mutation operators (GA-04). Maximizes F1-score with 5-fold CV (GA-05).
Tracks fitness history across generations (GA-06).
"""

from src.optimization.search_spaces import (
    SEARCH_SPACES,
    decode_individual,
    get_search_space_size,
)
from src.optimization.fitness import (
    create_fitness_function,
    evaluate_individual,
    create_model_from_params,
)
from src.optimization.ga_optimizer import (
    setup_toolbox,
    run_ga_optimization,
)
from src.optimization.feature_selection import (
    setup_feature_selection_toolbox,
    run_feature_selection,
    get_selected_features,
)
from src.optimization.ensemble_weights import (
    setup_weight_optimization_toolbox,
    run_weight_optimization,
    normalize_weights,
    create_weighted_ensemble,
)
from src.optimization.model_registry import (
    register_model,
    compare_versions,
    set_active_version,
    get_active_model,
    generate_comparison_report,
)
from src.optimization.mlflow_tracker import (
    setup_experiment,
    log_generation,
    log_best_individual,
)

__all__ = [
    # Search spaces
    'SEARCH_SPACES', 'decode_individual', 'get_search_space_size',
    # Fitness
    'create_fitness_function', 'evaluate_individual', 'create_model_from_params',
    # GA optimizer
    'setup_toolbox', 'run_ga_optimization',
    # Feature selection
    'setup_feature_selection_toolbox', 'run_feature_selection', 'get_selected_features',
    # Ensemble weights
    'setup_weight_optimization_toolbox', 'run_weight_optimization',
    'normalize_weights', 'create_weighted_ensemble',
    # Model registry
    'register_model', 'compare_versions', 'set_active_version',
    'get_active_model', 'generate_comparison_report',
    # MLflow tracking
    'setup_experiment', 'log_generation', 'log_best_individual',
]
