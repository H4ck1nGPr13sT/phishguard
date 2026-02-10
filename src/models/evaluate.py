"""Model evaluation module for comprehensive performance metrics.

This module provides functions to evaluate trained models with all required
metrics: accuracy, precision, recall, F1, AUC-ROC, and confusion matrix.
"""

import logging
from typing import Any, Dict

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report
)
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)


def evaluate_model(
    model: Pipeline,
    X_test: pd.DataFrame,
    y_test: pd.Series
) -> Dict[str, Any]:
    """Comprehensive model evaluation matching requirements EVAL-01, EVAL-02, EVAL-03.

    Args:
        model: Trained sklearn Pipeline
        X_test: Test features
        y_test: Test labels

    Returns:
        Dict with:
        - accuracy, precision, recall, f1_score, roc_auc
        - confusion_matrix: {true_negative, false_positive, false_negative, true_positive}
        - classification_report: detailed per-class metrics

    Example:
        >>> model = load_model(Path('models/rf_pipeline.joblib'))
        >>> metrics = evaluate_model(model, X_test, y_test)
        >>> print(f"Accuracy: {metrics['accuracy']:.4f}")
        >>> print_evaluation_report(metrics)
    """
    logger.info("Evaluating model on test data...")

    # Get predictions and probabilities
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]  # Probability of phishing class (1)

    # Calculate all metrics
    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred, zero_division=0),
        'recall': recall_score(y_test, y_pred, zero_division=0),
        'f1_score': f1_score(y_test, y_pred, zero_division=0),
        'roc_auc': roc_auc_score(y_test, y_proba)
    }

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    metrics['confusion_matrix'] = {
        'true_negative': int(cm[0, 0]),
        'false_positive': int(cm[0, 1]),
        'false_negative': int(cm[1, 0]),
        'true_positive': int(cm[1, 1])
    }

    # Classification report (string format)
    metrics['classification_report'] = classification_report(
        y_test,
        y_pred,
        target_names=['Legitimate', 'Phishing'],
        zero_division=0
    )

    # Test data metadata
    metrics['test_samples'] = len(X_test)

    logger.info(f"Evaluation complete: accuracy={metrics['accuracy']:.4f}")

    return metrics


def print_evaluation_report(metrics: Dict[str, Any]) -> None:
    """Print formatted evaluation report for thesis documentation.

    Args:
        metrics: Metrics dictionary from evaluate_model()

    Example:
        >>> metrics = evaluate_model(model, X_test, y_test)
        >>> print_evaluation_report(metrics)
        ============================================================
        MODEL EVALUATION REPORT
        ============================================================
        Accuracy:  0.9234
        Precision: 0.9012
        ...
    """
    print("=" * 80)
    print("MODEL EVALUATION REPORT")
    print("=" * 80)
    print(f"Test samples: {metrics['test_samples']}")
    print()
    print(f"Accuracy:  {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall:    {metrics['recall']:.4f}")
    print(f"F1 Score:  {metrics['f1_score']:.4f}")
    print(f"ROC AUC:   {metrics['roc_auc']:.4f}")
    print()

    # Confusion matrix
    cm = metrics['confusion_matrix']
    print("Confusion Matrix:")
    print(f"                 Predicted")
    print(f"              Legit  Phishing")
    print(f"Actual Legit  {cm['true_negative']:5d}  {cm['false_positive']:5d}")
    print(f"    Phishing  {cm['false_negative']:5d}  {cm['true_positive']:5d}")
    print()

    # Classification report
    print("Classification Report:")
    print(metrics['classification_report'])

    # Check success criteria
    print("=" * 80)
    if metrics['accuracy'] >= 0.90:
        print("✓ SUCCESS: Accuracy meets 90%+ requirement")
    else:
        print(f"✗ FAIL: Accuracy {metrics['accuracy']:.2%} below 90% threshold")
    print("=" * 80)
