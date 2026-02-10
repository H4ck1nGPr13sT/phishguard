"""Multi-source dataset merger for phishing detection.

This module combines datasets from PhishTank, UCI ML, and Nazario corpus into
a unified format with standardized columns.
"""

import pandas as pd
from typing import Dict, Tuple, Any
import logging

logger = logging.getLogger(__name__)


def merge_datasets(
    datasets: Dict[str, pd.DataFrame],
    validate: bool = True
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Merge multiple phishing datasets into unified format.

    This function standardizes column names across different data sources,
    concatenates them, and optionally performs validation and deduplication.

    Column mapping per source:
    - PhishTank: url (from 'url'), label=1 (all phishing), timestamp (from 'verified_at'), content=None
    - UCI ML: url='' (features only), label (from 'Result' mapped 0/1), timestamp=None, keep all feature columns
    - Nazario: url (extracted), label=1 (all phishing), timestamp (from Date header), content (email body)

    Args:
        datasets: Dict mapping source_name to DataFrame (e.g., {'phishtank': df1, 'uci_ml': df2})
        validate: If True, run validation and deduplication on merged data

    Returns:
        Tuple of (merged_df, merge_report) where:
        - merged_df: Unified DataFrame with standardized columns
        - merge_report: Dict with merge statistics:
            - samples_per_source: {source: count}
            - total_before_merge: Sum of all source counts
            - total_after_validation: Count after validation (if enabled)
            - total_after_dedup: Count after deduplication (if enabled)
            - validation_report: From validate_dataset (if enabled)

    Example:
        >>> datasets = {
        ...     'phishtank': pd.DataFrame({'url': ['https://phish.com'], 'verified_at': [pd.Timestamp('2024-01-01')]}),
        ...     'uci_ml': pd.DataFrame({'Result': ['-1'], 'feature1': [0.5]})
        ... }
        >>> merged, report = merge_datasets(datasets, validate=False)
        >>> print(report['samples_per_source'])
        {'phishtank': 1, 'uci_ml': 1}
    """
    if validate:
        # Import here to avoid circular dependency
        from src.data.validators.schemas import validate_dataset
        from src.data.validators.quality import deduplicate_dataset

    standardized_dfs = []
    samples_per_source = {}

    for source_name, df in datasets.items():
        if df is None or len(df) == 0:
            logger.warning(f"Source '{source_name}' is empty, skipping")
            samples_per_source[source_name] = 0
            continue

        original_count = len(df)
        samples_per_source[source_name] = original_count

        # Create standardized DataFrame for this source
        standardized = pd.DataFrame()

        # Standardize columns based on source
        if source_name == 'phishtank':
            standardized['url'] = df['url'] if 'url' in df.columns else ''
            standardized['label'] = 1  # All PhishTank data is phishing
            standardized['content'] = None  # PhishTank doesn't provide content
            standardized['timestamp'] = df['verified_at'] if 'verified_at' in df.columns else None
            standardized['source'] = 'phishtank'

        elif source_name == 'uci_ml':
            # UCI ML has features only, no raw URLs - use empty string explicitly
            standardized['url'] = pd.Series([''] * len(df), dtype=str)

            # Map Result column: -1 (legitimate) -> 0, 1 (phishing) -> 1
            if 'Result' in df.columns:
                standardized['label'] = df['Result'].apply(lambda x: 1 if x == 1 else 0)
            else:
                logger.error(f"UCI ML dataset missing 'Result' column")
                continue

            standardized['content'] = None
            standardized['timestamp'] = None
            standardized['source'] = 'uci_ml'

            # Preserve all feature columns from UCI ML
            feature_cols = [col for col in df.columns if col != 'Result']
            for col in feature_cols:
                standardized[col] = df[col]

        elif source_name == 'nazario':
            standardized['url'] = df['url'] if 'url' in df.columns else ''
            standardized['label'] = 1  # All Nazario corpus data is phishing
            standardized['content'] = df['body'] if 'body' in df.columns else None
            standardized['timestamp'] = df['date'] if 'date' in df.columns else None
            standardized['source'] = 'nazario'

        else:
            # Generic handling for unknown sources
            logger.warning(f"Unknown source '{source_name}', using generic mapping")
            standardized['url'] = df['url'] if 'url' in df.columns else ''
            standardized['label'] = df['label'] if 'label' in df.columns else 1
            standardized['content'] = df.get('content', None)
            standardized['timestamp'] = df.get('timestamp', None)
            standardized['source'] = source_name

            # Preserve other columns
            other_cols = [col for col in df.columns if col not in ['url', 'label', 'content', 'timestamp', 'source']]
            for col in other_cols:
                standardized[col] = df[col]

        standardized_dfs.append(standardized)
        logger.info(f"Standardized {source_name}: {len(standardized)} samples")

    # Concatenate all standardized DataFrames
    if not standardized_dfs:
        logger.error("No valid datasets to merge")
        return pd.DataFrame(), {
            'samples_per_source': samples_per_source,
            'total_before_merge': 0,
            'total_after_validation': 0,
            'total_after_dedup': 0
        }

    merged_df = pd.concat(standardized_dfs, ignore_index=True)

    # Initialize merge report
    merge_report = {
        'samples_per_source': samples_per_source,
        'total_before_merge': len(merged_df),
        'total_after_validation': len(merged_df),
        'total_after_dedup': len(merged_df)
    }

    logger.info(f"Merged {len(merged_df)} total samples from {len(datasets)} sources")

    # Run validation if requested
    if validate:
        validated_df, validation_report = validate_dataset(merged_df)
        merge_report['validation_report'] = validation_report
        merge_report['total_after_validation'] = len(validated_df)
        merged_df = validated_df

        # Deduplicate after validation
        deduped_df, removed_count = deduplicate_dataset(merged_df, method='exact')
        merge_report['total_after_dedup'] = len(deduped_df)
        merge_report['duplicates_removed'] = removed_count
        merged_df = deduped_df

        logger.info(
            f"After validation and deduplication: {len(merged_df)} samples "
            f"({merge_report['total_before_merge'] - len(merged_df)} removed)"
        )

    return merged_df, merge_report
