"""Train Bayesian classifier for Phase 5 multi-paradigm detection.

Uses same training data as Phase 3 ensemble classifiers.
Saves model to models/bayesian/bayesian_classifier.joblib
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from sklearn.model_selection import cross_val_score

from src.paradigms.bayesian import BayesianClassifier


def load_training_data():
    """Load training data used for Phase 3 ensemble."""
    import joblib

    # Try loading from cache first
    cache_path = Path("cache/url_training_data.joblib")
    if cache_path.exists():
        data = joblib.load(cache_path)
        return data['X_train'], data['y_train']

    # Fallback: Load from train_balanced
    retrain_cache = Path("cache/train_balanced.joblib")
    if retrain_cache.exists():
        data = joblib.load(retrain_cache)
        # Extract features and labels from DataFrame
        if hasattr(data, 'columns'):
            y = data['label'].values
            X = data.drop(columns=['label']).values
            return X, y
        return data['X_train'], data['y_train']

    raise FileNotFoundError(
        "Training data not found. Run ensemble training first: "
        "python scripts/retrain_with_urls.py"
    )


def main():
    print("Loading training data...")
    X_train, y_train = load_training_data()
    print(f"Loaded {len(X_train)} samples, {X_train.shape[1]} features")
    print(f"Class distribution: {dict(zip(*np.unique(y_train, return_counts=True)))}")

    # Initialize and train classifier
    print("\nTraining Bayesian classifier...")
    classifier = BayesianClassifier(var_smoothing=1e-9)
    classifier.fit(X_train, y_train)

    # Cross-validation score
    print("\nPerforming 5-fold cross-validation...")
    cv_scores = cross_val_score(classifier.pipeline, X_train, y_train, cv=5, scoring='f1')
    print(f"5-fold CV F1 scores: {cv_scores}")
    print(f"Mean F1: {np.mean(cv_scores):.4f} (+/- {np.std(cv_scores)*2:.4f})")

    # Save model
    output_dir = Path("models/bayesian")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "bayesian_classifier.joblib"
    classifier.save(output_path)
    print(f"\nModel saved to {output_path}")

    # Test prediction
    print("\nTest prediction on first sample:")
    result = classifier.predict_with_posterior(X_train[:1])
    print(f"  Posterior phishing: {result['posterior_phishing']:.4f}")
    print(f"  Posterior legitimate: {result['posterior_legitimate']:.4f}")
    print(f"  Prediction: {result['prediction']}")
    print(f"  Confidence: {result['confidence']:.4f}")
    print(f"  Prior phishing: {result['prior_info']['prior_phishing']:.4f}")


if __name__ == "__main__":
    main()
