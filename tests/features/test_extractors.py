"""Integration tests for unified feature extraction interface.

Tests the extract_features() function and all content type routing,
feature combination, and singleton behavior.
"""

import pytest

from src.features.extractors import (
    ContentType,
    detect_content_type,
    extract_email_features,
    extract_features,
    extract_sms_features,
    get_text_extractor,
)


# Test fixtures
SAMPLE_URL = "https://suspicious-site.tk/login?verify=1"

SAMPLE_EMAIL_BYTES = b"""From: phisher@evil.tk
To: victim@example.com
Subject: URGENT: Verify your account now!
MIME-Version: 1.0
Content-Type: text/plain; charset="utf-8"

Your account has been locked due to suspicious activity.
Click here to verify immediately: https://phishing.tk/verify
"""

SAMPLE_EMAIL_TEXT = """From: sender@example.com
Subject: Normal email
To: recipient@example.com

This is a normal email body with no urgency.
"""

SAMPLE_SMS = "ALERT: Account locked. Click bit.ly/verify123 to unlock NOW!"


class TestContentTypeDetection:
    """Test content type auto-detection logic."""

    def test_detect_url(self):
        """URLs starting with http:// or https:// are detected."""
        assert detect_content_type("https://example.com") == ContentType.URL
        assert detect_content_type("http://example.com/path") == ContentType.URL

    def test_detect_email_bytes(self):
        """Email bytes with headers are detected as EMAIL_FILE."""
        assert detect_content_type(SAMPLE_EMAIL_BYTES) == ContentType.EMAIL_FILE
        assert detect_content_type(b"From: test@example.com\nSubject: Test") == ContentType.EMAIL_FILE

    def test_detect_email_text(self):
        """Email-like text strings are detected as EMAIL."""
        assert detect_content_type(SAMPLE_EMAIL_TEXT) == ContentType.EMAIL
        assert detect_content_type("Subject: Test\nFrom: test@example.com") == ContentType.EMAIL

    def test_detect_sms(self):
        """Plain text defaults to SMS."""
        assert detect_content_type("Hello world") == ContentType.SMS
        assert detect_content_type(SAMPLE_SMS) == ContentType.SMS
        assert detect_content_type("Just a normal text message") == ContentType.SMS


class TestUnifiedInterface:
    """Test extract_features() unified interface."""

    def test_extract_url_features(self):
        """URL extraction via unified interface works."""
        features = extract_features(SAMPLE_URL)
        assert 'content_type' in features
        assert features['content_type'] == 0  # URL
        assert 'has_suspicious_tld' in features
        assert features['has_suspicious_tld'] == 1  # .tk is suspicious
        assert len(features) == 31  # 30 URL features + 1 content_type

    def test_extract_email_features(self):
        """Email extraction returns combined header + text features."""
        features = extract_features(SAMPLE_EMAIL_BYTES)
        assert 'content_type' in features
        assert features['content_type'] == 1  # EMAIL
        assert len(features) == 66  # 15 header + 50 text + 1 content_type

    def test_extract_sms_features(self):
        """SMS extraction returns combined SMS-specific + text features."""
        features = extract_features(SAMPLE_SMS, ContentType.SMS)
        assert 'content_type' in features
        assert features['content_type'] == 2  # SMS
        assert len(features) == 71  # 20 SMS + 50 text + 1 content_type

    def test_auto_detect_url(self):
        """Auto-detection routes URL correctly."""
        features = extract_features("https://example.com")
        assert features['content_type'] == 0
        assert 'url_length' in features

    def test_auto_detect_sms(self):
        """Auto-detection routes SMS correctly."""
        features = extract_features("Hello world")
        assert features['content_type'] == 2
        assert 'text_word_count' in features


