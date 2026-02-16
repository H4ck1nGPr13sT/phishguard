"""Unit tests for SMS feature extraction module."""

import pytest

from src.features.sms_features import (
    extract_sms_features,
    parse_sms,
    SHORTENED_URL_DOMAINS,
)


# Test fixtures - Sample SMS messages
@pytest.fixture
def smishing_text():
    """Typical smishing message with urgency and shortened URL."""
    return "ALERT: Your bank account locked. Verify now: bit.ly/x1y2z3"


@pytest.fixture
def legitimate_sms():
    """Legitimate SMS from a service."""
    return "Your package has shipped. Track at: ups.com/track/123456"


@pytest.fixture
def prize_scam():
    """Prize scam SMS."""
    return "Congratulations! You WON $10000. Call 1-800-555-0123 to claim!"


@pytest.fixture
def long_sms():
    """Multipart SMS exceeding 160 characters."""
    return (
        "This is a very long SMS message that exceeds the standard 160 character "
        "limit for a single SMS segment. It will be split into multiple parts when "
        "sent over the mobile network. This is used to test multipart detection."
    )


@pytest.fixture
def empty_sms():
    """Empty SMS message."""
    return ""


@pytest.fixture
def emoji_sms():
    """SMS with emoji characters."""
    return "Your order is ready for pickup 📦🎉"


@pytest.fixture
def whitespace_only():
    """SMS with only whitespace."""
    return "   \t\n  "


# Test parse_sms() function
class TestParseSms:
    """Tests for parse_sms() function."""

    def test_parse_extracts_urls(self):
        """Test URL extraction from SMS."""
        message = "Visit https://example.com or bit.ly/abc123"
        result = parse_sms(message)

        assert len(result['urls']) == 2
        assert 'https://example.com' in result['urls']
        assert 'bit.ly/abc123' in result['urls']

    def test_parse_extracts_phone(self):
        """Test phone number extraction."""
        message = "Call 1-800-555-0123 or text +44 20 1234 5678"
        result = parse_sms(message)

        assert len(result['phone_numbers']) >= 1
        assert 'phone_numbers' in result

    def test_parse_multipart_detection(self):
        """Test multipart SMS detection (>160 chars)."""
        short_message = "Short message"
        long_message = "x" * 161

        short_result = parse_sms(short_message)
        long_result = parse_sms(long_message)

        assert short_result['is_multipart'] is False
        assert long_result['is_multipart'] is True

    def test_parse_empty_message(self):
        """Test parsing empty message doesn't crash."""
        result = parse_sms("")

        assert result['text'] == ''
        assert result['urls'] == []
        assert result['phone_numbers'] == []
        assert result['is_multipart'] is False


# Test extract_sms_features() function
class TestExtractSmsFeatures:
    """Tests for extract_sms_features() function."""

    def test_shortened_url_detection(self, smishing_text):
        """Test shortened URL detection (bit.ly, tinyurl, etc.)."""
        features = extract_sms_features(smishing_text)

        assert features['has_shortened_url'] == 1
        assert features['shortened_url_count'] >= 1
        assert features['url_count'] >= 1

    def test_segment_count(self, long_sms):
        """Test SMS segment count calculation."""
        features = extract_sms_features(long_sms)

        # 160+ chars should be at least 2 segments
        assert features['sms_segment_count'] >= 2
        assert features['exceeds_single_sms'] == 1

    def test_urgency_caps_detection(self):
        """Test urgency keywords in CAPS detection."""
        urgent_msg = "URGENT: Your account will be closed"
        normal_msg = "Your order has shipped"

        urgent_features = extract_sms_features(urgent_msg)
        normal_features = extract_sms_features(normal_msg)

        assert urgent_features['has_urgency_caps'] == 1
        assert normal_features['has_urgency_caps'] == 0

    def test_prize_claim_detection(self, prize_scam):
        """Test prize/claim pattern detection."""
        features = extract_sms_features(prize_scam)

        assert features['has_prize_claim'] == 1

    def test_phone_number_detection(self, prize_scam):
        """Test phone number detection."""
        features = extract_sms_features(prize_scam)

        assert features['has_phone_number'] == 1
        assert features['phone_number_count'] >= 1

    def test_emoji_detection(self, emoji_sms):
        """Test emoji detection and counting."""
        features = extract_sms_features(emoji_sms)

        assert features['has_emoji'] == 1
        assert features['emoji_count'] >= 2  # 📦🎉

    def test_uppercase_word_count(self):
        """Test ALL CAPS word counting."""
        message = "URGENT WARNING: Your account SUSPENDED"
        features = extract_sms_features(message)

        assert features['uppercase_word_count'] >= 2  # URGENT, WARNING, SUSPENDED

    def test_account_alert_detection(self, smishing_text):
        """Test account security alert pattern detection."""
        features = extract_sms_features(smishing_text)

        assert features['has_account_alert'] == 1

    def test_call_to_action_detection(self):
        """Test call-to-action keyword detection."""
        cta_msg = "Click here to verify your account"
        no_cta_msg = "Your package has arrived"

        cta_features = extract_sms_features(cta_msg)
        no_cta_features = extract_sms_features(no_cta_msg)

        assert cta_features['has_call_to_action'] == 1
        assert no_cta_features['has_call_to_action'] == 0

    def test_shorthand_ratio(self):
        """Test SMS shorthand detection."""
        shorthand_msg = "hey u plz txt me asap thx"
        normal_msg = "Hello, could you please text me as soon as possible? Thank you."

        shorthand_features = extract_sms_features(shorthand_msg)
        normal_features = extract_sms_features(normal_msg)

        assert shorthand_features['shorthand_ratio'] > 0
        assert normal_features['shorthand_ratio'] == 0

    def test_numeric_string_count(self):
        """Test numeric sequence detection (codes, PINs, amounts)."""
        message = "Your PIN is 1234 and amount is 5678"
        features = extract_sms_features(message)

        assert features['numeric_string_count'] >= 2  # 1234, 5678


