"""Class imbalance handling for phishing detection training data.

This module provides SMOTE + undersampling for balancing training data.

CRITICAL: These functions should ONLY be applied to training data, NEVER to
validation or test data. Applying balancing to validation/test would cause
data leakage and invalidate model evaluation.

Design decisions:
- Hybrid SMOTE + undersampling approach for robust balancing
- Configurable target ratio (default: 0.5 for 50/50 balance)
- Detailed balance report for thesis documentation
- Random state from config for reproducibility
"""

from typing import Any, Dict, Tuple

import pandas as pd

from src.config.settings import RANDOM_SEED


def balance_training_data(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    target_ratio: float = 0.5,
    random_state: int = None
) -> Tuple[pd.DataFrame, pd.Series, Dict[str, Any]]:
    """Balance training data using SMOTE + undersampling pipeline.

    WARNING: NEVER apply to validation or test data - this would cause data leakage.
    Only use on training data after temporal split.

    Applies SMOTE (Synthetic Minority Over-sampling Technique) to generate synthetic
    minority class samples, then undersamples majority class to achieve target ratio.

    Args:
        X_train: Training features DataFrame
        y_train: Training labels Series
        target_ratio: Target proportion of minority class in final dataset (default: 0.5 for 50/50 balanced)
                     For example, 0.5 means 50% minority and 50% majority.
        random_state: Random seed for reproducibility (default: uses RANDOM_SEED from config)

    Returns:
        Tuple of (X_resampled, y_resampled, balance_report)

        balance_report contains:
        - original_counts: {class: count} before balancing
        - final_counts: {class: count} after balancing
        - technique: 'SMOTE + RandomUnderSampler'
        - target_ratio: the proportion used
        - synthetic_samples_added: count of SMOTE-generated samples
        - samples_removed: count removed by undersampling
        - random_state: seed used

    Raises:
        ValueError: If all samples are one class (cannot balance)
        ValueError: If target_ratio not in (0, 1)

    Example:
        >>> X = pd.DataFrame({'feature1': range(100), 'feature2': range(100, 200)})
        >>> y = pd.Series([0] * 90 + [1] * 10)  # 90% class 0, 10% class 1
        >>> X_bal, y_bal, report = balance_training_data(X, y, target_ratio=0.5)
        >>> # Result: approximately 50% minority, 50% majority
        >>> print(report['technique'])
        'SMOTE + RandomUnderSampler'
    """
    # Validate target_ratio
    if not (0 < target_ratio < 1):
        raise ValueError(f"target_ratio must be in (0, 1), got {target_ratio}")

    # Use RANDOM_SEED from config if not provided
    if random_state is None:
        random_state = RANDOM_SEED

    # Record original class distribution
    original_counts = y_train.value_counts().to_dict()

    # Check for single-class data
    if len(original_counts) < 2:
        raise ValueError(
            f"Cannot balance data with only one class: {list(original_counts.keys())}"
        )

    # Determine minority and majority classes
    minority_class = min(original_counts, key=original_counts.get)
    majority_class = max(original_counts, key=original_counts.get)

    # Check if already balanced (within 5% of target)
    current_ratio = original_counts[minority_class] / original_counts[majority_class]
    if abs(current_ratio - target_ratio) < 0.05:
        return (
            X_train.copy(),
            y_train.copy(),
            {
                'original_counts': original_counts,
                'final_counts': original_counts,
                'technique': 'None (already balanced)',
                'target_ratio': target_ratio,
                'synthetic_samples_added': 0,
                'samples_removed': 0,
                'random_state': random_state
            }
        )

    # Import imbalanced-learn
    try:
        from imblearn.over_sampling import SMOTE
        from imblearn.under_sampling import RandomUnderSampler
        from imblearn.pipeline import Pipeline as ImbPipeline
    except ImportError:
        raise ImportError(
            "imbalanced-learn is required for balancing. Install with: pip install imbalanced-learn"
        )

    # Two-step approach: SMOTE first, then manual undersampling
    # This gives us more control over the final ratio

    # Step 1: SMOTE to oversample minority class
    k_neighbors = 5
    if original_counts[minority_class] < k_neighbors + 1:
        k_neighbors = max(1, original_counts[minority_class] - 1)

    if k_neighbors < 1:
        # Too few samples for SMOTE
        import warnings
        warnings.warn(
            f"Minority class has only {original_counts[minority_class]} samples. "
            f"Using RandomOverSampler instead of SMOTE."
        )
        from imblearn.over_sampling import RandomOverSampler
        smote = RandomOverSampler(sampling_strategy='auto', random_state=random_state)
    else:
        smote = SMOTE(sampling_strategy='auto', random_state=random_state, k_neighbors=k_neighbors)

    X_after_smote, y_after_smote = smote.fit_resample(X_train, y_train)

    # Step 2: Undersample to achieve target ratio
    # After SMOTE, minority matches majority (both have ~majority_count)
    # target_ratio is the desired proportion of minority class
    # For example, target_ratio=0.5 means 50% minority, 50% majority
    #
    # Let minority_final = M, majority_final = J
    # target_ratio = M / (M + J)
    # Solving for J: J = M * (1 - target_ratio) / target_ratio
    #
    # Strategy: After SMOTE balances classes, undersample to achieve desired proportion

    counts_after_smote = pd.Series(y_after_smote).value_counts().to_dict()
    minority_count_after_smote = counts_after_smote[minority_class]
    majority_count_after_smote = counts_after_smote[majority_class]

    # Calculate desired counts for target proportion
    # If target_ratio = 0.5 (50% minority), then minority = majority
    # If target_ratio = 0.3 (30% minority), then majority = minority * 0.7 / 0.3 = minority * 2.33
    desired_majority_count = int(minority_count_after_smote * (1 - target_ratio) / target_ratio)

    # If desired majority count is more than what we have after SMOTE,
    # we can't achieve that ratio without oversampling majority (which we don't want)
    # In that case, keep the balanced result
    if desired_majority_count >= majority_count_after_smote:
        X_resampled = X_after_smote
        y_resampled = y_after_smote
    else:
        # Undersample majority class to achieve target proportion
        undersample_strategy = {
            minority_class: minority_count_after_smote,
            majority_class: desired_majority_count
        }
        undersampler = RandomUnderSampler(sampling_strategy=undersample_strategy, random_state=random_state)
        X_resampled, y_resampled = undersampler.fit_resample(X_after_smote, y_after_smote)

    # Convert back to pandas
    X_resampled = pd.DataFrame(X_resampled, columns=X_train.columns)
    y_resampled = pd.Series(y_resampled, name=y_train.name)

    # Calculate synthetic samples added and samples removed
    final_counts = y_resampled.value_counts().to_dict()
    total_original = sum(original_counts.values())
    total_after_smote = sum(counts_after_smote.values())
    synthetic_samples_added = total_after_smote - total_original
    samples_removed = total_after_smote - len(X_resampled)

    # Generate balance report
    balance_report = {
        'original_counts': original_counts,
        'final_counts': final_counts,
        'technique': 'SMOTE + RandomUnderSampler',
        'target_ratio': target_ratio,
        'synthetic_samples_added': int(synthetic_samples_added),
        'samples_removed': int(samples_removed),
        'random_state': random_state
    }

    return X_resampled, y_resampled, balance_report


def get_class_distribution(y: pd.Series) -> Dict[str, Any]:
    """Get detailed class distribution statistics.

    Args:
        y: Label Series

    Returns:
        Dictionary with:
        - class counts (e.g., {0: 100, 1: 50})
        - 'majority': label of majority class
        - 'minority': label of minority class
        - 'imbalance_ratio': minority/majority ratio

    Example:
        >>> y = pd.Series([0] * 90 + [1] * 10)
        >>> dist = get_class_distribution(y)
        >>> print(dist['imbalance_ratio'])
        0.111...
    """
    counts = y.value_counts().to_dict()

    if len(counts) == 0:
        return {
            'majority': None,
            'minority': None,
            'imbalance_ratio': None
        }

    if len(counts) == 1:
        single_class = list(counts.keys())[0]
        return {
            **counts,
            'majority': single_class,
            'minority': None,
            'imbalance_ratio': None
        }

    minority_class = min(counts, key=counts.get)
    majority_class = max(counts, key=counts.get)

    imbalance_ratio = counts[minority_class] / counts[majority_class]

    return {
        **counts,
        'majority': majority_class,
        'minority': minority_class,
        'imbalance_ratio': imbalance_ratio
    }
