"""Train all 6 new classifiers for ensemble learning.

This script trains SVM, MLP, XGBoost, Logistic Regression, Naive Bayes, and
Decision Tree classifiers using the same data as the existing Random Forest.
Each classifier is wrapped in a Pipeline with StandardScaler and saved to models/.
"""

import logging
import time
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline

from src.data.pipeline import load_cached_splits
from src.models.classifiers import create_classifiers
from src.models.predict import save_model

logger = logging.getLogger(__name__)


def train_all_classifiers(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    output_dir: Path
) -> Dict[str, dict]:
    """Train all classifiers and save to output directory.

    Args:
        X_train: Training features (numeric only)
        y_train: Training labels
        output_dir: Directory to save trained models

    Returns:
        Dict mapping classifier name to metrics dict

    Example:
        >>> results = train_all_classifiers(X_train, y_train, Path('models'))
        >>> for name, metrics in results.items():
        ...     print(f"{name}: {metrics['cv_accuracy']:.4f}")
    """
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get all classifiers
    classifiers = create_classifiers()

    # Skip RF since it's already trained in Phase 2
    classifiers_to_train = {k: v for k, v in classifiers.items() if k != 'rf'}

    logger.info("=" * 80)
    logger.info(f"Training {len(classifiers_to_train)} ensemble classifiers")
    logger.info("=" * 80)
    logger.info(f"Training samples: {len(X_train)}")
    logger.info(f"Features: {X_train.shape[1]}")
    logger.info(f"Classifiers to train: {list(classifiers_to_train.keys())}")

    results = {}

    for name, pipeline in classifiers_to_train.items():
        logger.info("-" * 80)
        logger.info(f"Training {name.upper()} classifier...")
        logger.info("-" * 80)

        start_time = time.time()

        # Train the pipeline
        pipeline.fit(X_train, y_train)
        train_time = time.time() - start_time

        # Calculate training accuracy
        train_accuracy = pipeline.score(X_train, y_train)

        # Get validation accuracy
        # For RF and DT with oob_score, use that
        # For others, use 5-fold cross-validation
        classifier = pipeline.named_steps['classifier']

        if hasattr(classifier, 'oob_score_'):
            # Use OOB score for Random Forest / Decision Tree
            cv_accuracy = classifier.oob_score_
            validation_method = 'OOB'
        else:
            # Use cross-validation for other classifiers
            logger.info(f"Running 5-fold cross-validation for {name}...")
            cv_scores = cross_val_score(
                pipeline, X_train, y_train, cv=5, scoring='accuracy', n_jobs=-1
            )
            cv_accuracy = cv_scores.mean()
            cv_std = cv_scores.std()
            validation_method = f'5-fold CV (std={cv_std:.4f})'

        logger.info(f"Training accuracy: {train_accuracy:.4f}")
        logger.info(f"Validation accuracy ({validation_method}): {cv_accuracy:.4f}")
        logger.info(f"Training time: {train_time:.2f}s")

        # Prepare metrics
        metrics = {
            'train_accuracy': train_accuracy,
            'cv_accuracy': cv_accuracy,
            'train_time': train_time,
            'validation_method': validation_method,
            'train_samples': len(X_train),
            'feature_count': X_train.shape[1],
            'feature_names': list(X_train.columns)
        }

        # Save model
        model_path = output_dir / f"{name}_pipeline.joblib"
        logger.info(f"Saving {name} model to {model_path}...")
        save_model(pipeline, model_path, metadata=metrics)

        results[name] = metrics

        logger.info(f"✓ {name.upper()} complete!")

    logger.info("=" * 80)
    logger.info("All classifiers trained successfully!")
    logger.info("=" * 80)

    return results


def print_summary_table(results: Dict[str, dict]) -> None:
    """Print formatted summary table of all classifier results.

    Args:
        results: Dict from train_all_classifiers()
    """
    print("\n" + "=" * 100)
    print("ENSEMBLE TRAINING SUMMARY")
    print("=" * 100)
    print(f"{'Classifier':<20} {'Train Acc':<12} {'CV/OOB Acc':<12} {'Time (s)':<12} {'Status':<20}")
    print("-" * 100)

    for name, metrics in sorted(results.items()):
        train_acc = metrics['train_accuracy']
        cv_acc = metrics['cv_accuracy']
        train_time = metrics['train_time']

        # Check if meets >80% requirement
        status = "✓ PASS (>80%)" if cv_acc > 0.80 else "✗ FAIL (<80%)"

        print(f"{name.upper():<20} {train_acc:<12.4f} {cv_acc:<12.4f} {train_time:<12.2f} {status:<20}")

    print("=" * 100)

    # Overall summary
    all_pass = all(m['cv_accuracy'] > 0.80 for m in results.values())
    total_time = sum(m['train_time'] for m in results.values())
    avg_accuracy = sum(m['cv_accuracy'] for m in results.values()) / len(results)

    print(f"\nTotal training time: {total_time:.2f}s")
    print(f"Average accuracy: {avg_accuracy:.4f}")
    print(f"All classifiers >80% accuracy: {all_pass}")
    print("=" * 100 + "\n")


def main():
    """Main training script."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("=" * 80)
    logger.info("Ensemble Classifier Training")
    logger.info("=" * 80)

    # Load Phase 1 cached data
    logger.info("Loading cached data from Phase 1...")
    try:
        splits = load_cached_splits()
        X_train, y_train = splits['train']
    except FileNotFoundError as e:
        logger.error(f"Cache files not found: {e}")
        logger.error("Run Phase 1 pipeline first: python -m src.data.pipeline")
        return

    logger.info(f"Loaded training data: {len(X_train)} samples")

    # Filter to numeric features only (exclude metadata columns)
    metadata_cols = ['url', 'content', 'timestamp', 'source']
    feature_cols = [col for col in X_train.columns if col not in metadata_cols]

    logger.info(f"Using {len(feature_cols)} numeric features")
    logger.info(f"Features: {feature_cols[:5]}... (showing first 5)")

    X_train_features = X_train[feature_cols]

    # Train all classifiers
    output_dir = Path('models')
    results = train_all_classifiers(X_train_features, y_train, output_dir)

    # Print summary table
    print_summary_table(results)

    logger.info("Training complete! All models saved to models/ directory.")


if __name__ == '__main__':
    main()
