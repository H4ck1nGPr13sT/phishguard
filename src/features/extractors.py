"""Main feature extraction interface for URL phishing detection.

This module provides the primary extract_url_features() function that combines
all feature extraction functions into a single interface. It handles URL parsing
and edge cases, returning a consistent dictionary of 30+ numeric features.

Extended in Phase 06 to support unified extraction for URL, Email, and SMS inputs.
"""

from enum import Enum
from typing import Dict, Optional, Union
from urllib.parse import urlparse

import tldextract

from src.features.url_features import (
    extract_binary_features,
    extract_char_features,
    extract_length_features,
    extract_structure_features,
)
from email import message_from_bytes, policy
from src.features.email_features import parse_email, extract_email_header_features
from src.features.text_features import TextFeatureExtractor
from src.features.sms_features import extract_sms_features as extract_sms_specific_features


class ContentType(Enum):
    """Content types supported by unified feature extraction."""
    URL = "url"
    EMAIL = "email"
    EMAIL_FILE = "email_file"  # .eml bytes
    SMS = "sms"
    IMAGE = "image"


# Module-level extractor - loads spaCy model once
_text_extractor: Optional[TextFeatureExtractor] = None


def get_text_extractor() -> TextFeatureExtractor:
    """Get or create singleton TextFeatureExtractor.

    Loads the spaCy model once and reuses across all text extractions.
    This is significantly more efficient than creating a new extractor
    for each email or SMS message.

    Returns:
        Singleton TextFeatureExtractor instance
    """
    global _text_extractor
    if _text_extractor is None:
        _text_extractor = TextFeatureExtractor()
    return _text_extractor


# Module-level OCR backend singleton - avoids re-resolving (and, once
# EasyOCRBackend is in use, re-loading model weights) on every image request.
_ocr_backend = None


def get_ocr_backend():
    """Get or create singleton OCR backend for image feature extraction.

    Mirrors get_text_extractor()'s singleton-on-first-use pattern. Lazily
    imports resolve_ocr_backend() from src.features.ocr INSIDE this function
    body (never at module top level) so importing src.features.extractors
    never requires easyocr/torch to be installed.

    Returns:
        Singleton OCRBackend instance (EasyOCRBackend if easyocr is
        importable, else NullOCRBackend).
    """
    global _ocr_backend
    if _ocr_backend is None:
        from src.features.ocr import resolve_ocr_backend
        _ocr_backend = resolve_ocr_backend()
    return _ocr_backend


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


def extract_email_features(raw_email: bytes) -> Dict[str, float]:
    """Extract combined header and text features from email.

    Combines email-specific header features (~15) with NLP text features (~50)
    from the email body. Text features are prefixed with "text_" to distinguish
    them from header features.

    Args:
        raw_email: Raw email bytes (from .eml file or SMTP)

    Returns:
        Dictionary with ~65 features:
            - 15 email header features (authentication, sender, subject, structure)
            - 50 text features prefixed with "text_" (lexical, syntactic, stylometric, sentiment)

    Examples:
        >>> email = b"From: phisher@evil.tk\\nSubject: URGENT ACTION REQUIRED\\n\\nVerify now!"
        >>> features = extract_email_features(email)
        >>> features['from_domain_suspicious']
        1
        >>> features['text_has_urgency']
        1
        >>> len(features)
        65
    """
    if not raw_email:
        # Return default header features + default text features
        header_features = extract_email_header_features(None)
        text_extractor = get_text_extractor()
        text_features = text_extractor.extract_all_features("")
        # Prefix text features
        text_features_prefixed = {f"text_{k}": v for k, v in text_features.items()}
        return {**header_features, **text_features_prefixed}

    try:
        # Parse email for both header and text extraction
        # parse_email() returns dict with headers and body
        parsed = parse_email(raw_email)

        # Parse again to get EmailMessage object for header features
        # (extract_email_header_features expects EmailMessage, not dict)
        msg = message_from_bytes(raw_email, policy=policy.default)

        # Extract header features from EmailMessage object
        header_features = extract_email_header_features(msg)

        # Extract text features from body
        text_extractor = get_text_extractor()
        text_features = text_extractor.extract_all_features(parsed['body'])

        # Prefix text features to distinguish from header features
        text_features_prefixed = {f"text_{k}": v for k, v in text_features.items()}

        # Combine both feature sets
        return {**header_features, **text_features_prefixed}

    except Exception:
        # On parse failure, return defaults
        header_features = extract_email_header_features(None)
        text_extractor = get_text_extractor()
        text_features = text_extractor.extract_all_features("")
        text_features_prefixed = {f"text_{k}": v for k, v in text_features.items()}
        return {**header_features, **text_features_prefixed}


