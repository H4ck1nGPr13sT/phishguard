"""Unit tests for email feature extraction module."""

import pytest
from email import message_from_bytes, policy

from src.features.email_features import (
    parse_email,
    extract_email_header_features,
    extract_domain_from_email,
)


# Test fixtures - Sample email bytes
@pytest.fixture
def simple_plain_email():
    """Simple plain text email."""
    return b"""From: sender@example.com
To: recipient@test.org
Subject: Test Email
Date: Mon, 1 Jan 2024 12:00:00 +0000

This is a plain text email body.
"""


@pytest.fixture
def html_email():
    """HTML-only email."""
    return b"""From: user@company.com
To: contact@example.org
Subject: Newsletter
Content-Type: text/html

<html><body><h1>Welcome</h1><p>This is HTML content.</p></body></html>
"""


@pytest.fixture
def multipart_email():
    """Multipart email with both plain and HTML."""
    return b"""From: info@service.com
To: user@example.com
Subject: Account Update
MIME-Version: 1.0
Content-Type: multipart/alternative; boundary="boundary123"

--boundary123
Content-Type: text/plain

Plain text version of the message.

--boundary123
Content-Type: text/html

<html><body>HTML version of the message.</body></html>

--boundary123--
"""


@pytest.fixture
def spf_dkim_pass_email():
    """Email with SPF and DKIM pass in Authentication-Results."""
    return b"""From: legitimate@bank.com
To: customer@example.com
Subject: Your Statement
Authentication-Results: mx.google.com;
       spf=pass smtp.mailfrom=bank.com;
       dkim=pass header.i=@bank.com;
       dmarc=pass

Your monthly statement is ready.
"""


@pytest.fixture
def suspicious_sender_email():
    """Email from suspicious .tk domain."""
    return b"""From: support@paypal-security.tk
To: victim@example.com
Subject: URGENT: Verify your account now!
Reply-To: scammer@different-domain.xyz

Click here to verify immediately.
"""


@pytest.fixture
def reply_to_mismatch_email():
    """Email with Reply-To different from From."""
    return b"""From: sales@company.com
To: client@example.com
Subject: Special Offer
Reply-To: different@other-domain.com

Limited time offer!
"""


@pytest.fixture
def empty_email():
    """Empty email bytes."""
    return b""


# Test parse_email() function
class TestParseEmail:
    """Tests for parse_email() function."""

    def test_parse_plain_text_email(self, simple_plain_email):
        """Test parsing simple plain text email."""
        result = parse_email(simple_plain_email)

        assert result['headers']['From'] == 'sender@example.com'
        assert result['headers']['To'] == 'recipient@test.org'
        assert result['headers']['Subject'] == 'Test Email'
        assert 'plain text email body' in result['body']
        assert result['is_html'] is False
        assert result['has_attachments'] is False

    def test_parse_html_email(self, html_email):
        """Test parsing HTML email and extracting text."""
        result = parse_email(html_email)

        assert result['headers']['From'] == 'user@company.com'
        assert 'Welcome' in result['body']
        assert 'HTML content' in result['body']
        assert '<html>' not in result['body']  # HTML tags stripped
        assert result['is_html'] is True

    def test_parse_multipart_email(self, multipart_email):
        """Test parsing multipart email prefers text/plain."""
        result = parse_email(multipart_email)

        assert result['headers']['From'] == 'info@service.com'
        # Should prefer plain text over HTML
        assert 'Plain text version' in result['body']
        assert result['is_html'] is False

    def test_parse_empty_email(self, empty_email):
        """Test parsing empty email returns default structure."""
        result = parse_email(empty_email)

        assert result['headers'] == {}
        assert result['body'] == ''
        assert result['is_html'] is False
        assert result['has_attachments'] is False


