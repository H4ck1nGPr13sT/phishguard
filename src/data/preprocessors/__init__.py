"""Data preprocessing module for phishing detection datasets.

Provides functions for merging and standardizing datasets from multiple sources,
temporal splitting, and class balancing.
"""

from .merger import merge_datasets
from .temporal_split import temporal_split, verify_temporal_integrity

__all__ = ['merge_datasets', 'temporal_split', 'verify_temporal_integrity']
