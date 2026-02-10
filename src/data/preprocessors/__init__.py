"""Data preprocessing module for phishing detection datasets.

Provides functions for merging and standardizing datasets from multiple sources.
"""

from .merger import merge_datasets

__all__ = ['merge_datasets']
