"""Main feature extraction interface for URL phishing detection.

This module provides the primary extract_url_features() function that combines
all feature extraction functions into a single interface. It handles URL parsing
and edge cases, returning a consistent dictionary of 30+ numeric features.
"""

from typing import Dict
from urllib.parse import urlparse

import tldextract

from src.features.url_features import (
    extract_binary_features,
    extract_char_features,
    extract_length_features,
    extract_structure_features,
)


def extract_url_features(url: str) -> Dict[str, float]:
    """Extract 30+ numeric features from a URL for phishing detection.

    This is the main entry point for feature extraction. It combines all feature
    categories (length, character counts, binary indicators, structure) into a
    single feature dictionary suitable for machine learning models.

    The function handles edge cases:
    - Empty URLs: Returns all zeros/defaults
    - Invalid URLs: Parses as much as possible, sets is_valid=0
    - IP addresses: Detected and flagged with has_ip=1
    - Unicode domains: Handled by tldextract (punycode)
    - Missing components: Defaults to 0 or empty string

    Args:
        url: URL string to extract features from

    Returns:
        Dictionary mapping feature names to numeric values (int or float).
        Contains exactly 30 features:
            - 7 length features (url_length, domain_length, etc.)
            - 10 character count features (dot_count, hyphen_count, etc.)
            - 8 binary features (has_https, has_ip, etc.)
            - 5 structure features (path_depth, entropy, etc.)

    Examples:
        >>> features = extract_url_features('https://example.com/path?q=1')
        >>> len(features)
        30
        >>> features['has_https']
        1
        >>> features['url_length']
        34

        >>> features = extract_url_features('http://192.168.1.1:8080/admin')
        >>> features['has_ip']
        1
        >>> features['has_port']
        1
        >>> features['has_https']
        0

        >>> features = extract_url_features('https://phish.tk/login')
        >>> features['has_suspicious_tld']
        1

    Note:
        This function performs URL parsing once and passes parsed results to
        all feature extraction functions for efficiency. Typical execution time
        is <10ms per URL.
    """
    # Handle empty URL edge case
    if not url:
        return _get_default_features()

    # Parse URL once for efficiency
    # urlparse: Standard library parser (scheme, netloc, path, query, etc.)
    # tldextract: Robust domain parser (handles Public Suffix List edge cases)
    parsed = urlparse(url)
    extracted = tldextract.extract(url)

    # Combine all feature categories
    features = {}

    # Length features (7)
    features.update(extract_length_features(url, parsed, extracted))

    # Character count features (10)
    features.update(extract_char_features(url))

    # Binary indicator features (8)
    features.update(extract_binary_features(url, parsed, extracted))

    # Structure features (5)
    features.update(extract_structure_features(url, parsed, extracted))

    # Total: 30 features
    return features


def _get_default_features() -> Dict[str, float]:
    """Return default feature values for empty or invalid URLs.

    Used as fallback when URL is empty or cannot be parsed. Returns all zeros
    except for features where 0 has semantic meaning (e.g., entropy=0 is valid).

    Returns:
        Dictionary with all 30 features set to 0 or 0.0
    """
    return {
        # Length features
        'url_length': 0,
        'domain_length': 0,
        'path_length': 0,
        'hostname_length': 0,
        'subdomain_length': 0,
        'tld_length': 0,
        'query_length': 0,
        # Character counts
        'dot_count': 0,
        'hyphen_count': 0,
        'underscore_count': 0,
        'slash_count': 0,
        'question_count': 0,
        'equal_count': 0,
        'at_count': 0,
        'ampersand_count': 0,
        'digit_count': 0,
        'special_char_count': 0,
        # Binary features
        'has_https': 0,
        'has_ip': 0,
        'has_port': 0,
        'has_subdomain': 0,
        'has_query': 0,
        'has_fragment': 0,
        'is_valid': 0,
        'has_suspicious_tld': 0,
        # Structure features
        'path_depth': 0,
        'subdomain_count': 0,
        'param_count': 0,
        'entropy': 0.0,
        'digit_ratio': 0.0,
    }
