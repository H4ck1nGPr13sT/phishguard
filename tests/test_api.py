"""API endpoint tests with latency verification.

Tests cover:
- Root endpoint
- Health endpoint
- Prediction endpoint
- URL validation
- Error handling
- Latency requirements (<500ms)
- OpenAPI schema
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import numpy as np
import time


@pytest.fixture
def mock_model():
    """Create mock model that returns predictable probabilities."""
    model = MagicMock()
    model.predict_proba.return_value = np.array([[0.3, 0.7]])  # 70% phishing
    return model


@pytest.fixture
def client(mock_model):
    """Create test client with mocked model."""
    from src.api.main import app, ml_models

    ml_models["phishing_detector"] = mock_model
    return TestClient(app)


class TestRootEndpoint:
    """Test root endpoint."""

    def test_root_returns_200(self, client):
        """Test GET / returns 200 with service info."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_contains_service_info(self, client):
        """Test response contains service name and version."""
        response = client.get("/")
        data = response.json()
        assert data["service"] == "PhishGuard API"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data
        assert "/predict" in data["endpoints"]


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_returns_200_when_model_loaded(self, client):
        """Test GET /health returns 200 when model loaded."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_model_loaded_true(self, client):
        """Test response has model_loaded=True when model exists."""
        response = client.get("/health")
        data = response.json()
        assert data["model_loaded"] is True
        assert data["status"] == "healthy"

    def test_health_model_loaded_false_when_model_missing(self):
        """Test response has model_loaded=False when model not loaded."""
        from src.api.main import app, ml_models

        ml_models.clear()  # Remove model
        client = TestClient(app)
        response = client.get("/health")
        data = response.json()
        assert data["model_loaded"] is False
        assert data["status"] == "unhealthy"


class TestPredictEndpoint:
    """Test prediction endpoint."""

    def test_predict_returns_200_with_valid_url(self, client):
        """Test POST /predict with valid URL returns 200."""
        response = client.post("/predict", json={"url": "https://example.com"})
        assert response.status_code == 200

    def test_predict_response_structure(self, client):
        """Test response contains required fields."""
        response = client.post("/predict", json={"url": "https://example.com"})
        data = response.json()
        assert "url" in data
        assert "phishing_probability" in data
        assert "prediction" in data
        assert "confidence" in data
        assert "processing_time_ms" in data

    def test_predict_probability_in_range(self, client):
        """Test phishing_probability is between 0.0 and 1.0."""
        response = client.post("/predict", json={"url": "https://example.com"})
        data = response.json()
        assert 0.0 <= data["phishing_probability"] <= 1.0

    def test_predict_prediction_valid(self, client):
        """Test prediction is 'phishing' or 'legitimate'."""
        response = client.post("/predict", json={"url": "https://example.com"})
        data = response.json()
        assert data["prediction"] in ["phishing", "legitimate"]

    def test_predict_processing_time_positive(self, client):
        """Test processing_time_ms is positive number."""
        response = client.post("/predict", json={"url": "https://example.com"})
        data = response.json()
        assert data["processing_time_ms"] > 0

    def test_predict_phishing_url_high_probability(self, client):
        """Test phishing URL returns high probability (mock returns 0.7)."""
        response = client.post("/predict", json={"url": "http://suspicious.tk"})
        data = response.json()
        assert data["phishing_probability"] == 0.7
        assert data["prediction"] == "phishing"

    def test_predict_returns_correct_url(self, client):
        """Test response contains the URL that was analyzed."""
        test_url = "https://test-domain.com"
        response = client.post("/predict", json={"url": test_url})
        data = response.json()
        assert data["url"] == test_url


class TestURLValidation:
    """Test URL validation logic."""

    def test_url_without_protocol_rejected(self, client):
        """Test URL without http/https returns 422."""
        response = client.post("/predict", json={"url": "example.com"})
        assert response.status_code == 422

    def test_url_too_short_rejected(self, client):
        """Test URL too short (<10 chars) returns 422."""
        response = client.post("/predict", json={"url": "http://a"})
        assert response.status_code == 422

    def test_url_too_long_rejected(self, client):
        """Test URL too long (>2048 chars) returns 422."""
        long_url = "https://" + "a" * 2050
        response = client.post("/predict", json={"url": long_url})
        assert response.status_code == 422

    def test_http_url_accepted(self, client):
        """Test valid HTTP URL accepted."""
        response = client.post("/predict", json={"url": "http://example.com"})
        assert response.status_code == 200

    def test_https_url_accepted(self, client):
        """Test valid HTTPS URL accepted."""
        response = client.post("/predict", json={"url": "https://example.com"})
        assert response.status_code == 200


class TestErrorHandling:
    """Test error handling."""

    def test_predict_without_model_returns_503(self):
        """Test prediction with model not loaded returns 503."""
        from src.api.main import app, ml_models

        ml_models.clear()  # Remove model
        client = TestClient(app)
        response = client.post("/predict", json={"url": "https://example.com"})
        assert response.status_code == 503
        assert "Service unavailable" in response.json()["detail"]

    def test_malformed_request_body_returns_422(self, client):
        """Test malformed request body returns 422."""
        response = client.post("/predict", json={"invalid_field": "value"})
        assert response.status_code == 422

    def test_empty_request_body_returns_422(self, client):
        """Test empty request body returns 422."""
        response = client.post("/predict", json={})
        assert response.status_code == 422


class TestLatency:
    """Test latency requirements."""

    def test_prediction_latency_under_500ms(self, client):
        """Test actual prediction completes in <500ms (with mock model)."""
        start = time.time()
        response = client.post("/predict", json={"url": "https://example.com"})
        duration_ms = (time.time() - start) * 1000

        assert response.status_code == 200
        assert duration_ms < 500, f"Prediction took {duration_ms:.2f}ms (>500ms)"

    def test_processing_time_reported_accurately(self, client):
        """Test processing_time_ms is accurate."""
        response = client.post("/predict", json={"url": "https://example.com"})
        data = response.json()

        # Reported time should be reasonable (less than total request time)
        assert 0 < data["processing_time_ms"] < 500


class TestOpenAPI:
    """Test OpenAPI/Swagger documentation."""

    def test_docs_endpoint_returns_200(self, client):
        """Test GET /docs returns 200 (Swagger UI)."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_schema_valid(self, client):
        """Test GET /openapi.json returns valid schema."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert schema["info"]["title"] == "PhishGuard API"
        assert "paths" in schema
        assert "/predict" in schema["paths"]
        assert "/health" in schema["paths"]
