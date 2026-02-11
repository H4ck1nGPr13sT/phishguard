#!/usr/bin/env python3
"""Compare baseline vs GA-optimized models.

This script generates a comprehensive comparison report showing:
- Individual classifier improvements (baseline vs optimized)
- Ensemble improvements (soft voting vs weighted voting)
- Summary statistics (average improvement, best classifier)

Results are saved to cache/model_comparison.joblib and logged to MLflow.
Active models are set to optimized versions if improvement > 0.

Usage:
    python scripts/compare_models.py [--output table|json|csv] [--metrics f1,accuracy]
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List

import joblib
import mlflow
import pandas as pd

from src.optimization.model_registry import (
    generate_comparison_report,
    register_model,
    set_active_version,
)
from src.optimization.mlflow_tracker import setup_experiment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_table_report(results: Dict) -> None:
    """Print comparison results as formatted table.

    Args:
        results: Comparison report dict from generate_comparison_report()
    """
    print("\n" + "=" * 80)
    print("BASELINE VS GA-OPTIMIZED MODEL COMPARISON")
    print("=" * 80)

    # Individual classifiers
    if results["classifiers"]:
        print("\nIndividual Classifiers:")
        print("-" * 80)
        print(f"{'Classifier':<12} {'Baseline F1':>12} {'Optimized F1':>13} {'Improvement':>13}")
        print("-" * 80)

        for clf_name, data in results["classifiers"].items():
            baseline_f1 = data["baseline"]["f1"]
            optimized_f1 = data["optimized"]["f1"]
            improvement_pct = data["improvement"]["f1_pct"]

            print(
                f"{clf_name:<12} {baseline_f1:>12.4f} {optimized_f1:>13.4f} "
                f"{improvement_pct:>+12.2f}%"
            )

    # Ensembles
    if "soft_voting" in results["ensembles"] and "weighted_voting" in results["ensembles"]:
        print("\nEnsembles:")
        print("-" * 80)
        print(f"{'Type':<12} {'F1 Score':>12} {'Improvement':>13}")
        print("-" * 80)

        soft_f1 = results["ensembles"]["soft_voting"]["f1"]
        weighted_f1 = results["ensembles"]["weighted_voting"]["f1"]
        improvement_pct = results["ensembles"]["improvement"]["f1_pct"]

        print(f"{'Soft Vote':<12} {soft_f1:>12.4f} {'(baseline)':>13}")
        print(f"{'Weighted':<12} {weighted_f1:>12.4f} {improvement_pct:>+12.2f}%")

    # Summary statistics
    if results["summary"]:
        print("\nOverall Statistics:")
        print("-" * 80)

        avg_improvement = results["summary"]["avg_improvement"] * 100
        best_classifier = results["summary"]["best_classifier"]
        best_improvement = results["summary"]["best_improvement"] * 100
        ensemble_improvement = results["summary"]["ensemble_improvement"] * 100

        print(f"  Average classifier improvement: {avg_improvement:+.2f}%")
        print(f"  Best improving classifier: {best_classifier} ({best_improvement:+.2f}%)")
        print(f"  Ensemble improvement: {ensemble_improvement:+.2f}%")

    print("=" * 80 + "\n")


def print_json_report(results: Dict) -> None:
    """Print comparison results as JSON.

    Args:
        results: Comparison report dict from generate_comparison_report()
    """
    print(json.dumps(results, indent=2))


def print_csv_report(results: Dict) -> None:
    """Print comparison results as CSV.

    Args:
        results: Comparison report dict from generate_comparison_report()
    """
    # Build CSV rows
    rows = []

    for clf_name, data in results["classifiers"].items():
        rows.append({
            "model": clf_name,
            "type": "classifier",
            "baseline_f1": data["baseline"]["f1"],
            "optimized_f1": data["optimized"]["f1"],
            "improvement_pct": data["improvement"]["f1_pct"]
        })

    if "soft_voting" in results["ensembles"]:
        rows.append({
            "model": "soft_voting",
            "type": "ensemble",
            "baseline_f1": results["ensembles"]["soft_voting"]["f1"],
            "optimized_f1": None,
            "improvement_pct": None
        })

    if "weighted_voting" in results["ensembles"]:
        rows.append({
            "model": "weighted_voting",
            "type": "ensemble",
            "baseline_f1": None,
            "optimized_f1": results["ensembles"]["weighted_voting"]["f1"],
            "improvement_pct": results["ensembles"]["improvement"]["f1_pct"]
        })

    # Convert to DataFrame and print
    df = pd.DataFrame(rows)
    print(df.to_csv(index=False))


def set_active_models(results: Dict) -> None:
    """Set active model versions based on comparison results.

    Sets optimized version as active if improvement >= 0.
    For ensembles, always use weighted voting.

    Args:
        results: Comparison report dict
    """
    logger.info("Setting active model versions...")

    # Set classifiers to optimized if improvement >= 0
    for clf_name, data in results["classifiers"].items():
        improvement = data["improvement"]["f1_abs"]

        if improvement >= 0:
            set_active_version(clf_name, "ga_optimized")
            logger.info(f"  {clf_name}: ga_optimized (improvement: {improvement:+.4f})")
        else:
            set_active_version(clf_name, "baseline")
            logger.warning(f"  {clf_name}: baseline (regression: {improvement:+.4f})")

    # Always use weighted voting for ensemble
    if "weighted_voting" in results["ensembles"]:
        set_active_version("ensemble", "weighted")
        ensemble_improvement = results["ensembles"]["improvement"]["f1_abs"]
        logger.info(f"  ensemble: weighted (improvement: {ensemble_improvement:+.4f})")


def log_to_mlflow(results: Dict) -> None:
    """Log comparison results to MLflow.

    Args:
        results: Comparison report dict
    """
    # Setup experiment
    setup_experiment("phase_4_model_comparison")

    # Start run for comparison
    with mlflow.start_run(run_name="baseline_vs_optimized"):
        # Log summary metrics
        if results["summary"]:
            mlflow.log_metric("avg_classifier_improvement", results["summary"]["avg_improvement"])
            mlflow.log_metric("best_classifier_improvement", results["summary"]["best_improvement"])
            mlflow.log_metric("ensemble_improvement", results["summary"]["ensemble_improvement"])

            mlflow.log_param("best_classifier", results["summary"]["best_classifier"])

        # Log classifier improvements
        for clf_name, data in results["classifiers"].items():
            mlflow.log_metric(f"{clf_name}_baseline_f1", data["baseline"]["f1"])
            mlflow.log_metric(f"{clf_name}_optimized_f1", data["optimized"]["f1"])
            mlflow.log_metric(f"{clf_name}_improvement_pct", data["improvement"]["f1_pct"])

        # Log ensemble metrics
        if "soft_voting" in results["ensembles"]:
            mlflow.log_metric("soft_voting_f1", results["ensembles"]["soft_voting"]["f1"])
        if "weighted_voting" in results["ensembles"]:
            mlflow.log_metric("weighted_voting_f1", results["ensembles"]["weighted_voting"]["f1"])

        # Tag for filtering
        mlflow.set_tags({
            "phase": "04",
            "plan": "05",
            "comparison_type": "baseline_vs_optimized"
        })

        logger.info("Logged comparison results to MLflow")


def main():
    """Run model comparison."""
    parser = argparse.ArgumentParser(description="Compare baseline vs GA-optimized models")
    parser.add_argument(
        "--output",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format (default: table)"
    )
    parser.add_argument(
        "--metrics",
        default="f1,accuracy,precision,recall,auc_roc",
        help="Comma-separated list of metrics to compare (default: all)"
    )
    args = parser.parse_args()

    logger.info("Starting model comparison...")
    start_time = time.time()

    # Load test data
    data_path = Path("cache/url_training_data.joblib")
    if not data_path.exists():
        logger.error(f"Training data not found at {data_path}")
        logger.error("Run training first: python -m src.models.train")
        sys.exit(1)

    logger.info(f"Loading test data from {data_path}...")
    data = joblib.load(data_path)
    X_test = data["X_test"]
    y_test = data["y_test"]
    logger.info(f"Test set: {len(y_test)} samples")

    # Generate comparison report
    classifiers = ["rf", "svm", "mlp", "xgb", "lr", "nb", "dt"]
    logger.info(f"Comparing {len(classifiers)} classifiers...")

    results = generate_comparison_report(classifiers, X_test, y_test)

    # Add timestamp
    results["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

    # Save results
    output_path = Path("cache/model_comparison.joblib")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(results, output_path, compress=3)
    logger.info(f"Saved comparison results to {output_path}")

    # Log to MLflow
    try:
        log_to_mlflow(results)
    except Exception as e:
        logger.warning(f"Failed to log to MLflow: {e}")

    # Set active models
    set_active_models(results)

    # Print report
    if args.output == "table":
        print_table_report(results)
    elif args.output == "json":
        print_json_report(results)
    elif args.output == "csv":
        print_csv_report(results)

    # Print timing
    duration = time.time() - start_time
    logger.info(f"Comparison completed in {duration:.1f}s")


if __name__ == "__main__":
    main()
