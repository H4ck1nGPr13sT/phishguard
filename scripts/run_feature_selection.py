#!/usr/bin/env python3
"""CLI script for running GA-based feature selection.

This script runs genetic algorithm feature selection on URL training data to
identify the most important features for phishing detection. Selected features
can be used to retrain models with reduced feature sets.

Usage:
    python3 scripts/run_feature_selection.py --generations 20 --population 30
"""

import argparse
import logging
from datetime import datetime

import joblib
import mlflow
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, make_scorer
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.optimization.feature_selection import (
    get_selected_features,
    run_feature_selection,
    setup_feature_selection_toolbox,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def evaluate_baseline(X_train, y_train):
    """Evaluate baseline RF performance with all features.

    Args:
        X_train: Training features (all features)
        y_train: Training labels

    Returns:
        Mean F1-score from 5-fold CV
    """
    logger.info("Evaluating baseline (all features)...")

    model = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', RandomForestClassifier(
            n_estimators=100,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        ))
    ])

    f1_scorer = make_scorer(f1_score, average='binary')
    cv_scores = cross_val_score(
        model, X_train, y_train,
        cv=5,
        scoring=f1_scorer,
        n_jobs=1
    )

    baseline_f1 = cv_scores.mean()
    logger.info(f"Baseline F1 (all features): {baseline_f1:.4f} ± {cv_scores.std():.4f}")

    return baseline_f1


def evaluate_selected_features(X_train, y_train, selected_indices):
    """Evaluate RF performance with selected features only.

    Args:
        X_train: Training features (all features)
        y_train: Training labels
        selected_indices: List of selected feature indices

    Returns:
        Mean F1-score from 5-fold CV
    """
    logger.info(f"Evaluating selected features ({len(selected_indices)} features)...")

    X_selected = X_train[:, selected_indices]

    model = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', RandomForestClassifier(
            n_estimators=100,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        ))
    ])

    f1_scorer = make_scorer(f1_score, average='binary')
    cv_scores = cross_val_score(
        model, X_selected, y_train,
        cv=5,
        scoring=f1_scorer,
        n_jobs=1
    )

    selected_f1 = cv_scores.mean()
    logger.info(f"Selected F1: {selected_f1:.4f} ± {cv_scores.std():.4f}")

    return selected_f1


def main():
    parser = argparse.ArgumentParser(
        description='Run GA-based feature selection for phishing detection'
    )
    parser.add_argument(
        '--generations', type=int, default=20,
        help='Number of generations (default: 20)'
    )
    parser.add_argument(
        '--population', type=int, default=30,
        help='Population size (default: 30)'
    )
    parser.add_argument(
        '--min-features', type=int, default=5,
        help='Minimum features to select (default: 5)'
    )
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("GA-BASED FEATURE SELECTION")
    logger.info("=" * 80)
    logger.info(f"Generations: {args.generations}")
    logger.info(f"Population: {args.population}")
    logger.info(f"Min features: {args.min_features}")

    # Load training data
    logger.info("\nLoading training data...")
    data = joblib.load('cache/url_training_data.joblib')
    X_train = data['X_train']
    y_train = data['y_train']
    feature_names = data['feature_names']

    logger.info(f"Training samples: {X_train.shape[0]}")
    logger.info(f"Total features: {X_train.shape[1]}")
    logger.info(f"Feature names: {feature_names}")

    # Evaluate baseline (all features)
    baseline_f1 = evaluate_baseline(X_train, y_train)

    # Setup and run feature selection
    logger.info("\n" + "=" * 80)
    logger.info("RUNNING FEATURE SELECTION")
    logger.info("=" * 80)

    toolbox = setup_feature_selection_toolbox(
        X_train, y_train, min_features=args.min_features
    )
    best_individual, selected_indices, logbook = run_feature_selection(
        toolbox,
        population_size=args.population,
        n_generations=args.generations
    )

    # Extract selected features
    selected_info = get_selected_features(best_individual, feature_names)

    logger.info("\n" + "=" * 80)
    logger.info("SELECTED FEATURES")
    logger.info("=" * 80)
    logger.info(f"Selected {selected_info['n_selected']} / {len(feature_names)} features")
    logger.info(f"Feature reduction: {(1 - selected_info['n_selected'] / len(feature_names)) * 100:.1f}%")
    logger.info(f"\nSelected features:")
    for i, (idx, name) in enumerate(zip(selected_info['indices'], selected_info['names'])):
        logger.info(f"  {i+1}. [{idx}] {name}")

    # Evaluate selected features
    selected_f1 = evaluate_selected_features(X_train, y_train, selected_indices)

    # Compare performance
    logger.info("\n" + "=" * 80)
    logger.info("PERFORMANCE COMPARISON")
    logger.info("=" * 80)
    logger.info(f"Baseline F1 (all features): {baseline_f1:.4f}")
    logger.info(f"Selected F1 ({selected_info['n_selected']} features): {selected_f1:.4f}")
    improvement = selected_f1 - baseline_f1
    logger.info(f"Difference: {improvement:+.4f} ({improvement / baseline_f1 * 100:+.2f}%)")

    if improvement >= 0:
        logger.info("✓ Selected features maintain or improve performance")
    elif improvement >= -0.02:
        logger.info("✓ Selected features within acceptable performance loss (<2%)")
    else:
        logger.warning("⚠ Selected features show significant performance loss")

    # Save results
    logger.info("\n" + "=" * 80)
    logger.info("SAVING RESULTS")
    logger.info("=" * 80)

    results = {
        'selected_indices': selected_info['indices'],
        'selected_names': selected_info['names'],
        'n_original': len(feature_names),
        'n_selected': selected_info['n_selected'],
        'best_fitness': best_individual.fitness.values[0],
        'logbook': logbook,
        'baseline_f1': baseline_f1,
        'selected_f1': selected_f1,
        'improvement': improvement,
        'timestamp': datetime.now().isoformat(),
        'ga_params': {
            'population_size': args.population,
            'n_generations': args.generations,
            'min_features': args.min_features
        }
    }

    output_path = 'cache/selected_features.joblib'
    joblib.dump(results, output_path)
    logger.info(f"Saved results to: {output_path}")

    # Log to MLflow
    logger.info("\nLogging to MLflow...")
    mlflow.set_experiment("phase_4_feature_selection")

    with mlflow.start_run():
        # Log parameters
        mlflow.log_param("population_size", args.population)
        mlflow.log_param("n_generations", args.generations)
        mlflow.log_param("min_features", args.min_features)
        mlflow.log_param("n_original_features", len(feature_names))
        mlflow.log_param("n_selected_features", selected_info['n_selected'])

        # Log metrics
        mlflow.log_metric("baseline_f1", baseline_f1)
        mlflow.log_metric("selected_f1", selected_f1)
        mlflow.log_metric("improvement", improvement)
        mlflow.log_metric("best_fitness", best_individual.fitness.values[0])
        mlflow.log_metric("feature_reduction_pct",
                         (1 - selected_info['n_selected'] / len(feature_names)) * 100)

        # Log selected features as text
        mlflow.log_text(
            "\n".join(selected_info['names']),
            "selected_features.txt"
        )

        logger.info("✓ Logged to MLflow")

    logger.info("\n" + "=" * 80)
    logger.info("FEATURE SELECTION COMPLETE")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
