"""Fitness evaluation for genetic algorithm optimization.

This module provides fitness functions for evaluating GA individuals
(hyperparameter sets) using cross-validation. Fitness is measured as
F1-score averaged over 5-fold stratified cross-validation to prevent
overfitting and handle class imbalance.
"""

import logging
from typing import Any, Callable, Dict, List, Tuple

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, make_scorer
from sklearn.model_selection import cross_val_score
from sklearn.naive_bayes import GaussianNB
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

from .search_spaces import decode_individual

logger = logging.getLogger(__name__)


def create_model_from_params(classifier_name: str, params: Dict[str, Any]) -> Pipeline:
    """Create sklearn Pipeline with scaler and classifier from hyperparameters.

    Args:
        classifier_name: One of 'rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt'
        params: Hyperparameter dictionary (decoded from individual)

    Returns:
        sklearn Pipeline with StandardScaler + classifier

    Raises:
        ValueError: If classifier name not recognized
    """
    # Map classifier names to classes
    classifier_map = {
        'rf': RandomForestClassifier,
        'svm': SVC,
        'mlp': MLPClassifier,
        'xgb': XGBClassifier,
        'lr': LogisticRegression,
        'nb': GaussianNB,
        'dt': DecisionTreeClassifier
    }

    if classifier_name not in classifier_map:
        raise ValueError(
            f"Unknown classifier: {classifier_name}. "
            f"Valid options: {list(classifier_map.keys())}"
        )

    # Merge with constant parameters per classifier
    full_params = params.copy()

    if classifier_name == 'rf':
        full_params.update({
            'class_weight': 'balanced',
            'oob_score': True,
            'n_jobs': -1,
            'random_state': 42
        })
    elif classifier_name == 'svm':
        full_params.update({
            'probability': True,  # Required for soft voting
            'class_weight': 'balanced',
            'random_state': 42
        })
    elif classifier_name == 'mlp':
        full_params.update({
            'activation': 'relu',
            'solver': 'adam',
            'max_iter': 500,
            'random_state': 42
        })
        # MLP expects tuple for hidden_layer_sizes
        if 'hidden_layer_sizes' in full_params:
            full_params['hidden_layer_sizes'] = (full_params['hidden_layer_sizes'],)
    elif classifier_name == 'xgb':
        full_params.update({
            'n_jobs': 1,  # Prevent thread thrashing with sklearn
            'random_state': 42
        })
    elif classifier_name == 'lr':
        # Handle solver based on penalty
        if params.get('penalty') == 'none':
            solver = 'saga'  # saga supports penalty='none'
        else:
            solver = 'lbfgs'  # lbfgs is default, faster for l2

        full_params.update({
            'solver': solver,
            'class_weight': 'balanced',
            'max_iter': 1000,
            'random_state': 42,
            'n_jobs': -1
        })
    elif classifier_name == 'dt':
        full_params.update({
            'class_weight': 'balanced',
            'random_state': 42
        })
    # nb has no additional constant params

    classifier_class = classifier_map[classifier_name]
    classifier = classifier_class(**full_params)

    # Wrap in pipeline with scaler
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', classifier)
    ])

    return pipeline


def evaluate_individual(
    individual: List[Any],
    classifier_name: str,
    X_train: np.ndarray,
    y_train: np.ndarray
) -> Tuple[float]:
    """Evaluate fitness of an individual using 5-fold cross-validation.

    This function decodes the individual to hyperparameters, creates a model,
    and evaluates it using stratified 5-fold cross-validation with F1-score.

    Handles invalid hyperparameter combinations by returning zero fitness.
    Uses n_jobs=1 in cross_val_score to avoid nested parallelism when
    classifiers already use n_jobs=-1.

    Args:
        individual: List of hyperparameter values from DEAP evolution
        classifier_name: One of 'rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt'
        X_train: Training features (numpy array)
        y_train: Training labels (numpy array)

    Returns:
        Tuple with single fitness value (mean F1-score from CV)
        Returns (0.0,) if evaluation fails due to invalid hyperparameters

    Example:
        >>> ind = [200, 15, 10, 5]  # RF hyperparameters
        >>> fitness = evaluate_individual(ind, 'rf', X_train, y_train)
        >>> print(f"F1-score: {fitness[0]:.4f}")
        F1-score: 0.9247
    """
    try:
        # Decode individual to hyperparameters
        params = decode_individual(classifier_name, individual)

        # Create model with these hyperparameters
        model = create_model_from_params(classifier_name, params)

        # Evaluate with 5-fold stratified CV using F1-score
        f1_scorer = make_scorer(f1_score, average='binary')
        cv_scores = cross_val_score(
            model, X_train, y_train,
            cv=5,  # 5-fold stratified CV
            scoring=f1_scorer,
            n_jobs=1  # Avoid nested parallelism (classifiers use n_jobs=-1)
        )

        # Return mean F1 as fitness (DEAP requires tuple)
        fitness_value = cv_scores.mean()
        logger.debug(
            f"{classifier_name} individual {params}: "
            f"F1={fitness_value:.4f} (std={cv_scores.std():.4f})"
        )

        return (fitness_value,)

    except Exception as e:
        # Invalid hyperparameter combination - return zero fitness
        logger.warning(
            f"Failed to evaluate {classifier_name} individual: {e}. "
            "Returning zero fitness."
        )
        return (0.0,)


def create_fitness_function(
    classifier_name: str,
    X_train: np.ndarray,
    y_train: np.ndarray
) -> Callable[[List[Any]], Tuple[float]]:
    """Create fitness function with closure over training data.

    This factory function creates a fitness evaluation function that captures
    the training data in its closure, suitable for registration with DEAP toolbox.

    Args:
        classifier_name: One of 'rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt'
        X_train: Training features
        y_train: Training labels

    Returns:
        Fitness function that takes individual and returns tuple with F1-score

    Example:
        >>> fitness_func = create_fitness_function('rf', X_train, y_train)
        >>> toolbox.register('evaluate', fitness_func)
        >>> # Later in evolution loop:
        >>> individual = [200, 15, 10, 5]
        >>> fitness = fitness_func(individual)
    """
    def fitness_wrapper(individual: List[Any]) -> Tuple[float]:
        return evaluate_individual(individual, classifier_name, X_train, y_train)

    return fitness_wrapper