class TestFeatureCombination:
    """Test that features are correctly combined from multiple extractors."""

    def test_email_combines_header_and_text(self):
        """Email features include both header and text features."""
        features = extract_email_features(SAMPLE_EMAIL_BYTES)

        # Should have header features (not prefixed)
        header_features = [k for k in features.keys() if not k.startswith('text_')]
        assert len(header_features) == 15, f"Expected 15 header features, got {len(header_features)}"

        # Should have text features (prefixed)
        text_features = [k for k in features.keys() if k.startswith('text_')]
        assert len(text_features) == 50, f"Expected 50 text features, got {len(text_features)}"

        # Check some specific features
        assert 'from_domain_suspicious' in features  # Header feature
        assert 'text_word_count' in features  # Text feature
        assert 'text_has_urgency' in features  # Text sentiment feature

    def test_sms_combines_specific_and_text(self):
        """SMS features include both SMS-specific and text features."""
        features = extract_sms_features(SAMPLE_SMS)

        # Should have SMS-specific features (not prefixed)
        sms_features = [k for k in features.keys() if not k.startswith('text_')]
        assert len(sms_features) == 20, f"Expected 20 SMS features, got {len(sms_features)}"

        # Should have text features (prefixed)
        text_features = [k for k in features.keys() if k.startswith('text_')]
        assert len(text_features) == 50, f"Expected 50 text features, got {len(text_features)}"

        # Check some specific features
        assert 'has_shortened_url' in features  # SMS feature
        assert 'text_word_count' in features  # Text feature
        assert 'text_has_urgency' in features  # Text sentiment feature

    def test_text_features_prefixed(self):
        """All NLP text features have 'text_' prefix."""
        # Test email
        email_features = extract_email_features(SAMPLE_EMAIL_BYTES)
        text_prefixed = [k for k in email_features.keys() if k.startswith('text_')]
        assert len(text_prefixed) == 50, "Email should have exactly 50 text-prefixed features"

        # Test SMS
        sms_features = extract_sms_features(SAMPLE_SMS)
        text_prefixed = [k for k in sms_features.keys() if k.startswith('text_')]
        assert len(text_prefixed) == 50, "SMS should have exactly 50 text-prefixed features"


class TestSingletonBehavior:
    """Test that TextFeatureExtractor is properly shared."""

    def test_text_extractor_singleton(self):
        """Same TextFeatureExtractor instance is reused."""
        extractor1 = get_text_extractor()
        extractor2 = get_text_extractor()
        assert id(extractor1) == id(extractor2), "Should return same instance"

    def test_spacy_loaded_once(self):
        """spaCy model is not reloaded on multiple extractions."""
        # First extraction loads spaCy
        features1 = extract_email_features(SAMPLE_EMAIL_BYTES)
        extractor1 = get_text_extractor()

        # Second extraction reuses same instance
        features2 = extract_sms_features(SAMPLE_SMS)
        extractor2 = get_text_extractor()

        assert id(extractor1) == id(extractor2), "Should reuse TextFeatureExtractor"
        assert len(features1) == 65
        assert len(features2) == 70


class TestErrorHandling:
    """Test graceful error handling for edge cases."""

    def test_empty_content(self):
        """Empty content returns defaults, not crash."""
        # Empty URL
        url_features = extract_features("")
        assert 'content_type' in url_features

        # Empty email
        email_features = extract_email_features(b"")
        assert len(email_features) == 65  # Returns defaults

        # Empty SMS
        sms_features = extract_sms_features("")
        assert len(sms_features) == 70  # Returns defaults

    def test_malformed_email(self):
        """Malformed email returns default features gracefully."""
        malformed = b"Not a valid email at all!"
        features = extract_email_features(malformed)
        assert len(features) == 65  # Returns all features with defaults
        assert 'text_word_count' in features

    def test_unicode_content(self):
        """Unicode and emoji content is handled correctly."""
        unicode_sms = "🚨 URGENT: Your account 账户 has been locked! 🔒"
        features = extract_sms_features(unicode_sms)
        # SMS features have emoji_count (not text_emoji_count)
        assert 'emoji_count' in features
        assert features['emoji_count'] > 0
        assert len(features) == 70


class TestSpecificFeatureValues:
    """Test that specific feature values are correct for known inputs."""

    def test_suspicious_email_features(self):
        """Suspicious email triggers expected features."""
        features = extract_email_features(SAMPLE_EMAIL_BYTES)

        # Header features
        assert features['from_domain_suspicious'] == 1  # evil.tk
        assert features['has_urgent_subject'] == 1  # URGENT in subject

        # Text features
        assert features['text_has_urgency'] > 0  # Body has urgency
        assert features['text_url_count'] > 0  # Contains URL

    def test_sms_with_shortened_url(self):
        """SMS with shortened URL triggers expected features."""
        features = extract_sms_features(SAMPLE_SMS)

        assert features['has_shortened_url'] == 1  # bit.ly
        assert features['has_urgency_caps'] == 1  # ALERT, NOW
        assert features['text_has_urgency'] > 0  # Urgency sentiment

    def test_url_with_suspicious_tld(self):
        """URL with suspicious TLD is detected."""
        features = extract_features(SAMPLE_URL)

        assert features['has_suspicious_tld'] == 1  # .tk
        assert features['url_length'] > 0
        assert features['has_query'] == 1  # ?verify=1
