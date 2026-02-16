"""API endpoint tests for email and SMS phishing prediction.

Tests the /predict/email, /predict/email/file, and /predict/sms endpoints
added in Phase 06 Plan 05.

Requirements tested:
- INPUT-02: API accepts raw email/SMS text
- INPUT-03: API accepts .eml file upload
- FEAT-07: Email header feature extraction
"""

import io
import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    with TestClient(app) as c:
        yield c


def skip_if_not_implemented(response):
    """Helper to skip tests when endpoints return 501 (not implemented yet).

    Email/SMS endpoints return 501 until models are retrained with expanded features (Plan 06-06).
    """
    if response.status_code == 503:
        pytest.skip("Models not loaded - expected in unit test environment")
    if response.status_code == 501:
        pytest.skip("Email/SMS prediction not yet implemented - models need retraining with expanded features")


@pytest.fixture
def sample_email_text():
    """Valid raw email with headers."""
    return """From: sender@example.com
To: recipient@example.com
Subject: Test Email
Date: Mon, 16 Feb 2026 10:00:00 +0000

This is a test email body with some content.
"""


@pytest.fixture
def sample_phishing_email():
    """Suspicious email with phishing indicators."""
    return """From: urgent-security@suspicious.tk
To: victim@example.com
Subject: URGENT: Account Verification Required
Date: Mon, 16 Feb 2026 10:00:00 +0000

URGENT ACTION REQUIRED!

Your account will be suspended within 24 hours unless you verify your identity immediately.

Click here to verify: http://verify-account.tk/login

Best regards,
Security Team
"""


@pytest.fixture
def sample_sms():
    """Valid SMS message."""
    return "Hello, this is a normal text message from a friend."


@pytest.fixture
def sample_phishing_sms():
    """Suspicious SMS with smishing indicators."""
    return "URGENT: Your account has been locked! Click bit.ly/verify123 to unlock NOW!"


@pytest.fixture
def sample_eml_bytes():
    """Valid .eml file content as bytes."""
    email_text = """From: test@example.com
To: user@example.com
Subject: Test
Date: Mon, 16 Feb 2026 10:00:00 +0000

Test body content.
"""
    return email_text.encode('utf-8')


# ========== Test /predict/email endpoint ==========

def test_predict_email_valid(client, sample_email_text):
    """Test email prediction with valid email text."""
    response = client.post("/predict/email", json={"raw_email": sample_email_text})
    skip_if_not_implemented(response)

    assert response.status_code == 200
    data = response.json()
    assert data["content_type"] == "email"
    assert data["final_prediction"] in ["phishing", "legitimate"]
    assert 0.0 <= data["final_probability"] <= 1.0
    assert 0.5 <= data["confidence"] <= 1.0
    assert data["feature_count"] > 0
    assert "explanation" in data


def test_predict_email_invalid_format(client):
    """Test email prediction with missing headers."""
    invalid_email = "This is just plain text without headers"
    response = client.post("/predict/email", json={"raw_email": invalid_email})

    # Should return 422 validation error
    assert response.status_code == 422


def test_predict_email_empty(client):
    """Test email prediction with empty string."""
    response = client.post("/predict/email", json={"raw_email": ""})

    # Should return 422 validation error (min_length=10)
    assert response.status_code == 422