def extract_sms_features(message: str) -> Dict[str, float]:
    """Extract combined SMS-specific and text features from SMS message.

    Combines SMS-specific features (~20) with NLP text features (~50) from the
    message text. Text features are prefixed with "text_" to distinguish them
    from SMS-specific features.

    Args:
        message: SMS message text to analyze

    Returns:
        Dictionary with ~70 features:
            - 20 SMS-specific features (length, URL, phone, character, patterns)
            - 50 text features prefixed with "text_" (lexical, syntactic, stylometric, sentiment)

    Examples:
        >>> sms = "URGENT: Account locked. Click bit.ly/verify123 to unlock!"
        >>> features = extract_sms_features(sms)
        >>> features['has_shortened_url']
        1
        >>> features['urgency_caps_count']
        1
        >>> features['text_has_urgency']
        1
        >>> len(features)
        70
    """
    if not message:
        # Return default SMS features + default text features
        sms_features = extract_sms_specific_features("")
        text_extractor = get_text_extractor()
        text_features = text_extractor.extract_all_features("")
        # Prefix text features
        text_features_prefixed = {f"text_{k}": v for k, v in text_features.items()}
        return {**sms_features, **text_features_prefixed}

    try:
        # Extract SMS-specific features
        sms_features = extract_sms_specific_features(message)

        # Extract text features from message
        text_extractor = get_text_extractor()
        text_features = text_extractor.extract_all_features(message)

        # Prefix text features to distinguish from SMS features
        text_features_prefixed = {f"text_{k}": v for k, v in text_features.items()}

        # Combine both feature sets
        return {**sms_features, **text_features_prefixed}

    except Exception:
        # On extraction failure, return defaults
        sms_features = extract_sms_specific_features("")
        text_extractor = get_text_extractor()
        text_features = text_extractor.extract_all_features("")
        text_features_prefixed = {f"text_{k}": v for k, v in text_features.items()}
        return {**sms_features, **text_features_prefixed}


def detect_content_type(content: Union[str, bytes]) -> ContentType:
    """Auto-detect content type from input.

    Analyzes the content to determine if it's a URL, email, or SMS message.
    Uses pattern matching on common headers and URL schemes.

    Note: images are never auto-detected here. Raw image bytes are
    ambiguous versus .eml bytes, and image requests always arrive from the
    API endpoint with an explicit ContentType.IMAGE — see extract_features().

    Args:
        content: Input content (string or bytes)

    Returns:
        ContentType enum value (URL, EMAIL, EMAIL_FILE, or SMS)

    Examples:
        >>> detect_content_type("https://example.com")
        <ContentType.URL: 'url'>
        >>> detect_content_type(b"From: test@example.com\\nSubject: Test")
        <ContentType.EMAIL_FILE: 'email_file'>
        >>> detect_content_type("From: test@example.com\\nSubject: Test")
        <ContentType.EMAIL: 'email'>
        >>> detect_content_type("Hello world")
        <ContentType.SMS: 'sms'>
    """
    if isinstance(content, bytes):
        # Check for email headers in bytes
        content_lower = content.lower()
        if (b'from:' in content_lower or
            b'subject:' in content_lower or
            b'mime-version:' in content_lower):
            return ContentType.EMAIL_FILE
        # If bytes but not email, convert to string for further checks
        try:
            content = content.decode('utf-8', errors='ignore')
        except Exception:
            return ContentType.SMS  # Default to SMS for unknown bytes

    # Now content is a string
    content_stripped = content.strip()

    # Check for URL (starts with http:// or https://)
    if content_stripped.startswith(('http://', 'https://')):
        return ContentType.URL

    # Check for email-like text (has email headers)
    content_lower = content.lower()
    if ('from:' in content_lower or
        'subject:' in content_lower or
        'to:' in content_lower):
        return ContentType.EMAIL

    # Default to SMS for plain text
    return ContentType.SMS


