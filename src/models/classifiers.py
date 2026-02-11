"""Classifier factory for ensemble learning.

This module provides factory functions to create all 7 classifiers used in the
phishing detection ensemble. Each classifier is wrapped in a Pipeline with
StandardScaler to prevent data leakage.
"""

import logging
from typing import Dict

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

logger = logging.getLogger(__name__)


# Configuration for each classifier (optimized hyperparameters from research)
CLASSIFIER_CONFIGS = {
    'rf': {
        'class': RandomForestClassifier,
        'params': {
            'n_estimators': 200,
            'max_depth': 15,
            'min_samples_split': 10,
            'min_samples_leaf': 5,
            'class_weight': 'balanced',
            'oob_score': True,
            'n_jobs': -1,
            'random_state': 42
        }
    },
    'svm': {
        'class': SVC,
        'params': {
            'C': 1.0,
            'kernel': 'rbf',
            'gamma': 'scale',
            'probability': True,  # CRITICAL: Required for soft voting
            'class_weight': 'balanced',
            'random_state': 42
        }
    },
    'mlp': {
        'class': MLPClassifier,
        'params': {
            'hidden_layer_sizes': (100,),
            'activation': 'relu',
            'solver': 'adam',
            'alpha': 0.0001,
            'max_iter': 500,
            'random_state': 42
        }
    },
    'xgb': {
        'class': XGBClassifier,
        'params': {
            'n_estimators': 100,
            'max_depth': 6,
            'learning_rate': 0.1,
            'random_state': 42,
            'n_jobs': 1  # Prevent thread thrashing with sklearn
        }
    },
    'lr': {
        'class': LogisticRegression,
        'params': {
            'C': 1.0,
            'max_iter': 1000,
            'class_weight': 'balanced',
            'random_state': 42,
            'n_jobs': -1
        }
    },
    'nb': {
        'class': GaussianNB,
        'params': {
            'var_smoothing': 1e-9
        }
    },
    'dt': {
        'class': DecisionTreeClassifier,
        'params': {
            'max_depth': 10,
            'min_samples_split': 10,
            'min_samples_leaf': 5,
            'class_weight': 'balanced',
            'random_state': 42
        }
    }
}


def create_classifiers() -> Dict[str, Pipeline]:
    """Create all 7 classifiers wrapped in Pipelines with StandardScaler.

    Each classifier is wrapped in a scikit-learn Pipeline with:
    1. StandardScaler - Normalizes features to prevent feature scale bias
    2. Classifier - The actual ML algorithm

    The Pipeline ensures the scaler is fit only on training data,
    preventing data leakage from validation/test sets.

    Returns:
        Dict mapping classifier name to sklearn Pipeline

    Example:
        >>> classifiers = create_classifiers()
        >>> print(list(classifiers.keys()))
        ['rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt']
        >>> rf_pipeline = classifiers['rf']
        >>> rf_pipeline.fit(X_train, y_train)
        >>> predictions = rf_pipeline.predict(X_test)
    """
    classifiers = {}

    for name, config in CLASSIFIER_CONFIGS.items():
        classifier_class = config['class']
        params = config['params']

        # Create pipeline with scaler + classifier
        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', classifier_class(**params))
        ])

        classifiers[name] = pipeline
        logger.debug(f"Created pipeline for {name}: {classifier_class.__name__}")

    logger.info(f"Created {len(classifiers)} classifier pipelines")
    return classifiers


def get_classifier(name: str) -> Pipeline:
    """Get a single classifier pipeline by name.

    Args:
        name: Classifier name (rf, svm, mlp, xgb, lr, nb, dt)

    Returns:
        sklearn Pipeline with StandardScaler + classifier

    Raises:
        ValueError: If classifier name is not recognized

    Example:
        >>> svm_pipeline = get_classifier('svm')
        >>> svm_pipeline.fit(X_train, y_train)
    """
    if name not in CLASSIFIER_CONFIGS:
        valid_names = list(CLASSIFIER_CONFIGS.keys())
        raise ValueError(
            f"Unknown classifier: {name}. Valid options: {valid_names}"
        )

    config = CLASSIFIER_CONFIGS[name]
    classifier_class = config['class']
    params = config['params']

    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', classifier_class(**params))
    ])

    logger.info(f"Created {name} pipeline: {classifier_class.__name__}")
    return pipeline
