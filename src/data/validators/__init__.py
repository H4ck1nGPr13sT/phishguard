"""Data validation module for phishing detection datasets.

Provides Pandera schemas and validation functions for ensuring data quality.
"""

from .schemas import PhishingDataSchema, validate_dataset
from .quality import deduplicate_dataset, check_data_quality

__all__ = ['PhishingDataSchema', 'validate_dataset', 'deduplicate_dataset', 'check_data_quality']
