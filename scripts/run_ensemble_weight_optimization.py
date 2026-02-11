#!/usr/bin/env python3
"""CLI script for ensemble weight optimization using genetic algorithm.

This script:
1. Loads all 7 optimized classifiers from Plan 04-02
2. Loads training data
3. Evaluates baseline equal-weight soft voting
4. Runs GA weight optimization
5. Compares optimized vs equal weights
6. Saves optimized weights and weighted ensemble
7. Logs results to MLflow

Expected outcome:
- Higher weights for accurate classifiers (RF, SVM, MLP, XGBoost)
- Lower weights for less accurate classifiers (NB)
- 1-3% F1 improvement over equal-weight voting
"""

import argparse
import logging
from datetime import datetime
from pathlib import Path

import joblib
import mlflow
import numpy as np
from sklearn.model_selection import cross_val_score

from src.optimization.ensemble_weights import (
    create_weighted_ensemble,
    normalize_weights,
    run_weight_optimization,
    setup_weight_optimization_toolbox
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_optimized_classifiers() -> dict:
    """Load all 7 optimized classifiers from Plan 04-02.

    Returns:
        Dict mapping classifier name to fitted Pipeline

    Raises:
        FileNotFoundError: If any optimized model is missing
    """
    models_dir = Path('models/optimized')
    classifier_names = ['rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt']

    classifiers = {}

    for name in classifier_names:
        model_path = models_dir / f'{name}_optimized.joblib'

        if not model_path.exists():
            raise FileNotFoundError(
                f"Optimized model not found: {model_path}\n"
                f"Run Plan 04-02 first to create optimized classifiers."
            )

        # Load model
        clf_data = joblib.load(model_path)

        # Handle both dict format and direct Pipeline format
        if isinstance(clf_data, dict) and 'model' in clf_data:
            clf = clf_data['model']
        else:
            clf = clf_data

        classifiers[name] = clf
        logger.info(f"Loaded {name}_optimized.joblib")

    return classifiers


def evaluate_equal_weight_voting(classifiers: dict, X_train: np.ndarray, y_train: np.ndarray) -> float:
    """Evaluate baseline soft voting with equal weights (1/7 each).

    Args:
        classifiers: Dict of classifier name to Pipeline
        X_train: Training features
        y_train: Training labels

    Returns:
        Mean F1-score from 5-fold CV
    """
    from sklearn.ensemble import VotingClassifier

    logger.info("Evaluating equal-weight soft voting baseline...")

    estimators = [(name, clf) for name, clf in classifiers.items()]

    # Equal weights (1/7 = 0.1429 each)
    ensemble = VotingClassifier(
        estimators=estimators,
        voting='soft',
        weights=None,  # None = equal weights
        n_jobs=1
    )

    # 5-fold CV
    cv_scores = cross_val_score(
        ensemble, X_train, y_train,
        cv=5,
        scoring='f1',
        n_jobs=1
    )

    f1_mean = cv_scores.mean()
    logger.info(f"Equal-weight F1: {f1_mean:.4f} (±{cv_scores.std():.4f})")

    return f1_mean


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Run ensemble weight optimization')
    parser.add_argument('--generations', type=int, default=20, help='Number of GA generations')
    parser.add_argument('--population', type=int, default=30, help='Population size')
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("ENSEMBLE WEIGHT OPTIMIZATION")
    logger.info("=" * 60)

    # 1. Load optimized classifiers
    logger.info("\n[1/7] Loading optimized classifiers...")
    classifiers = load_optimized_classifiers()
    logger.info(f"Loaded {len(classifiers)} optimized classifiers")

    # 2. Load training data
    logger.info("\n[2/7] Loading training data...")
    data_path = Path('cache/url_training_data.joblib')

    if not data_path.exists():
        raise FileNotFoundError(
            f"Training data not found: {data_path}\n"
            f"Run scripts/retrain_with_urls.py first."
        )

    data = joblib.load(data_path)
    X_train = data['X_train']
    y_train = data['y_train']

    logger.info(f"Loaded training data: {X_train.shape[0]} samples, {X_train.shape[1]} features")

    # 3. Baseline comparison
    logger.info("\n[3/7] Evaluating baseline (equal weights)...")
    equal_weight_f1 = evaluate_equal_weight_voting(classifiers, X_train, y_train)

    # 4. Run weight optimization
    logger.info(f"\n[4/7] Running GA weight optimization (pop={args.population}, gen={args.generations})...")

    toolbox = setup_weight_optimization_toolbox(classifiers, X_train, y_train)
    best_weights_list, logbook = run_weight_optimization(
        toolbox,
        population_size=args.population,
        n_generations=args.generations
    )

    # Convert to dict
    classifier_names = ['rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt']
    best_weights = {name: weight for name, weight in zip(classifier_names, best_weights_list)}

    # 5. Results analysis
    logger.info("\n[5/7] Analyzing results...")

    optimized_weight_f1 = logbook[-1]['max']  # Best fitness from final generation
    improvement = optimized_weight_f1 - equal_weight_f1

    logger.info("\nOptimized weights:")
    for clf, weight in best_weights.items():
        logger.info(f"  {clf:4s}: {weight:.3f}")

    logger.info(f"\nEqual-weight F1:    {equal_weight_f1:.4f}")
    logger.info(f"Optimized F1:       {optimized_weight_f1:.4f}")
    logger.info(f"Improvement:        {improvement:+.4f} ({improvement/equal_weight_f1*100:+.2f}%)")

    # Analyze weight distribution
    sorted_weights = sorted(best_weights.items(), key=lambda x: x[1], reverse=True)
    logger.info("\nWeight ranking:")
    for i, (clf, weight) in enumerate(sorted_weights, 1):
        logger.info(f"  {i}. {clf:4s}: {weight:.3f}")

    # 6. Save results
    logger.info("\n[6/7] Saving results...")

    # Create cache dir if needed
    cache_dir = Path('cache')
    cache_dir.mkdir(exist_ok=True)

    # Save weights and metrics
    results = {
        'weights': best_weights,
        'equal_weight_f1': float(equal_weight_f1),
        'optimized_weight_f1': float(optimized_weight_f1),
        'improvement': float(improvement),
        'logbook': logbook,
        'timestamp': datetime.utcnow().isoformat(),
        'parameters': {
            'population_size': args.population,
            'n_generations': args.generations
        }
    }

    results_path = Path('cache/ensemble_weights.joblib')
    joblib.dump(results, results_path, compress=3)
    logger.info(f"Saved weights to: {results_path}")

    # Create and save weighted ensemble
    logger.info("Creating weighted voting ensemble...")

    classifier_paths = {
        name: Path(f'models/optimized/{name}_optimized.joblib')
        for name in classifier_names
    }

    ensemble = create_weighted_ensemble(best_weights, classifier_paths)

    # Fit on full training data
    ensemble.fit(X_train, y_train)

    # Save ensemble
    ensemble_dir = Path('models/optimized/ensemble')
    ensemble_dir.mkdir(parents=True, exist_ok=True)

    ensemble_path = ensemble_dir / 'weighted_voting.joblib'

    ensemble_data = {
        'model': ensemble,
        'metadata': {
            'model_type': 'weighted_voting',
            'weights': best_weights,
            'f1_score': float(optimized_weight_f1),
            'improvement_over_equal': float(improvement),
            'created_at': datetime.utcnow().isoformat()
        }
    }

    joblib.dump(ensemble_data, ensemble_path, compress=3, protocol=5)
    logger.info(f"Saved weighted ensemble to: {ensemble_path}")

    # 7. Log to MLflow
    logger.info("\n[7/7] Logging to MLflow...")

    mlflow.set_experiment("phase_4_ensemble_weights")

    with mlflow.start_run(run_name=f"weight_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
        # Log parameters
        mlflow.log_param("population_size", args.population)
        mlflow.log_param("n_generations", args.generations)

        # Log weights
        for clf, weight in best_weights.items():
            mlflow.log_metric(f"weight_{clf}", weight)

        # Log metrics
        mlflow.log_metric("equal_weight_f1", equal_weight_f1)
        mlflow.log_metric("optimized_weight_f1", optimized_weight_f1)
        mlflow.log_metric("improvement", improvement)
        mlflow.log_metric("improvement_percent", improvement / equal_weight_f1 * 100)

        # Log fitness history
        for gen_idx, record in enumerate(logbook):
            mlflow.log_metric("fitness_avg", record['avg'], step=gen_idx)
            mlflow.log_metric("fitness_max", record['max'], step=gen_idx)
            mlflow.log_metric("fitness_min", record['min'], step=gen_idx)

        logger.info("MLflow logging complete")

    logger.info("\n" + "=" * 60)
    logger.info("ENSEMBLE WEIGHT OPTIMIZATION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"\nOptimized weights saved to: {results_path}")
    logger.info(f"Weighted ensemble saved to: {ensemble_path}")
    logger.info(f"\nF1 improvement: {improvement:+.4f} ({improvement/equal_weight_f1*100:+.2f}%)")


if __name__ == '__main__':
    main()
