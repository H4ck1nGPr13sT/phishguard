"""Data quality checks for phishing detection datasets.

This module provides functions for deduplication and comprehensive quality reporting.
"""

import pandas as pd
from typing import Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)


def deduplicate_dataset(df: pd.DataFrame, method: str = 'exact') -> Tuple[pd.DataFrame, int]:
    """Remove duplicate URLs from dataset.

    Args:
        df: Input DataFrame with 'url' column
        method: Deduplication method
            - 'exact': Drop exact duplicate URLs (case-sensitive)
            - 'fuzzy': Normalize URLs before deduplication
                      (lowercase, strip trailing slash, remove www.)

    Returns:
        Tuple of (deduplicated_df, removed_count) where:
        - deduplicated_df: DataFrame with duplicates removed (first occurrence kept)
        - removed_count: Number of duplicate rows removed

    Example:
        >>> df = pd.DataFrame({
        ...     'url': ['https://A.com', 'https://A.com', 'https://B.com'],
        ...     'label': [1, 1, 0]
        ... })
        >>> deduped, removed = deduplicate_dataset(df, method='exact')
        >>> print(f"Removed {removed} duplicates")
        Removed 1 duplicates
    """
    original_count = len(df)

    if method == 'fuzzy':
        # Normalize URLs for fuzzy matching
        df_normalized = df.copy()

        # Only normalize non-empty URLs
        url_mask = df_normalized['url'].str.len() > 0

        if url_mask.any():
            df_normalized.loc[url_mask, 'url'] = (
                df_normalized.loc[url_mask, 'url']
                .str.lower()
                .str.rstrip('/')
                .str.replace(r'^(https?://)(www\.)', r'\1', regex=True)
            )

        # Deduplicate on normalized URL
        deduplicated_df = df_normalized.drop_duplicates(subset=['url'], keep='first')

    else:  # method == 'exact'
        # Deduplicate on exact URL match
        deduplicated_df = df.drop_duplicates(subset=['url'], keep='first')

    removed_count = original_count - len(deduplicated_df)

    if removed_count > 0:
        logger.info(f"Removed {removed_count} duplicate URLs ({method} matching)")

    return deduplicated_df, removed_count


def check_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate comprehensive quality report for phishing dataset.

    This function analyzes the dataset without modification, reporting various
    quality metrics useful for understanding data issues.

    Args:
        df: Input DataFrame with phishing data

    Returns:
        Dict with quality metrics:
        - empty_urls: Count of empty/null URLs
        - invalid_labels: Count of labels not in [0, 1]
        - missing_timestamps: Count of null timestamps
        - duplicate_urls: Count of duplicate URL rows
        - encoding_issues: Count of rows with potential non-UTF8 characters
        - class_balance: Ratio of phishing (label=1) to total samples
        - source_distribution: Dict of source value counts

    Example:
        >>> df = pd.DataFrame({
        ...     'url': ['https://a.com', ''],
        ...     'label': [1, 0],
        ...     'timestamp': [pd.Timestamp('2024-01-01'), None],
        ...     'source': ['phishtank', 'uci_ml']
        ... })
        >>> report = check_data_quality(df)
        >>> print(report['empty_urls'])
        1
    """
    report: Dict[str, Any] = {}

    # Count empty/null URLs
    if 'url' in df.columns:
        report['empty_urls'] = df['url'].isna().sum() + (df['url'].str.len() == 0).sum()
    else:
        report['empty_urls'] = 0

    # Count invalid labels
    if 'label' in df.columns:
        report['invalid_labels'] = (~df['label'].isin([0, 1])).sum()
    else:
        report['invalid_labels'] = 0

    # Count missing timestamps
    if 'timestamp' in df.columns:
        report['missing_timestamps'] = df['timestamp'].isna().sum()
    else:
        report['missing_timestamps'] = 0

    # Count duplicate URLs (only non-empty)
    if 'url' in df.columns:
        non_empty_urls = df['url'][df['url'].str.len() > 0]
        report['duplicate_urls'] = non_empty_urls.duplicated().sum()
    else:
        report['duplicate_urls'] = 0

    # Detect encoding issues (best effort - check for non-printable characters)
    encoding_issues = 0
    for col in df.select_dtypes(include=['object']).columns:
        # Check for non-ASCII characters that might indicate encoding problems
        try:
            has_issues = df[col].astype(str).str.contains(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', regex=True, na=False)
            encoding_issues += has_issues.sum()
        except Exception:
            pass  # Skip columns that can't be checked

    report['encoding_issues'] = encoding_issues

    # Calculate class balance
    if 'label' in df.columns and len(df) > 0:
        phishing_count = (df['label'] == 1).sum()
        report['class_balance'] = phishing_count / len(df)
    else:
        report['class_balance'] = 0.0

    # Source distribution
    if 'source' in df.columns:
        report['source_distribution'] = df['source'].value_counts().to_dict()
    else:
        report['source_distribution'] = {}

    return report
