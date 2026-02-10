"""End-to-end data pipeline orchestration for phishing detection.

This module provides the main pipeline that orchestrates the complete data
processing workflow: download → validate → merge → split → balance → cache.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd

from src.config.settings import CACHE_DIR, DATA_DIR, PHISHTANK_API_KEY, RANDOM_SEED, set_seeds
from src.data.downloaders import download_all_sources
from src.data.validators import validate_dataset, deduplicate_dataset
from src.data.preprocessors import (
    merge_datasets,
    temporal_split,
    verify_temporal_integrity,
    balance_training_data
)
from src.utils.cache import cache_dataset, load_cached_dataset

logger = logging.getLogger(__name__)


@dataclass
class DataPipelineConfig:
    """Configuration for data pipeline execution.

    Attributes:
        phishtank_api_key: API key for PhishTank dataset (optional)
        nazario_mbox_path: Path to Nazario mbox file (optional)
        cache_dir: Directory for caching processed datasets
        data_dir: Directory for storing raw downloaded data
        force_refresh: Force re-download and re-processing even if cache exists
        train_ratio: Proportion of data for training (default: 0.7)
        val_ratio: Proportion of data for validation (default: 0.15)
        test_ratio: Proportion of data for test (default: 0.15)
        balance_target_ratio: Target proportion of minority class (default: 0.5 = balanced)
        dedup_method: Deduplication method ('exact' or 'fuzzy')
        random_seed: Random seed for reproducibility (default: 42)
        skip_phishtank: Skip PhishTank download if no API key
        skip_nazario: Skip Nazario corpus if no mbox file
    """
    phishtank_api_key: Optional[str] = None
    nazario_mbox_path: Optional[Path] = None
    cache_dir: Path = None
    data_dir: Path = None
    force_refresh: bool = False
    train_ratio: float = 0.7
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    balance_target_ratio: float = 0.5
    dedup_method: str = 'exact'
    random_seed: int = 42
    skip_phishtank: bool = False
    skip_nazario: bool = False

    def __post_init__(self):
        """Initialize paths with defaults if not provided."""
        if self.cache_dir is None:
            self.cache_dir = CACHE_DIR
        if self.data_dir is None:
            self.data_dir = DATA_DIR
        if self.phishtank_api_key is None:
            self.phishtank_api_key = PHISHTANK_API_KEY
        if self.random_seed is None:
            self.random_seed = RANDOM_SEED


def run_pipeline(config: DataPipelineConfig = None) -> Dict[str, Any]:
    """Execute the complete data processing pipeline.

    Orchestrates the full workflow:
    1. Download datasets from multiple sources
    2. Validate and merge datasets
    3. Deduplicate entries
    4. Perform temporal split (train/val/test)
    5. Balance training data with SMOTE
    6. Cache processed datasets
    7. Generate comprehensive reports

    Args:
        config: Pipeline configuration. If None, uses default configuration.

    Returns:
        Dictionary containing:
            - 'train': Tuple of (X_train, y_train) - balanced training data
            - 'val': Tuple of (X_val, y_val) - validation data
            - 'test': Tuple of (X_test, y_test) - test data
            - 'reports': Dict with detailed reports from each stage
            - 'cache_paths': Dict with paths to cached datasets

    Raises:
        RuntimeError: If all downloads fail or validation rejects all data

    Example:
        >>> config = DataPipelineConfig(
        ...     balance_target_ratio=0.5,
        ...     random_seed=42
        ... )
        >>> results = run_pipeline(config)
        >>> X_train, y_train = results['train']
        >>> print(results['reports']['balance'])
    """
    # Initialize configuration
    if config is None:
        config = DataPipelineConfig()

    logger.info("=" * 80)
    logger.info("Starting data pipeline execution")
    logger.info("=" * 80)

    # Set random seeds for reproducibility
    set_seeds(config.random_seed)
    logger.info(f"Set random seed: {config.random_seed}")

    reports = {}

    # Check for cached data
    train_cache_path = config.cache_dir / 'train_balanced.joblib'
    val_cache_path = config.cache_dir / 'validation.joblib'
    test_cache_path = config.cache_dir / 'test.joblib'

    if not config.force_refresh and all([
        train_cache_path.exists(),
        val_cache_path.exists(),
        test_cache_path.exists()
    ]):
        logger.info("Loading cached datasets (use force_refresh=True to re-process)")

        X_train = load_cached_dataset(train_cache_path)
        X_val = load_cached_dataset(val_cache_path)
        X_test = load_cached_dataset(test_cache_path)

        if X_train is not None and X_val is not None and X_test is not None:
            # Extract labels (assuming 'label' column)
            y_train = X_train['label']
            X_train = X_train.drop(columns=['label'])

            y_val = X_val['label']
            X_val = X_val.drop(columns=['label'])

            y_test = X_test['label']
            X_test = X_test.drop(columns=['label'])

            logger.info("Successfully loaded cached datasets")
            return {
                'train': (X_train, y_train),
                'val': (X_val, y_val),
                'test': (X_test, y_test),
                'reports': {'source': 'cache'},
                'cache_paths': {
                    'train': train_cache_path,
                    'val': val_cache_path,
                    'test': test_cache_path
                }
            }

    # Stage 1: Download datasets
    logger.info("Stage 1: Downloading datasets...")

    download_results = download_all_sources(
        phishtank_api_key=config.phishtank_api_key if not config.skip_phishtank else None,
        nazario_path=config.nazario_mbox_path if not config.skip_nazario else None,
        cache_dir=config.cache_dir,
        force_refresh=config.force_refresh
    )

    reports['download'] = {
        'sources': {
            name: {
                'success': result['status'] == 'success',
                'samples': result.get('samples', 0),
                'error': result.get('error')
            }
            for name, result in download_results.items()
        },
        'total_samples': sum(
            r.get('samples', 0) for r in download_results.values()
            if r['status'] == 'success'
        )
    }

    # Check if any downloads succeeded and build dict for merger
    successful_downloads = {
        name: r['data'] for name, r in download_results.items()
        if r['status'] == 'success' and 'data' in r
    }

    if not successful_downloads:
        raise RuntimeError(
            "All dataset downloads failed. Check API keys and network connectivity.\n"
            f"Details: {reports['download']['sources']}"
        )

    logger.info(
        f"Downloaded {reports['download']['total_samples']} samples from "
        f"{len(successful_downloads)} sources"
    )

    # Stage 2: Merge datasets
    logger.info("Stage 2: Merging datasets...")

    merged_df, merge_report = merge_datasets(successful_downloads, validate=False)
    reports['merge'] = merge_report

    logger.info(
        f"Merged dataset: {merged_df.shape[0]} samples, "
        f"{merged_df.shape[1]} features"
    )

    # Stage 3: Validate data
    logger.info("Stage 3: Validating data...")

    validated_df, validation_report = validate_dataset(merged_df)
    reports['validation'] = validation_report

    if len(validated_df) == 0:
        raise RuntimeError(
            "Validation rejected all data. Check data quality and validation criteria.\n"
            f"Rejection reasons: {validation_report.get('rejected', {})}"
        )

    total_rejected = validation_report['total_samples'] - validation_report['valid_samples']
    logger.info(
        f"Validation: {len(validated_df)} samples passed, "
        f"{total_rejected} rejected"
    )

    # Stage 4: Deduplicate
    logger.info(f"Stage 4: Deduplicating ({config.dedup_method})...")

    dedup_df, duplicates_removed = deduplicate_dataset(
        validated_df,
        method=config.dedup_method
    )
    reports['deduplication'] = {
        'method': config.dedup_method,
        'duplicates_removed': duplicates_removed,
        'unique_samples': len(dedup_df)
    }

    logger.info(
        f"Deduplication: {duplicates_removed} duplicates removed, "
        f"{len(dedup_df)} unique samples remain"
    )

    # Stage 5: Temporal split
    logger.info("Stage 5: Performing temporal split...")

    train_df, val_df, test_df, split_report = temporal_split(
        dedup_df,
        train_ratio=config.train_ratio,
        val_ratio=config.val_ratio,
        test_ratio=config.test_ratio
    )
    reports['split'] = split_report

    logger.info(
        f"Split sizes - Train: {len(train_df)}, Val: {len(val_df)}, "
        f"Test: {len(test_df)}"
    )

    # Stage 6: Verify temporal integrity
    logger.info("Stage 6: Verifying temporal integrity...")

    try:
        integrity_check = verify_temporal_integrity(train_df, val_df, test_df)
        reports['split']['temporal_integrity'] = integrity_check
    except ValueError as e:
        # If verification fails, it raises ValueError
        logger.error(f"Temporal integrity check failed: {e}")
        reports['split']['temporal_integrity'] = False
        raise RuntimeError(
            f"Temporal integrity check failed. Training data contains samples "
            f"from after validation/test data. Details: {e}"
        )

    logger.info("Temporal integrity verified: no data leakage detected")

    # Stage 7: Balance training data
    logger.info("Stage 7: Balancing training data...")

    # Separate features and labels
    X_train = train_df.drop(columns=['label'])
    y_train = train_df['label']

    # SMOTE requires numeric features only - exclude metadata columns
    metadata_cols = ['url', 'content', 'timestamp', 'source']
    feature_cols = [col for col in X_train.columns if col not in metadata_cols]

    if len(feature_cols) == 0:
        raise RuntimeError(
            "No numeric features available for balancing. "
            "Dataset must contain at least one numeric feature column."
        )

    X_train_features = X_train[feature_cols]
    X_train_metadata = X_train[metadata_cols]

    X_train_balanced_features, y_train_balanced, balance_report = balance_training_data(
        X_train_features,
        y_train,
        target_ratio=config.balance_target_ratio,
        random_state=config.random_seed
    )
    reports['balance'] = balance_report

    # Reattach metadata columns to balanced features
    # Note: metadata rows will be from SMOTE-generated samples (replicated from nearest neighbors)
    X_train_balanced = X_train_balanced_features.copy()
    # For synthetic samples, metadata will be missing - use NaN
    for col in metadata_cols:
        if col in X_train_metadata.columns:
            # Map original indices to metadata
            X_train_balanced[col] = None  # Synthetic samples have no metadata

    logger.info(
        f"Balancing: {balance_report['original_counts']} -> "
        f"{balance_report['final_counts']}"
    )

    # Prepare validation and test sets (no balancing)
    X_val = val_df.drop(columns=['label'])
    y_val = val_df['label']

    X_test = test_df.drop(columns=['label'])
    y_test = test_df['label']

    # Stage 8: Cache results
    logger.info("Stage 8: Caching processed datasets...")

    # Combine features and labels for caching
    train_with_labels = X_train_balanced.copy()
    train_with_labels['label'] = y_train_balanced

    val_with_labels = X_val.copy()
    val_with_labels['label'] = y_val

    test_with_labels = X_test.copy()
    test_with_labels['label'] = y_test

    cache_dataset(
        train_with_labels,
        train_cache_path,
        description='Balanced training data with SMOTE',
        metadata={
            'split': 'train',
            'balance_ratio': config.balance_target_ratio,
            'random_seed': config.random_seed
        }
    )

    cache_dataset(
        val_with_labels,
        val_cache_path,
        description='Validation data (unbalanced)',
        metadata={'split': 'validation'}
    )

    cache_dataset(
        test_with_labels,
        test_cache_path,
        description='Test data (unbalanced)',
        metadata={'split': 'test'}
    )

    logger.info("Successfully cached all datasets")

    # Stage 9: Generate final report
    logger.info("=" * 80)
    logger.info("Pipeline execution complete")
    logger.info("=" * 80)
    logger.info(f"Training samples: {len(X_train_balanced)} (balanced)")
    logger.info(f"Validation samples: {len(X_val)}")
    logger.info(f"Test samples: {len(X_test)}")
    logger.info(f"Features: {X_train_balanced.shape[1]}")
    logger.info("=" * 80)

    return {
        'train': (X_train_balanced, y_train_balanced),
        'val': (X_val, y_val),
        'test': (X_test, y_test),
        'reports': reports,
        'cache_paths': {
            'train': train_cache_path,
            'val': val_cache_path,
            'test': test_cache_path
        }
    }


def load_cached_splits(cache_dir: Path = None) -> Dict[str, Tuple[pd.DataFrame, pd.Series]]:
    """Load previously cached train/val/test splits.

    Convenience function to quickly load cached data without re-running
    the full pipeline.

    Args:
        cache_dir: Directory containing cached datasets. If None, uses CACHE_DIR from config.

    Returns:
        Dictionary with 'train', 'val', 'test' keys, each containing (X, y) tuple

    Raises:
        FileNotFoundError: If any cache file is missing

    Example:
        >>> splits = load_cached_splits()
        >>> X_train, y_train = splits['train']
        >>> X_val, y_val = splits['val']
    """
    if cache_dir is None:
        cache_dir = CACHE_DIR

    train_cache_path = cache_dir / 'train_balanced.joblib'
    val_cache_path = cache_dir / 'validation.joblib'
    test_cache_path = cache_dir / 'test.joblib'

    # Check all files exist
    for path in [train_cache_path, val_cache_path, test_cache_path]:
        if not path.exists():
            raise FileNotFoundError(
                f"Cache file not found: {path}. Run pipeline first with run_pipeline()."
            )

    # Load datasets
    train_df = load_cached_dataset(train_cache_path)
    val_df = load_cached_dataset(val_cache_path)
    test_df = load_cached_dataset(test_cache_path)

    # Separate features and labels
    y_train = train_df['label']
    X_train = train_df.drop(columns=['label'])

    y_val = val_df['label']
    X_val = val_df.drop(columns=['label'])

    y_test = test_df['label']
    X_test = test_df.drop(columns=['label'])

    return {
        'train': (X_train, y_train),
        'val': (X_val, y_val),
        'test': (X_test, y_test)
    }
