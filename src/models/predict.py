"""Model prediction and persistence module.

This module provides functions for saving/loading trained models and making
predictions on new data.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)


def save_model(model: Pipeline, path: Path, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Save model with joblib (protocol=5, compress=3).

    Saves dict with:
    - 'model': trained Pipeline
    - 'sklearn_version': for compatibility checking
    - 'saved_at': ISO timestamp
    - 'metadata': custom metadata (features, metrics, etc.)

    Args:
        model: Trained sklearn Pipeline
        path: Path to save model (should end with .joblib)
        metadata: Optional metadata dict to save with model

    Example:
        >>> model = create_pipeline()
        >>> model.fit(X_train, y_train)
        >>> save_model(model, Path('models/rf_pipeline.joblib'), metadata={'accuracy': 0.95})
    """
    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Prepare model data with metadata
    model_data = {
        'model': model,
        'sklearn_version': sklearn.__version__,
        'saved_at': datetime.now().isoformat(),
        'metadata': metadata or {}
    }

    # Save with joblib (protocol=5 for NumPy optimization, compress=3 for size)
    joblib.dump(model_data, path, compress=3, protocol=5)

    logger.info(f"Model saved to {path}")
    logger.info(f"sklearn version: {sklearn.__version__}")
    logger.info(f"File size: {path.stat().st_size / 1024:.2f} KB")


def load_model(path: Path, check_version: bool = True) -> Pipeline:
    """Load saved model with optional version checking.

    Args:
        path: Path to .joblib file
        check_version: Warn if sklearn version mismatch

    Returns:
        Trained sklearn Pipeline

    Raises:
        FileNotFoundError: If model file doesn't exist

    Example:
        >>> model = load_model(Path('models/rf_pipeline.joblib'))
        >>> predictions = model.predict(X_test)
    """
    if not path.exists():
        raise FileNotFoundError(f"Model not found: {path}")

    logger.info(f"Loading model from {path}...")

    # Load model data
    model_data = joblib.load(path)

    # Handle both dict format (with metadata) and direct Pipeline format
    if isinstance(model_data, dict) and 'model' in model_data:
        # Dict format with metadata
        if check_version and 'sklearn_version' in model_data:
            saved_version = model_data['sklearn_version']
            current_version = sklearn.__version__
            if saved_version != current_version:
                logger.warning(
                    f"Model trained with sklearn {saved_version}, "
                    f"loading with {current_version}. Behavior may differ."
                )
        model = model_data['model']
    else:
        # Direct Pipeline format (from retraining script)
        model = model_data
        model_data = {'metadata': {}}  # Create empty metadata for compatibility

    logger.info(f"Model loaded successfully: {type(model).__name__}")

    # Log metadata if available
    if 'metadata' in model_data and model_data['metadata']:
        logger.info(f"Model metadata: {model_data['metadata']}")

    return model


def predict_single(model: Pipeline, features: Dict[str, float]) -> Dict[str, Any]:
    """Predict phishing probability for single URL features.

    Args:
        model: Loaded sklearn Pipeline
        features: Dict of features from extract_url_features()

    Returns:
        Dict with: phishing_probability, prediction, confidence

    Example:
        >>> model = load_model(Path('models/rf_pipeline.joblib'))
        >>> features = {'url_length': 45, 'has_https': 1, ...}
        >>> result = predict_single(model, features)
        >>> print(f"Phishing probability: {result['phishing_probability']:.2%}")
    """
    # Convert features dict to array
    feature_array = np.array([list(features.values())])

    # Get prediction probabilities
    proba = model.predict_proba(feature_array)[0]

    # Prepare result
    result = {
        'phishing_probability': float(proba[1]),  # Probability of class 1 (phishing)
        'prediction': 'phishing' if proba[1] > 0.5 else 'legitimate',
        'confidence': float(max(proba))
    }

    return result


def predict_batch(model: Pipeline, features_list: List[Dict[str, float]]) -> List[Dict[str, Any]]:
    """Predict phishing probability for multiple URLs.

    Args:
        model: Loaded sklearn Pipeline
        features_list: List of feature dicts

    Returns:
        List of prediction dicts (same format as predict_single)

    Example:
        >>> model = load_model(Path('models/rf_pipeline.joblib'))
        >>> features_list = [
        ...     {'url_length': 45, 'has_https': 1, ...},
        ...     {'url_length': 120, 'has_https': 0, ...}
        ... ]
        >>> results = predict_batch(model, features_list)
        >>> for i, result in enumerate(results):
        ...     print(f"URL {i}: {result['prediction']} ({result['confidence']:.2%})")
    """
    # Convert list of dicts to 2D array
    feature_arrays = [list(features.values()) for features in features_list]
    X = np.array(feature_arrays)

    # Get prediction probabilities
    probas = model.predict_proba(X)

    # Prepare results
    results = []
    for proba in probas:
        result = {
            'phishing_probability': float(proba[1]),
            'prediction': 'phishing' if proba[1] > 0.5 else 'legitimate',
            'confidence': float(max(proba))
        }
        results.append(result)

    return results
