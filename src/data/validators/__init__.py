"""Data validation module for phishing detection datasets.

Provides Pandera schemas and validation functions for ensuring data quality.
"""

from .schemas import PhishingDataSchema, validate_dataset

__all__ = ['PhishingDataSchema', 'validate_dataset']
