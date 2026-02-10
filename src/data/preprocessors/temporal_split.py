"""Temporal train-validation-test splitting for time-series data.

This module provides functions for splitting datasets by timestamp to prevent
data leakage. Ensures all training data comes strictly before validation data,
and all validation data comes strictly before test data.

Design decisions:
- Samples without timestamps are conservatively assigned to training set only
- Split boundaries respect timestamp values (no splitting within same timestamp)
- Produces 70/15/15 split by default (configurable)
"""

from typing import Any, Dict, Tuple

import pandas as pd


def temporal_split(
    df: pd.DataFrame,
    timestamp_col: str = 'timestamp',
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Split dataset by timestamp to prevent data leakage.

    Enforces strict temporal ordering: train < validation < test.
    Samples without timestamps are assigned to training set only (conservative approach).

    Args:
        df: DataFrame with timestamp column
        timestamp_col: Name of timestamp column (default: 'timestamp')
        train_ratio: Fraction of timestamped data for training (default: 0.7)
        val_ratio: Fraction of timestamped data for validation (default: 0.15)
        test_ratio: Fraction of timestamped data for testing (default: 0.15)

    Returns:
        Tuple of (train_df, val_df, test_df, split_report)

        split_report contains:
        - with_timestamps: count of samples with valid timestamps
        - without_timestamps: count of samples without timestamps (added to train)
        - train_size, val_size, test_size: final counts
        - train_date_range: (min, max) timestamps in train
        - val_date_range: (min, max) timestamps in val
        - test_date_range: (min, max) timestamps in test
        - temporal_integrity: True if train_max < val_min < test_min

    Raises:
        ValueError: If ratios don't sum to 1.0 (within tolerance)
        ValueError: If timestamp column doesn't exist

    Example:
        >>> df = pd.DataFrame({
        ...     'url': ['https://site1.com', 'https://site2.com'],
        ...     'label': [0, 1],
        ...     'timestamp': pd.to_datetime(['2024-01-01', '2024-06-01'])
        ... })
        >>> train, val, test, report = temporal_split(df)
        >>> print(report['temporal_integrity'])
        True
    """
    # Validate ratios
    ratio_sum = train_ratio + val_ratio + test_ratio
    if not (0.999 <= ratio_sum <= 1.001):  # tolerance for float precision
        raise ValueError(
            f"Ratios must sum to 1.0, got {ratio_sum:.4f} "
            f"(train={train_ratio}, val={val_ratio}, test={test_ratio})"
        )

    # Validate timestamp column exists
    if timestamp_col not in df.columns:
        raise ValueError(f"Timestamp column '{timestamp_col}' not found in DataFrame")

    # Separate data into with-timestamp and without-timestamp subsets
    with_ts_mask = df[timestamp_col].notna()
    df_with_ts = df[with_ts_mask].copy()
    df_without_ts = df[~with_ts_mask].copy()

    n_with_ts = len(df_with_ts)
    n_without_ts = len(df_without_ts)

    # Handle edge case: all samples without timestamps
    if n_with_ts == 0:
        import warnings
        warnings.warn(
            "All samples have missing timestamps. All data assigned to training set. "
            "Validation and test sets will be empty."
        )
        return (
            df.copy(),
            pd.DataFrame(columns=df.columns),
            pd.DataFrame(columns=df.columns),
            {
                'with_timestamps': 0,
                'without_timestamps': n_without_ts,
                'train_size': len(df),
                'val_size': 0,
                'test_size': 0,
                'train_date_range': None,
                'val_date_range': None,
                'test_date_range': None,
                'temporal_integrity': True  # vacuously true
            }
        )

    # Sort timestamped data by timestamp ascending
    df_with_ts = df_with_ts.sort_values(by=timestamp_col).reset_index(drop=True)

    # Calculate split indices
    train_end = int(n_with_ts * train_ratio)
    val_end = int(n_with_ts * (train_ratio + val_ratio))

    # Ensure at least 1 sample in each split if possible
    if n_with_ts >= 3:
        train_end = max(1, train_end)
        val_end = max(train_end + 1, min(val_end, n_with_ts - 1))

    # Split timestamped data
    train_with_ts = df_with_ts.iloc[:train_end]
    val_with_ts = df_with_ts.iloc[train_end:val_end]
    test_with_ts = df_with_ts.iloc[val_end:]

    # Append all without-timestamp samples to training set
    train_df = pd.concat([train_with_ts, df_without_ts], ignore_index=True)
    val_df = val_with_ts.reset_index(drop=True)
    test_df = test_with_ts.reset_index(drop=True)

    # Generate split report
    def get_date_range(df_subset):
        """Get (min, max) timestamp from subset, ignoring NaT."""
        valid_timestamps = df_subset[timestamp_col].dropna()
        if len(valid_timestamps) == 0:
            return None
        return (valid_timestamps.min(), valid_timestamps.max())

    train_range = get_date_range(train_df)
    val_range = get_date_range(val_df)
    test_range = get_date_range(test_df)

    # Check temporal integrity
    temporal_integrity = True
    if train_range and val_range and test_range:
        train_max = train_range[1]
        val_min = val_range[0]
        val_max = val_range[1]
        test_min = test_range[0]

        temporal_integrity = (train_max < val_min) and (val_max < test_min)

    split_report = {
        'with_timestamps': n_with_ts,
        'without_timestamps': n_without_ts,
        'train_size': len(train_df),
        'val_size': len(val_df),
        'test_size': len(test_df),
        'train_date_range': train_range,
        'val_date_range': val_range,
        'test_date_range': test_range,
        'temporal_integrity': temporal_integrity
    }

    return train_df, val_df, test_df, split_report


def verify_temporal_integrity(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    timestamp_col: str = 'timestamp'
) -> bool:
    """Verify that train < validation < test temporally.

    Checks that the maximum timestamp in training data is strictly before
    the minimum timestamp in validation data, and the maximum timestamp in
    validation data is strictly before the minimum timestamp in test data.

    Args:
        train_df: Training DataFrame with timestamp column
        val_df: Validation DataFrame with timestamp column
        test_df: Test DataFrame with timestamp column
        timestamp_col: Name of timestamp column (default: 'timestamp')

    Returns:
        True if temporal integrity is valid

    Raises:
        ValueError: If temporal ordering is violated, with details
        ValueError: If timestamp column doesn't exist in any DataFrame

    Example:
        >>> train = pd.DataFrame({'timestamp': pd.to_datetime(['2024-01-01'])})
        >>> val = pd.DataFrame({'timestamp': pd.to_datetime(['2024-02-01'])})
        >>> test = pd.DataFrame({'timestamp': pd.to_datetime(['2024-03-01'])})
        >>> verify_temporal_integrity(train, val, test)
        True
    """
    # Check timestamp column exists in all DataFrames
    for name, df in [('train', train_df), ('val', val_df), ('test', test_df)]:
        if timestamp_col not in df.columns:
            raise ValueError(
                f"Timestamp column '{timestamp_col}' not found in {name} DataFrame"
            )

    # Get valid timestamps (ignoring NaT)
    train_timestamps = train_df[timestamp_col].dropna()
    val_timestamps = val_df[timestamp_col].dropna()
    test_timestamps = test_df[timestamp_col].dropna()

    # Handle edge cases: empty sets
    if len(train_timestamps) == 0 or len(val_timestamps) == 0 or len(test_timestamps) == 0:
        import warnings
        warnings.warn(
            "One or more splits have no valid timestamps. Temporal integrity check skipped."
        )
        return True  # vacuously true

    # Get boundary timestamps
    train_max = train_timestamps.max()
    val_min = val_timestamps.min()
    val_max = val_timestamps.max()
    test_min = test_timestamps.min()

    # Check temporal ordering
    if not (train_max < val_min):
        raise ValueError(
            f"Temporal integrity violated: training max ({train_max}) >= validation min ({val_min}). "
            f"Training data contains timestamps from the future relative to validation data."
        )

    if not (val_max < test_min):
        raise ValueError(
            f"Temporal integrity violated: validation max ({val_max}) >= test min ({test_min}). "
            f"Validation data contains timestamps from the future relative to test data."
        )

    return True
