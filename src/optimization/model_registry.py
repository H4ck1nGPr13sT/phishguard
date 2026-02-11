"""Model registry for versioning and comparison of ML models.

This module provides a registry system for managing baseline and GA-optimized
model versions. It supports:

- Model registration with version tags (baseline, ga_optimized)
- Version comparison with improvement metrics
- Active model selection and loading
- MLflow integration for tracking

Integration pattern:
- Register models with metrics and metadata
- Compare versions on same test set
- Set active version (defaults to optimized if available)
- API loads active models from registry
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import mlflow
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

logger = logging.getLogger(__name__)


def register_model(
    model_path: Path,
    model_type: str,
    classifier_name: str,
    metrics: Dict[str, float],
    version_tag: str,
    hyperparams: Optional[Dict[str, Any]] = None,
    optimization_method: Optional[str] = None
) -> str:
    """Register model in MLflow Model Registry with metrics and metadata.

    Args:
        model_path: Path to saved model file
        model_type: Type of model (classifier, ensemble)
        classifier_name: Name (rf, svm, mlp, xgb, lr, nb, dt, ensemble)
        metrics: Dict with accuracy, f1, precision, recall
        version_tag: Version identifier ("baseline", "ga_optimized")
        hyperparams: Hyperparameter dictionary (optional)
        optimization_method: Method used for optimization (optional)

    Returns:
        Registered model version ID

    Example:
        >>> register_model(
        ...     Path("models/rf_pipeline.joblib"),
        ...     "classifier", "rf",
        ...     {"accuracy": 0.96, "f1": 0.95},
        ...     "baseline"
        ... )
    """
    # Start MLflow run for registration
    with mlflow.start_run(run_name=f"{classifier_name}_{version_tag}"):
        # Log metrics
        for metric_name, metric_value in metrics.items():
            mlflow.log_metric(metric_name, metric_value)

        # Log hyperparameters if provided
        if hyperparams:
            for param_name, param_value in hyperparams.items():
                mlflow.log_param(param_name, param_value)

        # Log tags
        mlflow.set_tags({
            "model_type": model_type,
            "classifier_name": classifier_name,
            "version_tag": version_tag,
            "optimization_method": optimization_method or "none"
        })

        # Log model artifact
        mlflow.log_artifact(str(model_path))

        run_id = mlflow.active_run().info.run_id
        logger.info(
            f"Registered {classifier_name} ({version_tag}): "
            f"f1={metrics.get('f1', 0):.4f}, run_id={run_id}"
        )

        return run_id


def compare_versions(
    classifier_name: str,
    baseline_model: Any,
    optimized_model: Any,
    X_test: np.ndarray,
    y_test: np.ndarray
) -> Dict[str, Any]:
    """Compare baseline vs optimized model versions on same test set.

    Args:
        classifier_name: Classifier name
        baseline_model: Baseline model (sklearn Pipeline)
        optimized_model: Optimized model (sklearn Pipeline)
        X_test: Test features
        y_test: Test labels

    Returns:
        Dict with baseline, optimized metrics and improvements

    Example:
        >>> results = compare_versions("rf", baseline, optimized, X_test, y_test)
        >>> print(f"F1 improvement: {results['improvement']['f1_pct']:.2f}%")
    """
    # Evaluate baseline
    y_pred_baseline = baseline_model.predict(X_test)
    y_proba_baseline = baseline_model.predict_proba(X_test)[:, 1]

    baseline_metrics = {
        "accuracy": accuracy_score(y_test, y_pred_baseline),
        "f1": f1_score(y_test, y_pred_baseline),
        "precision": precision_score(y_test, y_pred_baseline),
        "recall": recall_score(y_test, y_pred_baseline),
        "auc_roc": roc_auc_score(y_test, y_proba_baseline)
    }

    # Evaluate optimized
    y_pred_optimized = optimized_model.predict(X_test)
    y_proba_optimized = optimized_model.predict_proba(X_test)[:, 1]

    optimized_metrics = {
        "accuracy": accuracy_score(y_test, y_pred_optimized),
        "f1": f1_score(y_test, y_pred_optimized),
        "precision": precision_score(y_test, y_pred_optimized),
        "recall": recall_score(y_test, y_pred_optimized),
        "auc_roc": roc_auc_score(y_test, y_proba_optimized)
    }

    # Calculate improvements
    improvements = {}
    for metric in ["accuracy", "f1", "precision", "recall", "auc_roc"]:
        baseline_val = baseline_metrics[metric]
        optimized_val = optimized_metrics[metric]

        # Absolute improvement
        improvements[f"{metric}_abs"] = optimized_val - baseline_val

        # Percentage improvement
        if baseline_val > 0:
            improvements[f"{metric}_pct"] = (optimized_val - baseline_val) / baseline_val * 100
        else:
            improvements[f"{metric}_pct"] = 0.0

    return {
        "classifier": classifier_name,
        "baseline": baseline_metrics,
        "optimized": optimized_metrics,
        "improvement": improvements
    }


def generate_comparison_report(
    classifiers: List[str],
    X_test: np.ndarray,
    y_test: np.ndarray,
    baseline_dir: Path = Path("models"),
    optimized_dir: Path = Path("models/optimized")
) -> Dict[str, Any]:
    """Generate comprehensive baseline vs optimized comparison report.

    Args:
        classifiers: List of classifier names to compare
        X_test: Test features
        y_test: Test labels
        baseline_dir: Directory with baseline models
        optimized_dir: Directory with optimized models

    Returns:
        Structured report dict with all comparisons

    Example:
        >>> report = generate_comparison_report(
        ...     ["rf", "svm", "mlp"], X_test, y_test
        ... )
        >>> print(f"Average improvement: {report['summary']['avg_improvement']:.2%}")
    """
    results = {
        "classifiers": {},
        "ensembles": {},
        "summary": {}
    }

    # Compare individual classifiers
    f1_improvements = []

    for clf_name in classifiers:
        try:
            # Load baseline
            baseline_path = baseline_dir / f"{clf_name}_pipeline.joblib"
            baseline_model = _load_model_artifact(baseline_path)

            # Load optimized
            optimized_path = optimized_dir / f"{clf_name}_optimized.joblib"
            optimized_model = _load_model_artifact(optimized_path)

            # Compare
            comparison = compare_versions(
                clf_name, baseline_model, optimized_model, X_test, y_test
            )

            results["classifiers"][clf_name] = comparison
            f1_improvements.append(comparison["improvement"]["f1_abs"])

            logger.info(
                f"{clf_name}: F1 {comparison['baseline']['f1']:.4f} → "
                f"{comparison['optimized']['f1']:.4f} "
                f"({comparison['improvement']['f1_pct']:+.2f}%)"
            )

        except FileNotFoundError as e:
            logger.warning(f"Skipping {clf_name}: {e}")
        except Exception as e:
            logger.error(f"Error comparing {clf_name}: {e}")

    # Compare ensembles
    try:
        # Baseline soft voting
        soft_voting_path = baseline_dir / "ensemble" / "voting_soft.joblib"
        soft_voting = _load_model_artifact(soft_voting_path)

        y_pred_soft = soft_voting.predict(X_test)
        y_proba_soft = soft_voting.predict_proba(X_test)[:, 1]

        results["ensembles"]["soft_voting"] = {
            "accuracy": accuracy_score(y_test, y_pred_soft),
            "f1": f1_score(y_test, y_pred_soft),
            "precision": precision_score(y_test, y_pred_soft),
            "recall": recall_score(y_test, y_pred_soft),
            "auc_roc": roc_auc_score(y_test, y_proba_soft)
        }

        # Optimized weighted voting
        weighted_voting_path = optimized_dir / "ensemble" / "weighted_voting.joblib"
        weighted_voting = _load_model_artifact(weighted_voting_path)

        y_pred_weighted = weighted_voting.predict(X_test)
        y_proba_weighted = weighted_voting.predict_proba(X_test)[:, 1]

        results["ensembles"]["weighted_voting"] = {
            "accuracy": accuracy_score(y_test, y_pred_weighted),
            "f1": f1_score(y_test, y_pred_weighted),
            "precision": precision_score(y_test, y_pred_weighted),
            "recall": recall_score(y_test, y_pred_weighted),
            "auc_roc": roc_auc_score(y_test, y_proba_weighted)
        }

        # Calculate ensemble improvement
        soft_f1 = results["ensembles"]["soft_voting"]["f1"]
        weighted_f1 = results["ensembles"]["weighted_voting"]["f1"]

        results["ensembles"]["improvement"] = {
            "f1_abs": weighted_f1 - soft_f1,
            "f1_pct": (weighted_f1 - soft_f1) / soft_f1 * 100 if soft_f1 > 0 else 0.0
        }

        logger.info(
            f"Ensemble: F1 {soft_f1:.4f} → {weighted_f1:.4f} "
            f"({results['ensembles']['improvement']['f1_pct']:+.2f}%)"
        )

    except FileNotFoundError as e:
        logger.warning(f"Skipping ensemble comparison: {e}")
    except Exception as e:
        logger.error(f"Error comparing ensembles: {e}")

    # Calculate summary statistics
    if f1_improvements:
        avg_improvement = np.mean(f1_improvements)
        best_idx = np.argmax([abs(x) for x in f1_improvements])
        best_classifier = classifiers[best_idx]

        results["summary"] = {
            "avg_improvement": avg_improvement,
            "best_classifier": best_classifier,
            "best_improvement": f1_improvements[best_idx],
            "ensemble_improvement": results["ensembles"].get("improvement", {}).get("f1_abs", 0.0)
        }

        logger.info(
            f"Summary: avg_improvement={avg_improvement:.4f}, "
            f"best={best_classifier} ({f1_improvements[best_idx]:+.4f})"
        )

    return results


def set_active_version(classifier_name: str, version_tag: str, model_path: Optional[Path] = None) -> None:
    """Set active model version for a classifier.

    Updates cache/active_models.json with the selected version.
    This config is read by get_active_model() to determine which model to load.

    Args:
        classifier_name: Classifier name (rf, svm, ensemble, etc.)
        version_tag: Version to activate ("baseline", "ga_optimized", "weighted")
        model_path: Path to model file (auto-determined if None)

    Example:
        >>> set_active_version("rf", "ga_optimized")
        >>> set_active_version("ensemble", "weighted")
    """
    config_path = Path("cache/active_models.json")
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config or create new
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    else:
        config = {}

    # Auto-determine model path if not provided
    if model_path is None:
        if version_tag == "baseline":
            model_path = Path(f"models/{classifier_name}_pipeline.joblib")
        elif version_tag == "ga_optimized":
            model_path = Path(f"models/optimized/{classifier_name}_optimized.joblib")
        elif version_tag == "weighted" and classifier_name == "ensemble":
            model_path = Path("models/optimized/ensemble/weighted_voting.joblib")
        elif version_tag == "soft" and classifier_name == "ensemble":
            model_path = Path("models/ensemble/voting_soft.joblib")
        else:
            raise ValueError(f"Cannot auto-determine path for {classifier_name}/{version_tag}")

    # Update config
    config[classifier_name] = {
        "version": version_tag,
        "path": str(model_path)
    }

    # Save config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    logger.info(f"Set active version for {classifier_name}: {version_tag} ({model_path})")


def get_active_model(classifier_name: str) -> Any:
    """Load active model version for a classifier.

    Reads cache/active_models.json to determine which model version to load.
    Defaults to ga_optimized if available, else baseline.

    Args:
        classifier_name: Classifier name (rf, svm, ensemble, etc.)

    Returns:
        Loaded sklearn Pipeline or VotingClassifier

    Raises:
        FileNotFoundError: If neither active config nor default models exist

    Example:
        >>> model = get_active_model("rf")  # Loads GA-optimized RF
        >>> ensemble = get_active_model("ensemble")  # Loads weighted voting
    """
    config_path = Path("cache/active_models.json")

    # Try to load from active config
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)

        if classifier_name in config:
            model_path = Path(config[classifier_name]["path"])
            version = config[classifier_name]["version"]

            if not model_path.exists():
                logger.warning(
                    f"Active model path not found: {model_path}. "
                    f"Falling back to default."
                )
            else:
                model = _load_model_artifact(model_path)
                logger.info(f"Loaded active model for {classifier_name}: {version}")
                return model

    # Fallback: try optimized, then baseline
    fallback_paths = [
        Path(f"models/optimized/{classifier_name}_optimized.joblib"),
        Path(f"models/{classifier_name}_pipeline.joblib")
    ]

    # Special handling for ensemble
    if classifier_name == "ensemble":
        fallback_paths = [
            Path("models/optimized/ensemble/weighted_voting.joblib"),
            Path("models/ensemble/voting_soft.joblib")
        ]

    for fallback_path in fallback_paths:
        if fallback_path.exists():
            model = _load_model_artifact(fallback_path)
            logger.info(f"Loaded fallback model for {classifier_name}: {fallback_path}")
            return model

    raise FileNotFoundError(
        f"No active or fallback model found for {classifier_name}. "
        f"Tried: {[str(p) for p in fallback_paths]}"
    )


def _load_model_artifact(model_path: Path) -> Any:
    """Load model from joblib file, handling both wrapped and direct formats.

    Args:
        model_path: Path to model file

    Returns:
        Unwrapped model (sklearn Pipeline or VotingClassifier)
    """
    artifact = joblib.load(model_path)

    # Handle dict-wrapped format (from save_optimized_model)
    if isinstance(artifact, dict) and "model" in artifact:
        return artifact["model"]

    # Handle direct Pipeline format
    return artifact
