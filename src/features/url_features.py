"""Individual feature extraction functions for URL analysis.

This module contains helper functions for extracting specific categories of
features from URLs: length features, character counts, binary indicators, and
structure features.
"""

import math
import re
from collections import Counter
from typing import Dict
from urllib.parse import ParseResult

import tldextract
from tldextract.tldextract import ExtractResult


def calculate_entropy(text: str) -> float:
    """Calculate Shannon entropy of a string.

    Shannon entropy measures the randomness/unpredictability of characters in a
    string. Higher entropy indicates more random characters (common in phishing
    URLs that use obfuscation).

    Args:
        text: Input string to calculate entropy for

    Returns:
        Shannon entropy value (float). Returns 0.0 for empty strings.

    Examples:
        >>> calculate_entropy('aaaa')  # Low entropy (very predictable)
        0.0
        >>> calculate_entropy('abcd')  # Higher entropy
        2.0
        >>> calculate_entropy('a1b2c3')  # High entropy (mixed characters)
        2.585
    """
    if not text:
        return 0.0

    counts = Counter(text)
    length = len(text)
    probs = [count / length for count in counts.values()]
    entropy = -sum(p * math.log2(p) for p in probs if p > 0)

    return entropy


def extract_length_features(
    url: str, parsed: ParseResult, extracted: ExtractResult
) -> Dict[str, int]:
    """Extract length-based features from URL.

    Length features measure the character counts of various URL components.
    Phishing URLs often have unusually long URLs, domains, or paths to obscure
    the actual destination.

    Args:
        url: Original URL string
        parsed: Parsed URL from urllib.parse.urlparse()
        extracted: Extracted domain info from tldextract.extract()

    Returns:
        Dictionary with 7 length features:
            - url_length: Total URL length
            - domain_length: Length of domain name (without subdomain/TLD)
            - path_length: Length of URL path component
            - hostname_length: Length of full hostname (subdomain.domain.tld)
            - subdomain_length: Length of subdomain component
            - tld_length: Length of TLD (e.g., 'com' = 3)
            - query_length: Length of query string

    Examples:
        >>> from urllib.parse import urlparse
        >>> import tldextract
        >>> url = 'https://www.example.com/path?query=1'
        >>> parsed = urlparse(url)
        >>> extracted = tldextract.extract(url)
        >>> features = extract_length_features(url, parsed, extracted)
        >>> features['url_length']
        37
        >>> features['domain_length']
        7
    """
    return {
        'url_length': len(url),
        'domain_length': len(extracted.domain),
        'path_length': len(parsed.path),
        'hostname_length': len(parsed.netloc),
        'subdomain_length': len(extracted.subdomain),
        'tld_length': len(extracted.suffix),
        'query_length': len(parsed.query),
    }


def extract_char_features(url: str) -> Dict[str, int]:
    """Extract character count features from URL.

    Character counts identify suspicious patterns in URLs. Phishing URLs often
    contain excessive special characters (@, -, .), many digits, or unusual
    character combinations.

    Args:
        url: Original URL string

    Returns:
        Dictionary with 10 character count features:
            - dot_count: Number of dots (.)
            - hyphen_count: Number of hyphens (-)
            - underscore_count: Number of underscores (_)
            - slash_count: Number of slashes (/)
            - question_count: Number of question marks (?)
            - equal_count: Number of equals signs (=)
            - at_count: Number of @ symbols
            - ampersand_count: Number of ampersands (&)
            - digit_count: Number of digit characters
            - special_char_count: Total non-alphanumeric characters

    Examples:
        >>> url = 'https://example.com/path?a=1&b=2'
        >>> features = extract_char_features(url)
        >>> features['dot_count']
        1
        >>> features['question_count']
        1
        >>> features['digit_count']
        2
    """
    return {
        'dot_count': url.count('.'),
        'hyphen_count': url.count('-'),
        'underscore_count': url.count('_'),
        'slash_count': url.count('/'),
        'question_count': url.count('?'),
        'equal_count': url.count('='),
        'at_count': url.count('@'),
        'ampersand_count': url.count('&'),
        'digit_count': sum(c.isdigit() for c in url),
        'special_char_count': len(re.findall(r'[^a-zA-Z0-9]', url)),
    }


