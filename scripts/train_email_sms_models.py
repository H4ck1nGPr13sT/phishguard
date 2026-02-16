#!/usr/bin/env python3
"""Train models with email/SMS features.

This script:
1. Loads email/SMS sample datasets
2. Extracts features using unified extractor
3. Trains all 7 classifiers on combined feature set
4. Saves models to models/email_sms/ with metadata
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

from src.features.extractors import extract_email_features, extract_sms_features, ContentType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_datasets() -> Tuple[List[Dict], List[Dict]]:
    """Load email and SMS datasets from JSON files."""
    email_path = Path("data/email_sms/email_samples.json")
    sms_path = Path("data/email_sms/sms_samples.json")

    with open(email_path) as f:
        email_data = json.load(f)

    with open(sms_path) as f:
        sms_data = json.load(f)

    logger.info(f"Loaded {len(email_data)} email samples")
    logger.info(f"Loaded {len(sms_data)} SMS samples")

    return email_data, sms_data


def extract_all_features(samples: List[Dict], content_type: ContentType) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """Extract features from all samples.

    Args:
        samples: List of dicts with 'content' and 'label' keys
        content_type: EMAIL or SMS

    Returns:
        Tuple of (features array, labels array, feature names list)
    """
    features = []
    labels = []
    feature_names = None

    for sample in samples:
        try:
            if content_type == ContentType.EMAIL:
                feats = extract_email_features(sample["content"].encode())
            else:
                feats = extract_sms_features(sample["content"])

            # Get feature names from first sample
            if feature_names is None:
                feature_names = list(feats.keys())

            features.append(list(feats.values()))
            labels.append(sample["label"])
        except Exception as e:
            logger.warning(f"Failed to extract features: {e}")

    return np.array(features), np.array(labels), feature_names


def get_classifiers() -> Dict[str, object]:
    """Create all 7 classifiers with baseline configurations.

    Returns dictionary of classifier name -> classifier instance.
    """
    return {
        "rf": RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        ),
        "svm": SVC(
            kernel='rbf',
            C=1.0,
            gamma='scale',
            probability=True,
            class_weight='balanced',
            random_state=42
        ),
        "mlp": MLPClassifier(
            hidden_layer_sizes=(100, 50),
            max_iter=500,
            alpha=0.001,
            random_state=42
        ),
        "xgb": XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            n_jobs=1,  # Prevent thread thrashing
            random_state=42
        ),
        "lr": LogisticRegression(
            C=1.0,
            max_iter=1000,
            penalty='l2',
            solver='lbfgs',
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        ),
        "nb": GaussianNB(
            var_smoothing=1e-9
        ),
        "dt": DecisionTreeClassifier(
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5,
            class_weight='balanced',
            random_state=42
        ),
    }


def train_classifier(name: str, clf: object, X_train: np.ndarray, y_train: np.ndarray,
                     X_test: np.ndarray, y_test: np.ndarray) -> Tuple[Pipeline, float]:
    """Train a single classifier with StandardScaler pipeline.

    Args:
        name: Classifier name
        clf: Classifier instance
        X_train: Training features
        y_train: Training labels
        X_test: Test features
        y_test: Test labels

    Returns:
        Tuple of (trained pipeline, test accuracy)
    """
    logger.info(f"Training {name}...")
    start_time = time.time()

    # Create pipeline with scaler
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", clf)
    ])

    # Train
    pipeline.fit(X_train, y_train)

    # Evaluate
    train_accuracy = pipeline.score(X_train, y_train)
    test_accuracy = pipeline.score(X_test, y_test)

    duration = time.time() - start_time

    logger.info(f"  {name}: train={train_accuracy:.4f}, test={test_accuracy:.4f} ({duration:.1f}s)")

    return pipeline, test_accuracy


def save_model(model: object, name: str, output_dir: Path, feature_names: List[str],
               content_type: str, accuracy: float):
    """Save model with metadata.

    Args:
        model: Trained model/pipeline
        name: Model name (e.g., 'rf', 'ensemble')
        output_dir: Directory to save to
        feature_names: List of feature names
        content_type: 'email' or 'sms'
        accuracy: Test accuracy
    """
    output_path = output_dir / f"{name}_{content_type}.joblib"

    model_data = {
        "model": model,
        "feature_names": feature_names,
        "content_type": content_type,
        "feature_count": len(feature_names),
        "test_accuracy": accuracy,
        "created_at": datetime.now().isoformat(),
        "model_type": name
    }

    joblib.dump(model_data, output_path, compress=3, protocol=5)
    logger.info(f"  Saved: {output_path} ({len(feature_names)} features, {accuracy:.4f} accuracy)")


def train_ensemble(classifiers: Dict[str, Pipeline], X_train: np.ndarray, y_train: np.ndarray,
                   X_test: np.ndarray, y_test: np.ndarray) -> Tuple[VotingClassifier, float]:
    """Train soft voting ensemble.

    Args:
        classifiers: Dict of trained classifier pipelines
        X_train: Training features
        y_train: Training labels
        X_test: Test features
        y_test: Test labels

    Returns:
        Tuple of (ensemble, test accuracy)
    """
    logger.info("Training ensemble (soft voting)...")
    start_time = time.time()

    # Get fitted classifiers from pipelines
    estimators = [(name, pipeline) for name, pipeline in classifiers.items()]

    # Create soft voting ensemble
    ensemble = VotingClassifier(
        estimators=estimators,
        voting='soft',
        n_jobs=-1
    )

    # Note: Ensemble needs to be fitted even though base estimators are trained
    # because VotingClassifier needs to learn from the training data
    ensemble.fit(X_train, y_train)

    # Evaluate
    train_accuracy = ensemble.score(X_train, y_train)
    test_accuracy = ensemble.score(X_test, y_test)

    duration = time.time() - start_time

    logger.info(f"  Ensemble: train={train_accuracy:.4f}, test={test_accuracy:.4f} ({duration:.1f}s)")

    return ensemble, test_accuracy


def validate_models(output_dir: Path, expected_feature_counts: Dict[str, int]):
    """Validate that saved models can load and predict.

    Args:
        output_dir: Directory containing saved models
        expected_feature_counts: Dict of content_type -> expected feature count
    """
    logger.info("\nValidating saved models...")

    for model_path in sorted(output_dir.glob("*.joblib")):
        try:
            # Load model
            model_data = joblib.load(model_path)
            model = model_data["model"]
            content_type = model_data["content_type"]
            feature_count = model_data["feature_count"]

            # Verify feature count
            expected_count = expected_feature_counts.get(content_type)
            if expected_count and feature_count != expected_count:
                logger.warning(f"  {model_path.name}: feature count mismatch (got {feature_count}, expected {expected_count})")

            # Test prediction with dummy data
            dummy_features = np.zeros((1, feature_count))
            pred = model.predict(dummy_features)
            prob = model.predict_proba(dummy_features) if hasattr(model, 'predict_proba') else None

            logger.info(f"  ✓ {model_path.name}: loaded OK, prediction={pred[0]}, features={feature_count}")

        except Exception as e:
            logger.error(f"  ✗ {model_path.name}: FAILED - {e}")
            raise


def train_all() -> Dict[str, Dict[str, float]]:
    """Main training pipeline.

    Returns:
        Dict of model_name -> accuracy metrics
    """
    logger.info("=" * 80)
    logger.info("TRAINING EMAIL/SMS PHISHING DETECTION MODELS")
    logger.info("=" * 80)

    # Load datasets
    email_data, sms_data = load_datasets()

    # Output directory
    output_dir = Path("models/email_sms")
    output_dir.mkdir(parents=True, exist_ok=True)

    all_accuracies = {}

    # Train for EMAIL
    logger.info("\n" + "=" * 80)
    logger.info("TRAINING EMAIL MODELS")
    logger.info("=" * 80)

    X_email, y_email, email_feature_names = extract_all_features(email_data, ContentType.EMAIL)
    logger.info(f"Email features extracted: {X_email.shape[1]} features, {len(X_email)} samples")

    X_train_email, X_test_email, y_train_email, y_test_email = train_test_split(
        X_email, y_email, test_size=0.2, random_state=42, stratify=y_email
    )
    logger.info(f"Train: {len(X_train_email)}, Test: {len(X_test_email)}")

    # Train individual classifiers
    classifiers_email = {}
    accuracies_email = {}

    for name, clf in get_classifiers().items():
        pipeline, accuracy = train_classifier(name, clf, X_train_email, y_train_email,
                                              X_test_email, y_test_email)
        classifiers_email[name] = pipeline
        accuracies_email[name] = accuracy
        save_model(pipeline, name, output_dir, email_feature_names, "email", accuracy)

    # Train ensemble
    ensemble_email, ensemble_accuracy_email = train_ensemble(
        classifiers_email, X_train_email, y_train_email, X_test_email, y_test_email
    )
    save_model(ensemble_email, "ensemble", output_dir, email_feature_names, "email", ensemble_accuracy_email)

    all_accuracies["email"] = {**accuracies_email, "ensemble": ensemble_accuracy_email}

    # Train for SMS
    logger.info("\n" + "=" * 80)
    logger.info("TRAINING SMS MODELS")
    logger.info("=" * 80)

    X_sms, y_sms, sms_feature_names = extract_all_features(sms_data, ContentType.SMS)
    logger.info(f"SMS features extracted: {X_sms.shape[1]} features, {len(X_sms)} samples")

    X_train_sms, X_test_sms, y_train_sms, y_test_sms = train_test_split(
        X_sms, y_sms, test_size=0.2, random_state=42, stratify=y_sms
    )
    logger.info(f"Train: {len(X_train_sms)}, Test: {len(X_test_sms)}")

    # Train individual classifiers
    classifiers_sms = {}
    accuracies_sms = {}

    for name, clf in get_classifiers().items():
        pipeline, accuracy = train_classifier(name, clf, X_train_sms, y_train_sms,
                                              X_test_sms, y_test_sms)
        classifiers_sms[name] = pipeline
        accuracies_sms[name] = accuracy
        save_model(pipeline, name, output_dir, sms_feature_names, "sms", accuracy)

    # Train ensemble
    ensemble_sms, ensemble_accuracy_sms = train_ensemble(
        classifiers_sms, X_train_sms, y_train_sms, X_test_sms, y_test_sms
    )
    save_model(ensemble_sms, "ensemble", output_dir, sms_feature_names, "sms", ensemble_accuracy_sms)

    all_accuracies["sms"] = {**accuracies_sms, "ensemble": ensemble_accuracy_sms}

    # Validate saved models
    expected_counts = {
        "email": len(email_feature_names),
        "sms": len(sms_feature_names)
    }
    validate_models(output_dir, expected_counts)

    return all_accuracies


def main():
    """Execute training and report results."""
    start_time = time.time()

    # Train all models
    all_accuracies = train_all()

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TRAINING COMPLETE")
    logger.info("=" * 80)

    logger.info("\nEMAIL MODEL ACCURACIES:")
    for model_name, accuracy in sorted(all_accuracies["email"].items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {model_name:10}: {accuracy:.4f}")

    logger.info("\nSMS MODEL ACCURACIES:")
    for model_name, accuracy in sorted(all_accuracies["sms"].items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {model_name:10}: {accuracy:.4f}")

    # Check threshold
    email_min = min(all_accuracies["email"].values())
    sms_min = min(all_accuracies["sms"].values())
    overall_min = min(email_min, sms_min)

    email_avg = sum(all_accuracies["email"].values()) / len(all_accuracies["email"])
    sms_avg = sum(all_accuracies["sms"].values()) / len(all_accuracies["sms"])

    logger.info("\n" + "=" * 80)
    logger.info(f"Email: min={email_min:.4f}, avg={email_avg:.4f}")
    logger.info(f"SMS:   min={sms_min:.4f}, avg={sms_avg:.4f}")
    logger.info(f"Overall min: {overall_min:.4f}")

    if overall_min < 0.80:
        logger.warning("⚠ WARNING: Some models below 80% accuracy threshold")
    else:
        logger.info("✓ SUCCESS: All models meet 80% accuracy threshold")

    duration = time.time() - start_time
    logger.info(f"\nTotal training time: {duration:.1f}s")


if __name__ == "__main__":
    main()
