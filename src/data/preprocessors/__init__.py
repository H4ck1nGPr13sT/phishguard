"""Data preprocessing module for phishing detection datasets.

Provides functions for merging and standardizing datasets from multiple sources,
temporal splitting, and class balancing.
"""

from .merger import merge_datasets
from .temporal_split import temporal_split, verify_temporal_integrity
from .balancer import balance_training_data, get_class_distribution

__all__ = [
    'merge_datasets',
    'temporal_split',
    'verify_temporal_integrity',
    'balance_training_data',
    'get_class_distribution'
]
