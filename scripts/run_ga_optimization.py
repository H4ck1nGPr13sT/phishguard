#!/usr/bin/env python3
"""Run genetic algorithm hyperparameter optimization for all classifiers.

This script orchestrates GA-based hyperparameter optimization using DEAP
framework with MLflow tracking. It:

1. Loads training data from cache/url_training_data.joblib
2. For each of 7 classifiers (rf, svm, mlp, xgb, lr, nb, dt):
   - Sets up DEAP toolbox with classifier-specific search space
   - Runs GA optimization (population=50, generations=30)
   - Logs generation fitness to MLflow
   - Saves optimized model with best hyperparameters
   - Evaluates on test set
3. Produces summary comparison: baseline vs optimized F1-scores
4. Saves results to cache/ga_optimization_results.joblib

Usage:
    # Optimize all classifiers with default settings
    python scripts/run_ga_optimization.py

    # Optimize single classifier (for testing)
    python scripts/run_ga_optimization.py --classifier rf

    # Quick test with fewer generations
    python scripts/run_ga_optimization.py --classifier rf --generations 5 --population 20

    # Override default parameters
    python scripts/run_ga_optimization.py --generations 50 --population 100

Expected runtime: ~2-3 hours for all 7 classifiers with default settings
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import joblib
import mlflow
import numpy as np
from sklearn.metrics import accuracy_score, f1_score

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.optimization.fitness import create_model_from_params
from src.optimization.ga_optimizer import run_ga_optimization, setup_toolbox
from src.optimization.mlflow_tracker import (
    log_best_individual,
    log_convergence_analysis,
    log_generation,
    save_optimized_model,
    setup_experiment,
)
from src.optimization.search_spaces import decode_individual

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_training_data():
    """Load training data from cache.

    Returns:
        Tuple of (X_train, y_train, X_test, y_test)
    """
    cache_path = Path("cache/url_training_data.joblib")

    if not cache_path.exists():
        raise FileNotFoundError(
            f"Training data not found at {cache_path}. "
            "Run scripts/retrain_with_urls.py first."
        )

    logger.info(f"Loading training data from {cache_path}")
    data = joblib.load(cache_path)

    X_train = data['X_train']
    y_train = data['y_train']
    X_test = data['X_test']
    y_test = data['y_test']

    logger.info(
        f"Loaded: X_train={X_train.shape}, y_train={y_train.shape}, "
        f"X_test={X_test.shape}, y_test={y_test.shape}"
    )

    return X_train, y_train, X_test, y_test


def optimize_classifier(
    classifier_name: str,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    population_size: int = 50,
    n_generations: int = 30,
    cxpb: float = 0.7,
    mutpb: float = 0.2,
    output_dir: Path = Path("models/optimized")
) -> dict:
    """Run GA optimization for a single classifier.

    Args:
        classifier_name: One of 'rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt'
        X_train: Training features
        y_train: Training labels
        X_test: Test features
        y_test: Test labels
        population_size: GA population size (default: 50)
        n_generations: Number of generations (default: 30)
        cxpb: Crossover probability (default: 0.7)
        mutpb: Mutation probability (default: 0.2)
        output_dir: Directory for optimized models

    Returns:
        Dictionary with optimization results:
        - best_hyperparams: Best hyperparameter dictionary
        - best_fitness: Best F1-score from CV
        - test_accuracy: Accuracy on test set
        - test_f1: F1-score on test set
        - duration: Optimization duration in seconds
        - logbook: DEAP logbook with generation history
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Optimizing {classifier_name.upper()}")
    logger.info(f"{'='*60}")

    start_time = time.time()

    # Start MLflow run for this classifier
    with mlflow.start_run(run_name=f"{classifier_name}_optimization"):
        # Setup DEAP toolbox
        logger.info(f"Setting up DEAP toolbox for {classifier_name}...")
        toolbox = setup_toolbox(classifier_name, X_train, y_train)

        # Run GA optimization
        logger.info(
            f"Running GA: population={population_size}, "
            f"generations={n_generations}, cxpb={cxpb}, mutpb={mutpb}"
        )

        best_individual, logbook, hof = run_ga_optimization(
            toolbox,
            population_size=population_size,
            n_generations=n_generations,
            cxpb=cxpb,
            mutpb=mutpb
        )

        # Log generation fitness to MLflow
        logger.info("Logging generation metrics to MLflow...")
        for gen, record in enumerate(logbook):
            mlflow.log_metrics({
                "avg_fitness": record["avg"],
                "max_fitness": record["max"],
                "min_fitness": record["min"],
                "std_fitness": record["std"]
            }, step=gen)

        # Decode best hyperparameters
        best_hyperparams = decode_individual(classifier_name, best_individual)
        best_fitness = best_individual.fitness.values[0]

        logger.info(f"Best hyperparameters: {best_hyperparams}")
        logger.info(f"Best CV F1-score: {best_fitness:.4f}")

        # Train final model with best hyperparameters
        logger.info("Training final model with best hyperparameters...")
        final_model = create_model_from_params(classifier_name, best_hyperparams)
        final_model.fit(X_train, y_train)

        # Evaluate on test set
        y_pred = final_model.predict(X_test)
        test_accuracy = accuracy_score(y_test, y_pred)
        test_f1 = f1_score(y_test, y_pred)

        logger.info(f"Test accuracy: {test_accuracy:.4f}")
        logger.info(f"Test F1-score: {test_f1:.4f}")

        # Calculate duration
        duration = time.time() - start_time
        logger.info(f"Optimization duration: {duration:.1f}s ({duration/60:.1f} min)")

        # Log to MLflow
        log_best_individual(
            classifier_name, best_individual, best_hyperparams,
            best_fitness, duration, n_generations
        )
        log_convergence_analysis(logbook)

        # Log test metrics
        mlflow.log_metrics({
            "test_accuracy": test_accuracy,
            "test_f1": test_f1
        })

        # Save optimized model
        model_path = save_optimized_model(
            classifier_name, final_model, best_hyperparams,
            best_fitness, output_dir
        )

        logger.info(f"Saved optimized model to {model_path}")

    # Return results
    return {
        "best_hyperparams": best_hyperparams,
        "best_fitness": best_fitness,
        "test_accuracy": test_accuracy,
        "test_f1": test_f1,
        "duration": duration,
        "logbook": logbook
    }


