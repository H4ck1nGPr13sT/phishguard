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
from src.models.predict import save_model, load_model
from src.models.ensemble import (
    create_voting_ensemble,
    create_stacking_ensemble,
    save_ensemble
)

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


def train_ensembles(
    trained_pipelines: Dict[str, Pipeline],
    X_train: pd.DataFrame,
    y_train: pd.Series,
    output_dir: Path
) -> Dict[str, dict]:
    """Train ensemble models using voting and stacking strategies.

    Args:
        trained_pipelines: Dict of already-trained pipelines {name: pipeline}
        X_train: Training features (numeric only)
        y_train: Training labels
        output_dir: Directory to save ensemble models (models/ensemble/)

    Returns:
        Dict mapping ensemble type to metrics dict

    Example:
        >>> ensemble_results = train_ensembles(pipelines, X_train, y_train, Path('models'))
        >>> print(ensemble_results['voting_soft']['train_accuracy'])
    """
    # Create ensemble output directory
    ensemble_dir = output_dir / 'ensemble'
    ensemble_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("Training Ensemble Models")
    logger.info("=" * 80)
    logger.info(f"Base estimators: {len(trained_pipelines)}")
    logger.info(f"Training samples: {len(X_train)}")
    logger.info(f"Output directory: {ensemble_dir}")

    # Prepare estimators list for ensemble creation
    estimators = [(name, pipeline) for name, pipeline in trained_pipelines.items()]

    results = {}

    # -------------------------------------------------------------------------
    # Train Soft Voting Ensemble
    # -------------------------------------------------------------------------
    logger.info("-" * 80)
    logger.info("Training SOFT VOTING ensemble...")
    logger.info("-" * 80)

    start_time = time.time()
    voting_soft = create_voting_ensemble(estimators, voting='soft')
    voting_soft.fit(X_train, y_train)
    train_time = time.time() - start_time

    train_accuracy = voting_soft.score(X_train, y_train)
    logger.info(f"Soft voting train accuracy: {train_accuracy:.4f}")
    logger.info(f"Training time: {train_time:.2f}s")

    # Save soft voting model
    soft_path = ensemble_dir / 'voting_soft.joblib'
    save_ensemble(
        voting_soft,
        soft_path,
        model_type='voting_soft',
        metadata={
            'train_accuracy': train_accuracy,
            'train_time': train_time,
            'n_estimators': len(estimators)
        }
    )

    results['voting_soft'] = {
        'train_accuracy': train_accuracy,
        'train_time': train_time,
        'model_path': str(soft_path)
    }

    logger.info(f"✓ Soft voting ensemble saved to {soft_path}")

    # -------------------------------------------------------------------------
    # Train Hard Voting Ensemble
    # -------------------------------------------------------------------------
    logger.info("-" * 80)
    logger.info("Training HARD VOTING ensemble...")
    logger.info("-" * 80)

    start_time = time.time()
    voting_hard = create_voting_ensemble(estimators, voting='hard')
    voting_hard.fit(X_train, y_train)
    train_time = time.time() - start_time

    train_accuracy = voting_hard.score(X_train, y_train)
    logger.info(f"Hard voting train accuracy: {train_accuracy:.4f}")
    logger.info(f"Training time: {train_time:.2f}s")

    # Save hard voting model
    hard_path = ensemble_dir / 'voting_hard.joblib'
    save_ensemble(
        voting_hard,
        hard_path,
        model_type='voting_hard',
        metadata={
            'train_accuracy': train_accuracy,
            'train_time': train_time,
            'n_estimators': len(estimators)
        }
    )

    results['voting_hard'] = {
        'train_accuracy': train_accuracy,
        'train_time': train_time,
        'model_path': str(hard_path)
    }

    logger.info(f"✓ Hard voting ensemble saved to {hard_path}")

    # -------------------------------------------------------------------------
    # Train Stacking Ensemble
    # -------------------------------------------------------------------------
    logger.info("-" * 80)
    logger.info("Training STACKING ensemble (this may take a while due to cv=5)...")
    logger.info("-" * 80)

    start_time = time.time()
    stacking = create_stacking_ensemble(estimators)
    stacking.fit(X_train, y_train)
    train_time = time.time() - start_time

    train_accuracy = stacking.score(X_train, y_train)
    logger.info(f"Stacking train accuracy: {train_accuracy:.4f}")
    logger.info(f"Training time: {train_time:.2f}s")

    # Save stacking model
    stacking_path = ensemble_dir / 'stacking.joblib'
    save_ensemble(
        stacking,
        stacking_path,
        model_type='stacking',
        metadata={
            'train_accuracy': train_accuracy,
            'train_time': train_time,
            'n_estimators': len(estimators),
            'meta_model': 'LogisticRegression',
            'cv_folds': 5
        }
    )

    results['stacking'] = {
        'train_accuracy': train_accuracy,
        'train_time': train_time,
        'model_path': str(stacking_path)
    }

    logger.info(f"✓ Stacking ensemble saved to {stacking_path}")

    logger.info("=" * 80)
    logger.info("All ensemble models trained successfully!")
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


