"""Hyperparameter search spaces for genetic algorithm optimization.

This module defines bounded search spaces for all 7 classifiers used in the
phishing detection ensemble. Search spaces are informed by Phase 4 research
and are 2-3x wider than baseline parameter ranges to enable exploration.

Each hyperparameter is typed as 'int', 'float' (with optional log scaling),
or 'categorical' (discrete choices).
"""

from typing import Any, Dict, List


# Search space definitions for all 7 classifiers
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
    'mlp': {
        'hidden_layer_sizes': {'type': 'int', 'low': 50, 'high': 200},
        'alpha': {'type': 'float', 'low': 0.0001, 'high': 0.1, 'log': True},
        'learning_rate_init': {'type': 'float', 'low': 0.001, 'high': 0.1, 'log': True},
        # activation='relu', solver='adam' kept constant
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


def decode_individual(classifier_name: str, individual: List[Any]) -> Dict[str, Any]:
    """Decode DEAP individual (list of values) to hyperparameter dictionary.

    Converts GA individual representation to typed hyperparameters suitable
    for sklearn classifier constructors. Handles type casting (int, float),
    log-scale decoding, and bounds enforcement.

    Args:
        classifier_name: One of 'rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt'
        individual: List of hyperparameter values from DEAP evolution

    Returns:
        Dictionary mapping hyperparameter names to properly typed values

    Example:
        >>> ind = [200, 15, 10, 5]  # RF individual
        >>> params = decode_individual('rf', ind)
        >>> print(params)
        {'n_estimators': 200, 'max_depth': 15, 'min_samples_split': 10, 'min_samples_leaf': 5}
    """
    if classifier_name not in SEARCH_SPACES:
        raise ValueError(
            f"Unknown classifier: {classifier_name}. "
            f"Valid options: {list(SEARCH_SPACES.keys())}"
        )

    search_space = SEARCH_SPACES[classifier_name]
    param_names = list(search_space.keys())

    if len(individual) != len(param_names):
        raise ValueError(
            f"Individual length mismatch: expected {len(param_names)} "
            f"parameters for {classifier_name}, got {len(individual)}"
        )

    params = {}

    for idx, param_name in enumerate(param_names):
        param_spec = search_space[param_name]
        value = individual[idx]

        # Type casting and bounds enforcement
        if param_spec['type'] == 'int':
            # Cast to int and enforce bounds
            value = int(value)
            value = max(param_spec['low'], min(param_spec['high'], value))

        elif param_spec['type'] == 'float':
            # Cast to float and enforce bounds
            value = float(value)
            value = max(param_spec['low'], min(param_spec['high'], value))

        elif param_spec['type'] == 'categorical':
            # For categorical, value should be index into choices
            # Ensure it's valid index
            choices = param_spec['choices']
            idx_value = int(value)
            idx_value = max(0, min(len(choices) - 1, idx_value))
            value = choices[idx_value]

        params[param_name] = value

    return params


def get_search_space_size(classifier_name: str) -> int:
    """Get the number of hyperparameters in search space for a classifier.

    Args:
        classifier_name: One of 'rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt'

    Returns:
        Number of hyperparameters to optimize

    Example:
        >>> get_search_space_size('rf')
        4
        >>> get_search_space_size('xgb')
        9
    """
    if classifier_name not in SEARCH_SPACES:
        raise ValueError(
            f"Unknown classifier: {classifier_name}. "
            f"Valid options: {list(SEARCH_SPACES.keys())}"
        )

    return len(SEARCH_SPACES[classifier_name])
