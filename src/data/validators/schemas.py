"""Pandera validation schemas for phishing datasets.

This module provides validation schemas and functions for ensuring data quality
in phishing detection datasets from multiple sources (PhishTank, UCI ML, Nazario).
"""

import pandas as pd
import pandera as pa
from pandera import Column, DataFrameSchema, Check
from typing import Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)


def _is_valid_url_or_empty(url: pd.Series) -> pd.Series:
    """Check if URL has valid HTTP/HTTPS prefix or is empty (for feature-based data).

    Args:
        url: Series of URL strings

    Returns:
        Boolean series indicating validity
    """
    return url.str.match(r'^(https?://|$)', case=False, na=False)


# Pandera schema for phishing datasets
PhishingDataSchema = DataFrameSchema(
    columns={
        "url": Column(
            str,
            nullable=False,
            checks=[
                Check(lambda s: s.str.len() >= 0, error="URL length check failed"),
                Check(_is_valid_url_or_empty, error="URL must start with http:// or https:// or be empty")
            ],
            description="URL string (empty for feature-only datasets like UCI ML)"
        ),
        "label": Column(
            int,
            nullable=False,
            checks=[
                Check.isin([0, 1], error="Label must be 0 (legitimate) or 1 (phishing)")
            ],
            description="Binary classification label"
        ),
        "content": Column(
            str,
            nullable=True,
            description="Text content (may be None for URL-only datasets)"
        ),
        "timestamp": Column(
            pd.Timestamp,
            nullable=True,
            description="Timestamp (may be None for some sources)"
        ),
        "source": Column(
            str,
            nullable=False,
            checks=[
                Check.isin(['phishtank', 'uci_ml', 'nazario'],
                          error="Source must be one of: phishtank, uci_ml, nazario")
            ],
            description="Data source identifier"
        ),
    },
    coerce=True,  # Attempt type conversion
    strict=False,  # Allow additional columns (e.g., UCI ML features)
    description="Validation schema for phishing detection datasets"
)


def validate_dataset(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Validate phishing dataset against schema and generate detailed report.

    This function validates the input DataFrame against PhishingDataSchema,
    collecting all validation errors. Invalid rows are filtered out rather than
    causing complete failure, allowing partial data recovery.

    Args:
        df: Input DataFrame to validate

    Returns:
        Tuple of (validated_df, validation_report) where:
        - validated_df: DataFrame containing only valid rows
        - validation_report: Dict with validation statistics:
            - total_samples: Original sample count
            - valid_samples: Count after validation
            - rejected: Dict of {check_name: count} for failed checks
            - statistics: Dict with null_timestamps, sources, class_distribution

    Example:
        >>> df = pd.DataFrame({
        ...     'url': ['https://example.com', 'http://test.org'],
        ...     'label': [0, 1],
        ...     'content': ['Safe', None],
        ...     'timestamp': [pd.Timestamp('2024-01-01'), None],
        ...     'source': ['phishtank', 'uci_ml']
        ... })
        >>> valid_df, report = validate_dataset(df)
        >>> print(report['valid_samples'])
        2
    """
    total_samples = len(df)

    # Initialize report
    report: Dict[str, Any] = {
        'total_samples': total_samples,
        'valid_samples': 0,
        'rejected': {},
        'statistics': {}
    }

    try:
        # Validate with lazy=True to collect all errors
        validated_df = PhishingDataSchema.validate(df, lazy=True)

        report['valid_samples'] = len(validated_df)
        logger.info(f"Validation passed: {len(validated_df)}/{total_samples} samples valid")

    except pa.errors.SchemaErrors as e:
        # Extract validation failures
        failure_cases = e.failure_cases

        # Group failures by check name
        rejection_counts = failure_cases.groupby('check').size().to_dict()
        report['rejected'] = rejection_counts

        # Get indices of failed rows
        failed_indices = failure_cases['index'].unique()

        # Filter to valid rows only
        valid_mask = ~df.index.isin(failed_indices)
        validated_df = df[valid_mask].copy()

        report['valid_samples'] = len(validated_df)

        logger.warning(
            f"Validation filtered {len(failed_indices)} invalid rows. "
            f"Valid: {report['valid_samples']}/{total_samples}"
        )
        logger.warning(f"Rejection reasons: {rejection_counts}")

    # Generate statistics on valid data
    if len(validated_df) > 0:
        report['statistics'] = {
            'null_timestamps': validated_df['timestamp'].isna().sum(),
            'sources': validated_df['source'].value_counts().to_dict(),
            'class_distribution': validated_df['label'].value_counts().to_dict()
        }
    else:
        report['statistics'] = {
            'null_timestamps': 0,
            'sources': {},
            'class_distribution': {}
        }

    return validated_df, report