def print_ensemble_summary(
    individual_results: Dict[str, dict],
    ensemble_results: Dict[str, dict]
) -> None:
    """Print comparison of individual classifiers vs ensembles.

    Args:
        individual_results: Results from train_all_classifiers()
        ensemble_results: Results from train_ensembles()
    """
    print("\n" + "=" * 100)
    print("ENSEMBLE VS INDIVIDUAL COMPARISON")
    print("=" * 100)
    print(f"{'Model':<25} {'Train Acc':<15} {'CV/OOB/Type':<20} {'Time (s)':<15}")
    print("-" * 100)

    # Print individual classifiers
    print("INDIVIDUAL CLASSIFIERS:")
    for name, metrics in sorted(individual_results.items()):
        train_acc = metrics['train_accuracy']
        cv_acc = metrics['cv_accuracy']
        train_time = metrics['train_time']
        print(f"  {name.upper():<23} {train_acc:<15.4f} {cv_acc:<20.4f} {train_time:<15.2f}")

    print()
    print("ENSEMBLE MODELS:")
    for name, metrics in sorted(ensemble_results.items()):
        train_acc = metrics['train_accuracy']
        train_time = metrics['train_time']
        model_type = name.replace('_', ' ').title()
        print(f"  {model_type:<23} {train_acc:<15.4f} {'(see above)':<20} {train_time:<15.2f}")

    print("=" * 100)

    # Calculate average individual accuracy
    avg_individual = sum(m['cv_accuracy'] for m in individual_results.values()) / len(individual_results)
    best_individual = max(m['cv_accuracy'] for m in individual_results.values())

    # Get ensemble accuracies
    ensemble_accs = {name: metrics['train_accuracy'] for name, metrics in ensemble_results.items()}

    print(f"\nAverage individual accuracy: {avg_individual:.4f}")
    print(f"Best individual accuracy: {best_individual:.4f}")
    print(f"Soft voting accuracy: {ensemble_accs.get('voting_soft', 0):.4f}")
    print(f"Hard voting accuracy: {ensemble_accs.get('voting_hard', 0):.4f}")
    print(f"Stacking accuracy: {ensemble_accs.get('stacking', 0):.4f}")

    # Check if ensembles beat average
    soft_beats_avg = ensemble_accs.get('voting_soft', 0) >= avg_individual
    hard_beats_avg = ensemble_accs.get('voting_hard', 0) >= avg_individual
    stacking_beats_avg = ensemble_accs.get('stacking', 0) >= avg_individual

    print(f"\nSoft voting >= avg individual: {soft_beats_avg}")
    print(f"Hard voting >= avg individual: {hard_beats_avg}")
    print(f"Stacking >= avg individual: {stacking_beats_avg}")
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

    # Train all individual classifiers
    output_dir = Path('models')
    results = train_all_classifiers(X_train_features, y_train, output_dir)

    # Print individual classifier summary
    print_summary_table(results)

    # Load existing RF pipeline from Phase 2
    logger.info("\nLoading existing Random Forest model from Phase 2...")
    rf_pipeline = load_model(output_dir / 'rf_pipeline.joblib')
    logger.info("✓ Random Forest model loaded")

    # Combine all pipelines for ensemble training
    all_pipelines = {
        'rf': rf_pipeline,  # From Phase 2
    }

    # Load newly-trained non-RF pipelines from disk
    for name in create_classifiers().keys():
        if name != 'rf':
            all_pipelines[name] = load_model(output_dir / f'{name}_pipeline.joblib')

    logger.info(f"\nPrepared {len(all_pipelines)} pipelines for ensemble training")

    # Train ensemble models
    ensemble_results = train_ensembles(all_pipelines, X_train_features, y_train, output_dir)

    # Print ensemble comparison summary
    print_ensemble_summary(results, ensemble_results)

    logger.info("Training complete! All models saved to models/ directory.")
    logger.info(f"Ensemble models: {output_dir / 'ensemble'}")


if __name__ == '__main__':
    main()