def extract_binary_features(
    url: str, parsed: ParseResult, extracted: ExtractResult
) -> Dict[str, int]:
    """Extract binary indicator features from URL.

    Binary features indicate presence/absence of specific properties. These are
    common indicators of phishing: lack of HTTPS, IP addresses instead of domains,
    suspicious TLDs, etc.

    Args:
        url: Original URL string
        parsed: Parsed URL from urllib.parse.urlparse()
        extracted: Extracted domain info from tldextract.extract()

    Returns:
        Dictionary with 8 binary features (1 = present, 0 = absent):
            - has_https: URL uses HTTPS protocol
            - has_ip: Hostname is an IP address (e.g., 192.168.1.1)
            - has_port: URL specifies a port (e.g., :8080)
            - has_subdomain: URL has subdomain component
            - has_query: URL has query string
            - has_fragment: URL has fragment (# anchor)
            - is_valid: URL passes basic validation
            - has_suspicious_tld: TLD is in suspicious list

    Examples:
        >>> from urllib.parse import urlparse
        >>> import tldextract
        >>> url = 'https://subdomain.example.com/path?q=1#anchor'
        >>> parsed = urlparse(url)
        >>> extracted = tldextract.extract(url)
        >>> features = extract_binary_features(url, parsed, extracted)
        >>> features['has_https']
        1
        >>> features['has_subdomain']
        1
        >>> features['has_query']
        1
        >>> features['has_fragment']
        1
    """
    # Suspicious TLDs commonly used in phishing
    # Source: Research on phishing URL patterns
    suspicious_tlds = {'tk', 'ml', 'ga', 'cf', 'gq', 'xyz', 'pw', 'cc'}

    # Check for IP address in hostname
    # Matches IPv4 pattern (e.g., 192.168.1.1)
    has_ip = bool(re.match(r'^\d+\.\d+\.\d+\.\d+', parsed.netloc))

    # Basic URL validation: has scheme and netloc
    is_valid = bool(parsed.scheme and parsed.netloc)

    return {
        'has_https': 1 if parsed.scheme == 'https' else 0,
        'has_ip': 1 if has_ip else 0,
        'has_port': 1 if parsed.port is not None else 0,
        'has_subdomain': 1 if extracted.subdomain else 0,
        'has_query': 1 if parsed.query else 0,
        'has_fragment': 1 if parsed.fragment else 0,
        'is_valid': 1 if is_valid else 0,
        'has_suspicious_tld': 1 if extracted.suffix.lower() in suspicious_tlds else 0,
    }


def extract_structure_features(
    url: str, parsed: ParseResult, extracted: ExtractResult
) -> Dict[str, float]:
    """Extract URL structure features.

    Structure features capture the organization and complexity of the URL.
    Phishing URLs often have unusual structures: deep paths, many subdomains,
    high entropy, or unusual digit ratios.

    Args:
        url: Original URL string
        parsed: Parsed URL from urllib.parse.urlparse()
        extracted: Extracted domain info from tldextract.extract()

    Returns:
        Dictionary with 5 structure features:
            - path_depth: Number of path segments (e.g., /a/b/c = 3)
            - subdomain_count: Number of subdomain levels
            - param_count: Number of query parameters
            - entropy: Shannon entropy of entire URL
            - digit_ratio: Ratio of digits to total characters

    Examples:
        >>> from urllib.parse import urlparse
        >>> import tldextract
        >>> url = 'https://sub1.sub2.example.com/a/b/c?x=1&y=2'
        >>> parsed = urlparse(url)
        >>> extracted = tldextract.extract(url)
        >>> features = extract_structure_features(url, parsed, extracted)
        >>> features['path_depth']
        3
        >>> features['param_count']
        2
        >>> features['digit_ratio']  # Should be > 0 due to '1' and '2'
        0.04...
    """
    # Count non-empty path segments
    path_depth = len([p for p in parsed.path.split('/') if p])

    # Count subdomain levels (split by dots)
    subdomain_count = len(extracted.subdomain.split('.')) if extracted.subdomain else 0

    # Count query parameters (split by &)
    param_count = len(parsed.query.split('&')) if parsed.query else 0

    # Calculate entropy for entire URL
    entropy = calculate_entropy(url)

    # Calculate digit ratio
    digit_count = sum(c.isdigit() for c in url)
    digit_ratio = digit_count / len(url) if url else 0.0

    return {
        'path_depth': path_depth,
        'subdomain_count': subdomain_count,
        'param_count': param_count,
        'entropy': entropy,
        'digit_ratio': digit_ratio,
    }
