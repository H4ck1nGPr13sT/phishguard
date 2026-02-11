"""Ensemble model creation and aggregation functions.

This module provides functions to create and work with ensemble models:
- VotingClassifier (soft and hard voting)
- StackingClassifier (meta-learning with Logistic Regression)
- Individual prediction extraction for disagreement analysis
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Union

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import StackingClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)


def create_voting_ensemble(
    estimators: List[Tuple[str, Pipeline]],
    voting: str = 'soft'
) -> VotingClassifier:
    """Create a VotingClassifier ensemble.

    Args:
        estimators: List of (name, pipeline) tuples from trained classifiers
        voting: 'soft' (average probabilities) or 'hard' (majority vote)

    Returns:
        VotingClassifier configured with n_jobs=-1

    Note:
        VotingClassifier.fit() will re-fit all estimators on the training data.
        For soft voting, all estimators must support predict_proba().

    Example:
        >>> estimators = [('rf', rf_pipeline), ('svm', svm_pipeline)]
        >>> voting_soft = create_voting_ensemble(estimators, voting='soft')
        >>> voting_soft.fit(X_train, y_train)
        >>> predictions = voting_soft.predict(X_test)
    """
    if voting not in ['soft', 'hard']:
        raise ValueError(f"voting must be 'soft' or 'hard', got: {voting}")

    logger.info(f"Creating {voting} voting ensemble with {len(estimators)} estimators")

    ensemble = VotingClassifier(
        estimators=estimators,
        voting=voting,
        n_jobs=-1
    )

    return ensemble


def create_stacking_ensemble(
    estimators: List[Tuple[str, Pipeline]]
) -> StackingClassifier:
    """Create a StackingClassifier ensemble with Logistic Regression meta-model.

    The stacking ensemble uses 5-fold cross-validation to generate meta-features,
    which prevents data leakage. The meta-model learns to combine predictions
    from base estimators.

    Args:
        estimators: List of (name, pipeline) tuples from trained classifiers

    Returns:
        StackingClassifier with LogisticRegression final estimator

    Note:
        cv=5 ensures meta-model is trained on out-of-fold predictions,
        preventing data leakage. Training will be slower due to 5-fold CV.

    Example:
        >>> estimators = [('rf', rf_pipeline), ('svm', svm_pipeline)]
        >>> stacking = create_stacking_ensemble(estimators)
        >>> stacking.fit(X_train, y_train)
        >>> predictions = stacking.predict(X_test)
    """
    logger.info(f"Creating stacking ensemble with {len(estimators)} base estimators")

    # Meta-model configuration
    final_estimator = LogisticRegression(
        class_weight='balanced',
        max_iter=1000,
        random_state=42
    )

    ensemble = StackingClassifier(
        estimators=estimators,
        final_estimator=final_estimator,
        cv=5,  # 5-fold CV prevents data leakage
        stack_method='auto',  # Use predict_proba if available
        passthrough=False,  # Don't include raw features in meta-model
        n_jobs=-1
    )

    logger.info("Stacking meta-model: LogisticRegression with cv=5")

    return ensemble


def get_individual_predictions(
    voting_model: VotingClassifier,
    X: np.ndarray
) -> Dict[str, dict]:
    """Extract individual predictions from each classifier in a voting ensemble.

    This function accesses each base estimator within the VotingClassifier
    and returns its individual prediction, probability, and confidence.
    Useful for disagreement analysis and explainability.

    Args:
        voting_model: Fitted VotingClassifier
        X: Feature array for single sample (shape: (1, n_features))

    Returns:
        Dict mapping classifier name to prediction details:
        {
            'rf': {
                'phishing_probability': 0.85,
                'prediction': 'phishing',
                'confidence': 0.85
            },
            'svm': {...},
            ...
        }

    Example:
        >>> import numpy as np
        >>> X_sample = X_test[0].reshape(1, -1)
        >>> predictions = get_individual_predictions(voting_soft, X_sample)
        >>> print(predictions['rf']['phishing_probability'])
        0.85
    """
    if not hasattr(voting_model, 'named_estimators_'):
        raise ValueError("VotingClassifier must be fitted before extracting predictions")

    predictions = {}

    for name, estimator in voting_model.named_estimators_.items():
        # Get probability predictions (shape: (1, 2) for binary classification)
        proba = estimator.predict_proba(X)[0]

        # Class 0 = legitimate, Class 1 = phishing
        phishing_proba = proba[1]
        prediction_label = 'phishing' if phishing_proba >= 0.5 else 'legitimate'

        # Confidence is the max probability
        confidence = max(proba)

        predictions[name] = {
            'phishing_probability': float(phishing_proba),
            'prediction': prediction_label,
            'confidence': float(confidence)
        }

    logger.debug(f"Extracted predictions from {len(predictions)} classifiers")

    return predictions


def save_ensemble(
    model: Union[VotingClassifier, StackingClassifier],
    path: Path,
    model_type: str,
    metadata: dict = None
) -> None:
    """Save ensemble model to disk with metadata.

    Args:
        model: Fitted VotingClassifier or StackingClassifier
        path: Output path for .joblib file
        model_type: 'voting_soft', 'voting_hard', or 'stacking'
        metadata: Optional dict with training metrics

    Example:
        >>> save_ensemble(voting_soft, Path('models/ensemble/voting_soft.joblib'),
        ...               model_type='voting_soft', metadata={'accuracy': 0.96})
    """
    # Prepare metadata
    save_metadata = {
        'model_type': model_type,
        'created_at': datetime.utcnow().isoformat(),
        'sklearn_version': sklearn.__version__,
        'n_estimators': len(model.estimators),
        'estimator_names': [name for name, _ in model.estimators] if hasattr(model, 'estimators') else None
    }

    if metadata:
        save_metadata.update(metadata)

    # Save model with compression
    logger.info(f"Saving {model_type} ensemble to {path}")
    joblib.dump(
        {'model': model, 'metadata': save_metadata},
        path,
        compress=3,
        protocol=5
    )

    file_size = path.stat().st_size / (1024 * 1024)  # MB
    logger.info(f"Saved {model_type} ({file_size:.2f} MB)")


def load_ensemble(path: Path) -> Union[VotingClassifier, StackingClassifier]:
    """Load ensemble model from disk.

    Args:
        path: Path to .joblib file

    Returns:
        VotingClassifier or StackingClassifier

    Example:
        >>> model = load_ensemble(Path('models/ensemble/voting_soft.joblib'))
        >>> predictions = model.predict(X_test)
    """
    logger.info(f"Loading ensemble from {path}")

    data = joblib.load(path)

    if isinstance(data, dict) and 'model' in data:
        model = data['model']
        metadata = data.get('metadata', {})
        logger.info(f"Loaded {metadata.get('model_type', 'ensemble')} "
                   f"(created: {metadata.get('created_at', 'unknown')})")
    else:
        # Legacy format (just the model)
        model = data
        logger.info("Loaded ensemble (legacy format)")

    return model