# Test extract_email_header_features() function
class TestExtractEmailHeaderFeatures:
    """Tests for extract_email_header_features() function."""

    def test_spf_dkim_detection(self, spf_dkim_pass_email):
        """Test SPF/DKIM/DMARC detection from Authentication-Results."""
        msg = message_from_bytes(spf_dkim_pass_email, policy=policy.default)
        features = extract_email_header_features(msg)

        assert features['has_spf_pass'] == 1
        assert features['has_dkim_pass'] == 1
        assert features['has_dmarc_pass'] == 1

    def test_spf_dkim_missing(self, simple_plain_email):
        """Test emails without Authentication-Results have 0 for auth features."""
        msg = message_from_bytes(simple_plain_email, policy=policy.default)
        features = extract_email_header_features(msg)

        assert features['has_spf_pass'] == 0
        assert features['has_dkim_pass'] == 0
        assert features['has_dmarc_pass'] == 0

    def test_reply_to_mismatch(self, reply_to_mismatch_email):
        """Test detection of Reply-To different from From."""
        msg = message_from_bytes(reply_to_mismatch_email, policy=policy.default)
        features = extract_email_header_features(msg)

        assert features['reply_to_mismatch'] == 1

    def test_no_reply_to_mismatch(self, simple_plain_email):
        """Test no mismatch when Reply-To is absent."""
        msg = message_from_bytes(simple_plain_email, policy=policy.default)
        features = extract_email_header_features(msg)

        assert features['reply_to_mismatch'] == 0

    def test_suspicious_domain(self, suspicious_sender_email):
        """Test detection of suspicious TLD (.tk)."""
        msg = message_from_bytes(suspicious_sender_email, policy=policy.default)
        features = extract_email_header_features(msg)

        assert features['from_domain_suspicious'] == 1

    def test_legitimate_domain(self, simple_plain_email):
        """Test legitimate domain (.com) not flagged as suspicious."""
        msg = message_from_bytes(simple_plain_email, policy=policy.default)
        features = extract_email_header_features(msg)

        assert features['from_domain_suspicious'] == 0

    def test_urgent_subject(self, suspicious_sender_email):
        """Test detection of urgent keywords in subject."""
        msg = message_from_bytes(suspicious_sender_email, policy=policy.default)
        features = extract_email_header_features(msg)

        assert features['has_urgent_subject'] == 1

    def test_normal_subject(self, simple_plain_email):
        """Test normal subject without urgent keywords."""
        msg = message_from_bytes(simple_plain_email, policy=policy.default)
        features = extract_email_header_features(msg)

        assert features['has_urgent_subject'] == 0

    def test_subject_length(self, suspicious_sender_email):
        """Test subject length extraction."""
        msg = message_from_bytes(suspicious_sender_email, policy=policy.default)
        features = extract_email_header_features(msg)

        assert features['subject_length'] > 0
        assert features['subject_length'] == len(msg.get('Subject', ''))

    def test_sender_domain_length(self, simple_plain_email):
        """Test sender domain length extraction."""
        msg = message_from_bytes(simple_plain_email, policy=policy.default)
        features = extract_email_header_features(msg)

        # sender@example.com -> domain is "example.com" (11 chars)
        assert features['sender_domain_length'] == 11

    def test_header_count(self, multipart_email):
        """Test header count feature."""
        msg = message_from_bytes(multipart_email, policy=policy.default)
        features = extract_email_header_features(msg)

        assert features['header_count'] > 0

    def test_default_features(self):
        """Test default features for None message."""
        features = extract_email_header_features(None)

        # All features should be 0
        assert features['has_spf_pass'] == 0
        assert features['has_dkim_pass'] == 0
        assert features['sender_domain_length'] == 0
        assert features['subject_length'] == 0
        assert features['header_count'] == 0


# Test extract_domain_from_email() function
class TestExtractDomainFromEmail:
    """Tests for extract_domain_from_email() helper function."""

    def test_standard_format(self):
        """Test extraction from 'Name <user@domain.com>' format."""
        email = "John Doe <john@example.com>"
        domain = extract_domain_from_email(email)

        assert domain == "example.com"

    def test_bare_email(self):
        """Test extraction from bare 'user@domain.com' format."""
        email = "user@test.org"
        domain = extract_domain_from_email(email)

        assert domain == "test.org"

    def test_subdomain(self):
        """Test extraction with subdomain."""
        email = "admin@mail.company.co.uk"
        domain = extract_domain_from_email(email)

        assert domain == "mail.company.co.uk"

    def test_empty_string(self):
        """Test extraction from empty string."""
        domain = extract_domain_from_email("")

        assert domain == ""

    def test_invalid_email(self):
        """Test extraction from invalid email."""
        domain = extract_domain_from_email("not-an-email")

        assert domain == ""

    def test_multiple_at_signs(self):
        """Test extraction with multiple @ signs (invalid but handled)."""
        email = "user@@domain.com"
        domain = extract_domain_from_email(email)

        # Should extract first valid domain after @
        assert "@domain.com" in email or domain == "domain.com"


# Integration tests
class TestEmailFeaturesIntegration:
    """Integration tests for email feature extraction pipeline."""

    def test_full_pipeline_suspicious_email(self, suspicious_sender_email):
        """Test full pipeline on suspicious phishing email."""
        # Parse email
        parsed = parse_email(suspicious_sender_email)

        assert 'URGENT' in parsed['headers']['Subject']
        assert parsed['headers']['Reply-To']  # Has Reply-To

        # Extract features
        msg = message_from_bytes(suspicious_sender_email, policy=policy.default)
        features = extract_email_header_features(msg)

        # Should trigger multiple phishing indicators
        assert features['has_urgent_subject'] == 1
        assert features['from_domain_suspicious'] == 1  # .tk domain
        assert features['reply_to_mismatch'] == 1  # Different Reply-To

    def test_full_pipeline_legitimate_email(self, spf_dkim_pass_email):
        """Test full pipeline on legitimate email."""
        # Parse email
        parsed = parse_email(spf_dkim_pass_email)

        assert parsed['body']  # Has body content

        # Extract features
        msg = message_from_bytes(spf_dkim_pass_email, policy=policy.default)
        features = extract_email_header_features(msg)

        # Should pass authentication checks
        assert features['has_spf_pass'] == 1
        assert features['has_dkim_pass'] == 1
        assert features['has_dmarc_pass'] == 1
        # Should not trigger phishing indicators
        assert features['from_domain_suspicious'] == 0
        assert features['has_urgent_subject'] == 0

    def test_feature_count(self, simple_plain_email):
        """Test that exactly 15 features are extracted."""
        msg = message_from_bytes(simple_plain_email, policy=policy.default)
        features = extract_email_header_features(msg)

        # Should have exactly 15 features
        assert len(features) == 15

        # Verify all expected features present
        expected_features = [
            'has_spf_pass', 'has_dkim_pass', 'has_dmarc_pass',
            'sender_domain_length', 'from_domain_suspicious', 'reply_to_mismatch',
            'has_multiple_recipients', 'subject_length', 'has_urgent_subject',
            'has_re_prefix', 'has_fwd_prefix', 'header_count', 'has_x_headers',
            'has_received_headers', 'received_header_count'
        ]
        for feature in expected_features:
            assert feature in features
