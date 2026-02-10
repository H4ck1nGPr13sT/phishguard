"""Feature extraction module for URL phishing detection.

This module provides functions to extract numeric features from URLs for machine
learning models. Features include URL length, special character counts, binary
indicators (HTTPS, IP addresses), and structure properties.

Exports:
    extract_url_features: Main feature extraction function
    calculate_entropy: Shannon entropy calculation
    extract_length_features: Length-based features
    extract_char_features: Character count features
    extract_binary_features: Binary indicator features
    extract_structure_features: URL structure features
"""

from src.features.extractors import extract_url_features
from src.features.url_features import (
    calculate_entropy,
    extract_binary_features,
    extract_char_features,
    extract_length_features,
    extract_structure_features,
)

__all__ = [
    'extract_url_features',
    'calculate_entropy',
    'extract_length_features',
    'extract_char_features',
    'extract_binary_features',
    'extract_structure_features',
]
