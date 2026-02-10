"""Train initial Random Forest model on Phase 1 cached data.

This script trains the initial model and saves it to models/rf_pipeline.joblib.
"""

import logging
from pathlib import Path

from src.data.pipeline import load_cached_splits
from src.models.train import train_model
from src.models.evaluate import evaluate_model, print_evaluation_report

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Train and evaluate the Random Forest model."""
    logger.info("=" * 80)
    logger.info("Training Random Forest Phishing Detector")
    logger.info("=" * 80)

    # Load Phase 1 cached data
    logger.info("Loading cached data from Phase 1...")
    try:
        splits = load_cached_splits()
        X_train, y_train = splits['train']
        X_val, y_val = splits['val']
        X_test, y_test = splits['test']
    except FileNotFoundError as e:
        logger.error(f"Cache files not found: {e}")
        logger.error("Run Phase 1 pipeline first: python -m src.data.pipeline")
        return

    logger.info(f"Loaded data - Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

    # Filter to numeric features only (exclude metadata columns)
    metadata_cols = ['url', 'content', 'timestamp', 'source']
    feature_cols = [col for col in X_train.columns if col not in metadata_cols]

    logger.info(f"Using {len(feature_cols)} numeric features")
    logger.info(f"Features: {feature_cols[:5]}... (showing first 5)")

    X_train_features = X_train[feature_cols]
    X_val_features = X_val[feature_cols] if len(X_val) > 0 else X_train_features[:0]
    X_test_features = X_test[feature_cols] if len(X_test) > 0 else X_train_features[:0]

    # Prepare save path
    model_path = Path('models/rf_pipeline.joblib')
    model_path.parent.mkdir(parents=True, exist_ok=True)

    # Train model
    logger.info("Starting model training...")
    model, train_metrics = train_model(
        X_train_features, y_train,
        X_val_features, y_val if len(y_val) > 0 else y_train[:0],
        save_path=model_path
    )

    # Evaluate on test set (if available)
    if len(X_test) > 0:
        logger.info("Evaluating model on test set...")
        test_metrics = evaluate_model(model, X_test_features, y_test)
        print_evaluation_report(test_metrics)
    else:
        logger.warning("Test set is empty, using OOB score for validation")
        logger.info(f"OOB Score: {train_metrics['oob_score']:.4f}")
        if train_metrics['oob_score'] >= 0.90:
            print("✓ SUCCESS: OOB score meets 90%+ requirement")
        else:
            print(f"✗ FAIL: OOB score {train_metrics['oob_score']:.2%} below 90% threshold")

    logger.info("=" * 80)
    logger.info("Training complete!")
    logger.info(f"Model saved to: {model_path}")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