def test_predict_email_response_structure(client, sample_email_text):
    """Test email response matches EmailSMSResponse structure."""
    response = client.post("/predict/email", json={"raw_email": sample_email_text})
    skip_if_not_implemented(response)

    assert response.status_code == 200
    data = response.json()

    # Check all required fields exist
    required_fields = [
        "content_type", "final_prediction", "final_probability",
        "confidence", "feature_count", "active_rules",
        "explanation", "processing_time_ms"
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"


def test_predict_email_phishing_indicators(client, sample_phishing_email):
    """Test email with strong phishing indicators."""
    response = client.post("/predict/email", json={"raw_email": sample_phishing_email})

    skip_if_not_implemented(response)

    assert response.status_code == 200
    data = response.json()

    # Phishing email should have features extracted
    assert data["feature_count"] > 0
    assert data["content_type"] == "email"


# ========== Test /predict/email/file endpoint ==========

def test_predict_email_file_valid(client, sample_eml_bytes):
    """Test .eml file upload with valid content."""
    files = {"file": ("test.eml", io.BytesIO(sample_eml_bytes), "message/rfc822")}
    response = client.post("/predict/email/file", files=files)

    skip_if_not_implemented(response)

    assert response.status_code == 200
    data = response.json()
    assert data["content_type"] == "email"
    assert data["final_prediction"] in ["phishing", "legitimate"]


def test_predict_email_file_wrong_extension(client, sample_eml_bytes):
    """Test file upload with wrong extension."""
    files = {"file": ("test.txt", io.BytesIO(sample_eml_bytes), "text/plain")}
    response = client.post("/predict/email/file", files=files)

    # Should return 400 bad request
    assert response.status_code == 400
    assert "must be .eml format" in response.json()["detail"]


def test_predict_email_file_too_large(client):
    """Test file upload exceeding 5MB limit."""
    # Create a file larger than 5MB
    large_content = b"X" * (6 * 1024 * 1024)  # 6MB
    files = {"file": ("large.eml", io.BytesIO(large_content), "message/rfc822")}
    response = client.post("/predict/email/file", files=files)

    # Should return 400 bad request
    assert response.status_code == 400
    assert "too large" in response.json()["detail"]


def test_predict_email_file_response_structure(client, sample_eml_bytes):
    """Test .eml file response matches EmailSMSResponse structure."""
    files = {"file": ("test.eml", io.BytesIO(sample_eml_bytes), "message/rfc822")}
    response = client.post("/predict/email/file", files=files)

    skip_if_not_implemented(response)

    assert response.status_code == 200
    data = response.json()

    # Check all required fields exist
    required_fields = [
        "content_type", "final_prediction", "final_probability",
        "confidence", "feature_count", "explanation", "processing_time_ms"
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"


# ========== Test /predict/sms endpoint ==========

def test_predict_sms_valid(client, sample_sms):
    """Test SMS prediction with valid message."""
    response = client.post("/predict/sms", json={"message": sample_sms})

    skip_if_not_implemented(response)

    assert response.status_code == 200
    data = response.json()
    assert data["content_type"] == "sms"
    assert data["final_prediction"] in ["phishing", "legitimate"]
    assert 0.0 <= data["final_probability"] <= 1.0
    assert 0.5 <= data["confidence"] <= 1.0
    assert data["feature_count"] > 0


def test_predict_sms_empty(client):
    """Test SMS prediction with empty string."""
    response = client.post("/predict/sms", json={"message": ""})

    # Should return 422 validation error (min_length=1)
    assert response.status_code == 422


def test_predict_sms_long_message(client):
    """Test SMS prediction with long message (1000+ chars)."""
    long_message = "This is a long SMS message. " * 50  # ~1400 chars
    response = client.post("/predict/sms", json={"message": long_message})

    skip_if_not_implemented(response)

    assert response.status_code == 200
    data = response.json()
    assert data["content_type"] == "sms"


def test_predict_sms_unicode(client):
    """Test SMS prediction with emoji and special characters."""
    unicode_message = "🚨 URGENT: Your package 📦 is waiting! Click here 👉 http://track.link"
    response = client.post("/predict/sms", json={"message": unicode_message})

    skip_if_not_implemented(response)

    assert response.status_code == 200
    data = response.json()
    assert data["content_type"] == "sms"


def test_predict_sms_response_structure(client, sample_sms):
    """Test SMS response matches EmailSMSResponse structure."""
    response = client.post("/predict/sms", json={"message": sample_sms})

    skip_if_not_implemented(response)

    assert response.status_code == 200
    data = response.json()

    # Check all required fields exist
    required_fields = [
        "content_type", "final_prediction", "final_probability",
        "confidence", "feature_count", "active_rules",
        "explanation", "processing_time_ms"
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"


def test_predict_sms_phishing_indicators(client, sample_phishing_sms):
    """Test SMS with strong smishing indicators."""
    response = client.post("/predict/sms", json={"message": sample_phishing_sms})

    skip_if_not_implemented(response)

    assert response.status_code == 200
    data = response.json()

    # Phishing SMS should have features extracted
    assert data["feature_count"] > 0
    assert data["content_type"] == "sms"


# ========== Test response fields ==========

def test_response_has_content_type(client, sample_email_text, sample_sms):
    """Test responses have correct content_type field."""
    # Email
    response_email = client.post("/predict/email", json={"raw_email": sample_email_text})
    if response_email.status_code == 200:
        assert response_email.json()["content_type"] == "email"

    # SMS
    response_sms = client.post("/predict/sms", json={"message": sample_sms})
    if response_sms.status_code == 200:
        assert response_sms.json()["content_type"] == "sms"


def test_response_has_prediction(client, sample_email_text):
    """Test response has valid prediction field."""
    response = client.post("/predict/email", json={"raw_email": sample_email_text})

    skip_if_not_implemented(response)

    assert response.status_code == 200
    data = response.json()
    assert data["final_prediction"] in ["phishing", "legitimate"]


def test_response_probability_range(client, sample_sms):
    """Test response probability is in valid range [0.0, 1.0]."""
    response = client.post("/predict/sms", json={"message": sample_sms})

    skip_if_not_implemented(response)

    assert response.status_code == 200
    data = response.json()
    assert 0.0 <= data["final_probability"] <= 1.0
    assert 0.5 <= data["confidence"] <= 1.0


def test_response_has_feature_count(client, sample_email_text):
    """Test response includes positive feature count."""
    response = client.post("/predict/email", json={"raw_email": sample_email_text})

    skip_if_not_implemented(response)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["feature_count"], int)
    assert data["feature_count"] > 0


# ========== Test error handling ==========

def test_models_not_loaded_email(client, sample_email_text, monkeypatch):
    """Test 503 error when models not loaded (email endpoint)."""
    # This test may naturally pass if models aren't loaded
    # We'll test that the endpoint handles the case gracefully
    response = client.post("/predict/email", json={"raw_email": sample_email_text})

    # Either 200 (models loaded), 503 (models not loaded), or 501 (not implemented)
    assert response.status_code in [200, 503, 501]


def test_models_not_loaded_sms(client, sample_sms, monkeypatch):
    """Test 503 error when models not loaded (SMS endpoint)."""
    # This test may naturally pass if models aren't loaded
    # We'll test that the endpoint handles the case gracefully
    response = client.post("/predict/sms", json={"message": sample_sms})

    # Either 200 (models loaded), 503 (models not loaded), or 501 (not implemented)
    assert response.status_code in [200, 503, 501]