# Test defaults and edge cases
class TestDefaults:
    """Tests for default values and edge cases."""

    def test_empty_sms_defaults(self, empty_sms):
        """Test all features are zero for empty message."""
        features = extract_sms_features(empty_sms)

        assert len(features) == 20
        assert features['sms_length'] == 0
        assert features['url_count'] == 0
        assert features['has_emoji'] == 0

    def test_whitespace_only(self, whitespace_only):
        """Test whitespace-only message treated as empty."""
        features = extract_sms_features(whitespace_only)

        assert len(features) == 20
        assert all(v == 0 or v == 0.0 for v in features.values())


# Test integration and consistency
class TestIntegration:
    """Integration tests for SMS feature extraction."""

    def test_feature_count_consistent(self, smishing_text, legitimate_sms, prize_scam):
        """Test all messages return same number of features."""
        smishing_features = extract_sms_features(smishing_text)
        legitimate_features = extract_sms_features(legitimate_sms)
        prize_features = extract_sms_features(prize_scam)

        assert len(smishing_features) == 20
        assert len(legitimate_features) == 20
        assert len(prize_features) == 20

    def test_all_features_numeric(self, smishing_text):
        """Test all feature values are numeric (int or float)."""
        features = extract_sms_features(smishing_text)

        for key, value in features.items():
            assert isinstance(value, (int, float)), f"Feature {key} is not numeric: {type(value)}"

    def test_url_to_text_ratio(self):
        """Test URL to text ratio calculation."""
        short_msg = "bit.ly/abc"
        long_msg = "Please visit our website at bit.ly/abc for more information about our amazing products"

        short_features = extract_sms_features(short_msg)
        long_features = extract_sms_features(long_msg)

        # Ratio should be higher for message with mostly URL
        assert short_features['url_to_text_ratio'] > long_features['url_to_text_ratio']

    def test_char_per_word_avg(self):
        """Test average characters per word calculation."""
        short_words = "a b c d"
        long_words = "extraordinary magnificent"

        short_features = extract_sms_features(short_words)
        long_features = extract_sms_features(long_words)

        assert short_features['char_per_word_avg'] < long_features['char_per_word_avg']

    def test_exclamation_density(self):
        """Test exclamation density calculation."""
        excited = "Wow! Amazing! Incredible!"
        calm = "Your order has been processed"

        excited_features = extract_sms_features(excited)
        calm_features = extract_sms_features(calm)

        assert excited_features['exclamation_density'] > calm_features['exclamation_density']


# Test shortened URL domain detection
class TestShortenedUrls:
    """Tests for shortened URL detection."""

    def test_all_shortened_domains_detected(self):
        """Test all shortened URL domains are properly detected."""
        for domain in list(SHORTENED_URL_DOMAINS)[:5]:  # Test subset
            message = f"Click {domain}/test123"
            features = extract_sms_features(message)

            assert features['has_shortened_url'] == 1, f"Failed to detect {domain}"

    def test_regular_url_not_shortened(self):
        """Test regular URLs not flagged as shortened."""
        message = "Visit https://www.google.com/search"
        features = extract_sms_features(message)

        assert features['has_shortened_url'] == 0
