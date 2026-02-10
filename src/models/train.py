"""Model training pipeline for Random Forest phishing detection.

This module provides the training pipeline that creates and trains a
scikit-learn Pipeline with StandardScaler + RandomForestClassifier.
"""

import logging
from pathlib import Path
from typing import Tuple

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.models.predict import save_model

logger = logging.getLogger(__name__)


def create_pipeline() -> Pipeline:
    """Create sklearn Pipeline with StandardScaler + RandomForestClassifier.

    CRITICAL: Pipeline ensures scaler is fit only on training data,
    preventing data leakage from validation/test sets.

    Returns:
        sklearn Pipeline with scaler and Random Forest classifier

    Example:
        >>> pipeline = create_pipeline()
        >>> pipeline.fit(X_train, y_train)
        >>> y_pred = pipeline.predict(X_test)
    """
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', RandomForestClassifier(
            n_estimators=200,          # More trees for better generalization
            max_depth=15,              # Prevent overfitting
            min_samples_split=10,      # Regularization
            min_samples_leaf=5,        # Regularization
            max_features='sqrt',       # Default, good balance
            class_weight='balanced',   # Handle imbalanced phishing data
            bootstrap=True,
            oob_score=True,            # Free validation estimate
            n_jobs=-1,                 # Use all CPU cores
            random_state=42,           # Reproducibility
            verbose=0
        ))
    ])

    logger.info("Created Pipeline with StandardScaler + RandomForestClassifier")
    return pipeline


def train_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    save_path: Path
) -> Tuple[Pipeline, dict]:
    """Train Random Forest pipeline on training data.

    Args:
        X_train: Training features
        y_train: Training labels
        X_val: Validation features
        y_val: Validation labels
        save_path: Path to save trained model

    Returns:
        Tuple of (trained pipeline, training metrics dict)

    Example:
        >>> pipeline, metrics = train_model(
        ...     X_train, y_train,
        ...     X_val, y_val,
        ...     Path('models/rf_pipeline.joblib')
        ... )
        >>> print(f"Training accuracy: {metrics['train_accuracy']:.4f}")
        >>> print(f"Validation accuracy: {metrics['val_accuracy']:.4f}")
    """
    logger.info("=" * 80)
    logger.info("Training Random Forest pipeline")
    logger.info("=" * 80)
    logger.info(f"Training samples: {len(X_train)}")
    logger.info(f"Validation samples: {len(X_val)}")
    logger.info(f"Features: {X_train.shape[1]}")

    # Create pipeline
    pipeline = create_pipeline()

    # Train pipeline (fit_transform on training only)
    logger.info("Fitting pipeline on training data...")
    pipeline.fit(X_train, y_train)

    # Evaluate on training and validation data
    train_score = pipeline.score(X_train, y_train)
    oob_score = pipeline.named_steps['classifier'].oob_score_

    logger.info(f"Training accuracy: {train_score:.4f}")
    logger.info(f"OOB score: {oob_score:.4f}")

    # Validate if validation set is not empty
    val_score = None
    if len(X_val) > 0:
        val_score = pipeline.score(X_val, y_val)
        logger.info(f"Validation accuracy: {val_score:.4f}")

        # Check for overfitting
        train_val_gap = train_score - val_score
        if train_val_gap > 0.1:
            logger.warning(
                f"Possible overfitting detected: train-val gap = {train_val_gap:.4f} (>10%)"
            )
    else:
        logger.warning("Validation set is empty, skipping validation evaluation")

    # Prepare metrics
    metrics = {
        'train_accuracy': train_score,
        'oob_score': oob_score,
        'val_accuracy': val_score,
        'train_samples': len(X_train),
        'val_samples': len(X_val),
        'feature_count': X_train.shape[1],
        'feature_names': list(X_train.columns)
    }

    # Save model with metadata
    logger.info(f"Saving model to {save_path}...")
    save_model(pipeline, save_path, metadata=metrics)

    logger.info("=" * 80)
    logger.info("Training complete")
    logger.info("=" * 80)

    return pipeline, metrics