def print_summary_table(results: dict):
    """Print comparison table of baseline vs optimized models.

    Args:
        results: Dictionary mapping classifier name to optimization results
    """
    print("\n" + "="*70)
    print("OPTIMIZATION SUMMARY")
    print("="*70)
    print(f"{'Classifier':<12} {'Best CV F1':<12} {'Test F1':<12} {'Duration':<15}")
    print("-"*70)

    for name, result in results.items():
        print(
            f"{name.upper():<12} "
            f"{result['best_fitness']:.4f}       "
            f"{result['test_f1']:.4f}       "
            f"{result['duration']/60:.1f} min"
        )

    print("="*70)

    # Calculate average
    avg_cv_f1 = np.mean([r['best_fitness'] for r in results.values()])
    avg_test_f1 = np.mean([r['test_f1'] for r in results.values()])
    total_duration = sum(r['duration'] for r in results.values())

    print(f"{'AVERAGE':<12} {avg_cv_f1:.4f}       {avg_test_f1:.4f}       {total_duration/60:.1f} min")
    print("="*70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run GA hyperparameter optimization for phishing classifiers"
    )
    parser.add_argument(
        "--classifier",
        type=str,
        choices=['rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt', 'all'],
        default='all',
        help="Classifier to optimize (default: all)"
    )
    parser.add_argument(
        "--population",
        type=int,
        default=50,
        help="GA population size (default: 50)"
    )
    parser.add_argument(
        "--generations",
        type=int,
        default=30,
        help="Number of generations (default: 30)"
    )
    parser.add_argument(
        "--cxpb",
        type=float,
        default=0.7,
        help="Crossover probability (default: 0.7)"
    )
    parser.add_argument(
        "--mutpb",
        type=float,
        default=0.2,
        help="Mutation probability (default: 0.2)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="models/optimized",
        help="Output directory for optimized models (default: models/optimized)"
    )

    args = parser.parse_args()

    # Setup MLflow experiment
    setup_experiment("phase_4_ga_optimization")

    # Load training data
    X_train, y_train, X_test, y_test = load_training_data()

    # Determine classifiers to optimize
    if args.classifier == 'all':
        classifiers = ['rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt']
    else:
        classifiers = [args.classifier]

    logger.info(f"Optimizing classifiers: {classifiers}")
    logger.info(
        f"GA parameters: population={args.population}, "
        f"generations={args.generations}, cxpb={args.cxpb}, mutpb={args.mutpb}"
    )

    # Run optimization for each classifier
    results = {}
    output_dir = Path(args.output_dir)

    for classifier_name in classifiers:
        try:
            result = optimize_classifier(
                classifier_name,
                X_train, y_train,
                X_test, y_test,
                population_size=args.population,
                n_generations=args.generations,
                cxpb=args.cxpb,
                mutpb=args.mutpb,
                output_dir=output_dir
            )
            results[classifier_name] = result

        except Exception as e:
            logger.error(f"Failed to optimize {classifier_name}: {e}", exc_info=True)
            continue

    # Print summary
    if results:
        print_summary_table(results)

        # Save results to cache
        results_path = Path("cache/ga_optimization_results.joblib")
        joblib.dump(results, results_path, compress=3)
        logger.info(f"\nSaved optimization results to {results_path}")

    else:
        logger.error("No successful optimizations")
        sys.exit(1)


if __name__ == "__main__":
    main()