def extract_features(content: Union[str, bytes],
                     content_type: Optional[ContentType] = None) -> Dict[str, float]:
    """Unified feature extraction interface for all content types.

    Main entry point for feature extraction. Auto-detects content type if not
    specified, then routes to the appropriate extractor. Adds a content_type
    feature to help models distinguish between input types.

    Args:
        content: Input content (URL string, email bytes/string, or SMS string)
        content_type: Optional ContentType enum to skip auto-detection

    Returns:
        Dictionary of numeric features. Feature count varies by content type:
            - URL: ~30 features
            - EMAIL: ~65 features (15 header + 50 text)
            - SMS: ~70 features (20 SMS-specific + 50 text)
        All feature dicts include a "content_type" feature:
            - 0 = URL
            - 1 = EMAIL
            - 2 = SMS
            - 3 = IMAGE

    Examples:
        >>> # Auto-detect URL
        >>> features = extract_features("https://phishing.tk/login")
        >>> features['content_type']
        0
        >>> features['has_suspicious_tld']
        1

        >>> # Extract email features
        >>> email_bytes = b"From: test@evil.tk\\nSubject: URGENT\\n\\nVerify now!"
        >>> features = extract_features(email_bytes)
        >>> features['content_type']
        1
        >>> features['has_suspicious_sender_tld']
        1

        >>> # Extract SMS features with explicit type
        >>> from src.features.extractors import ContentType
        >>> features = extract_features("URGENT: Click bit.ly/abc", ContentType.SMS)
        >>> features['content_type']
        2
        >>> features['has_shortened_url']
        1
    """
    # Auto-detect if not specified
    if content_type is None:
        content_type = detect_content_type(content)

    # Route to appropriate extractor
    if content_type == ContentType.URL:
        features = extract_url_features(content if isinstance(content, str) else content.decode('utf-8', errors='ignore'))
        features['content_type'] = 0

    elif content_type in (ContentType.EMAIL, ContentType.EMAIL_FILE):
        # Convert string emails to bytes if needed
        if isinstance(content, str):
            content = content.encode('utf-8')
        features = extract_email_features(content)
        features['content_type'] = 1

    elif content_type == ContentType.SMS:
        # Convert bytes to string if needed
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='ignore')
        features = extract_sms_features(content)
        features['content_type'] = 2

    elif content_type == ContentType.IMAGE:
        # Images are binary-only - no silent str->bytes coercion (T-07-06).
        if not isinstance(content, bytes):
            raise TypeError(
                "ContentType.IMAGE requires bytes content (raw image data); "
                f"got {type(content).__name__} instead."
            )
        # Lazy imports: image_features pulls Pillow eagerly and cv2/imagehash
        # lazily, and resolve_ocr_backend() lazily imports easyocr/torch.
        # Importing these INSIDE this branch (never at module top level)
        # preserves the torch/cv2-free module-load contract relied on by
        # the rest of the test suite.
        from src.features.image_features import extract_image_features
        backend = get_ocr_backend()
        features = extract_image_features(content, backend)
        features['content_type'] = 3

    else:
        # Fallback to SMS for unknown types
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='ignore')
        features = extract_sms_features(content)
        features['content_type'] = 2

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
