"""Dataset caching utilities for reproducible experiments.

This module provides functions for caching processed datasets using joblib,
including metadata tracking for cache freshness and provenance.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
from joblib import dump, load

logger = logging.getLogger(__name__)


def cache_dataset(
    df: pd.DataFrame,
    cache_path: Path,
    description: str = "",
    metadata: Dict[str, Any] = None
) -> None:
    """Cache a DataFrame with metadata using joblib compression.

    Saves the DataFrame along with metadata including timestamp, shape,
    columns, and custom metadata for reproducibility and provenance tracking.

    Args:
        df: DataFrame to cache
        cache_path: Path where cache file will be saved
        description: Human-readable description of the cached dataset
        metadata: Additional metadata dictionary to store with the dataset

    Example:
        >>> cache_dataset(
        ...     df=train_data,
        ...     cache_path=CACHE_DIR / 'train.joblib',
        ...     description='Training data with SMOTE balancing',
        ...     metadata={'balance_ratio': 0.5, 'split': 'train'}
        ... )
    """
    # Ensure cache directory exists
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Build cache object with metadata
    cache_obj = {
        'data': df,
        'timestamp': pd.Timestamp.now(),
        'description': description,
        'shape': df.shape,
        'columns': list(df.columns),
        'metadata': metadata or {}
    }

    # Save with compression
    dump(cache_obj, cache_path, compress=3)

    logger.info(
        f"Cached dataset to {cache_path}: {df.shape[0]} rows, "
        f"{df.shape[1]} columns"
    )


def load_cached_dataset(cache_path: Path) -> Optional[pd.DataFrame]:
    """Load a cached DataFrame from disk.

    Returns None if cache doesn't exist. Logs information about the loaded
    cache including creation timestamp and shape.

    Args:
        cache_path: Path to cached dataset file

    Returns:
        DataFrame if cache exists, None otherwise

    Example:
        >>> df = load_cached_dataset(CACHE_DIR / 'train.joblib')
        >>> if df is not None:
        ...     print(f"Loaded {len(df)} samples")
    """
    if not cache_path.exists():
        logger.debug(f"Cache not found: {cache_path}")
        return None

    try:
        cache_obj = load(cache_path)
        df = cache_obj['data']

        logger.info(
            f"Loaded cached dataset from {cache_path}: "
            f"{df.shape[0]} rows, {df.shape[1]} columns "
            f"(created: {cache_obj['timestamp']})"
        )

        return df

    except Exception as e:
        logger.error(f"Failed to load cache from {cache_path}: {e}")
        return None


def get_cache_info(cache_path: Path) -> Optional[Dict[str, Any]]:
    """Get cache metadata without loading the full dataset.

    Useful for checking cache freshness and provenance without the overhead
    of loading large DataFrames.

    Args:
        cache_path: Path to cached dataset file

    Returns:
        Dictionary with metadata (timestamp, description, shape, columns, metadata)
        or None if cache doesn't exist

    Example:
        >>> info = get_cache_info(CACHE_DIR / 'train.joblib')
        >>> if info and (pd.Timestamp.now() - info['timestamp']).days < 7:
        ...     print("Cache is fresh")
    """
    if not cache_path.exists():
        return None

    try:
        cache_obj = load(cache_path)
        # Return everything except the data itself
        return {
            'timestamp': cache_obj['timestamp'],
            'description': cache_obj['description'],
            'shape': cache_obj['shape'],
            'columns': cache_obj['columns'],
            'metadata': cache_obj.get('metadata', {})
        }

    except Exception as e:
        logger.error(f"Failed to read cache info from {cache_path}: {e}")
        return None
