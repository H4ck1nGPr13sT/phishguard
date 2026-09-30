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
def mock_voting_ensemble():
    """Create mock voting ensemble with individual classifiers."""
    ensemble = MagicMock()
    ensemble.predict_proba.return_value = np.array([[0.3, 0.7]])  # 70% phishing

    # Mock named_estimators_ for get_individual_predictions
    mock_estimators = {}
    classifier_names = ['rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt']
    probabilities = [0.9, 0.85, 0.8, 0.75, 0.7, 0.3, 0.2]  # Varied predictions

    for name, prob in zip(classifier_names, probabilities):
        mock_est = MagicMock()
        mock_est.predict_proba.return_value = np.array([[1 - prob, prob]])
        mock_estimators[name] = mock_est

    ensemble.named_estimators_ = mock_estimators
    return ensemble


@pytest.fixture
def client(mock_model):
    """Create test client with mocked model."""
    from src.api.main import app, ml_models

    ml_models["phishing_detector"] = mock_model
    return TestClient(app)


@pytest.fixture
def client_with_ensemble(mock_model, mock_voting_ensemble):
    """Create test client with mocked ensemble models."""
    from src.api.main import app, ml_models

    ml_models["phishing_detector"] = mock_model
    ml_models["voting_soft"] = mock_voting_ensemble
    return TestClient(app)


class TestRootEndpoint:
    """Test root endpoint.

    Phase 8: GET / now serves the HTML web UI (src/api/web.py); the JSON
    service-info payload previously at GET / moved to GET /api/info.
    """

    def test_root_returns_200(self, client):
        """Test GET /api/info returns 200 with service info."""
        response = client.get("/api/info")
        assert response.status_code == 200

    def test_root_contains_service_info(self, client):
        """Test response contains service name and version."""
        response = client.get("/api/info")
        data = response.json()
        assert data["service"] == "PhishGuard API"
        assert data["version"] == "4.0.0"  # Phase 7: Image/OCR support
        assert "endpoints" in data
        assert "/predict" in data["endpoints"]

    def test_root_serves_html(self, client):
        """Test GET / returns the HTML web UI, not JSON."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")


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


class TestEnsemblePredictEndpoint:
    """Test ensemble prediction endpoint."""

    def test_predict_ensemble_endpoint_exists(self, client_with_ensemble):
        """Test POST /predict/ensemble returns 200."""
        response = client_with_ensemble.post(
            "/predict/ensemble", json={"url": "https://example.com"}
        )
        assert response.status_code == 200

    def test_predict_ensemble_returns_all_classifiers(self, client_with_ensemble):
        """Test response has 7 individual_predictions."""
        response = client_with_ensemble.post(
            "/predict/ensemble", json={"url": "https://example.com"}
        )
        data = response.json()
        assert "individual_predictions" in data
        assert len(data["individual_predictions"]) == 7

        # Verify classifier names
        classifier_names = {pred["name"] for pred in data["individual_predictions"]}
        expected_names = {"rf", "svm", "mlp", "xgb", "lr", "nb", "dt"}
        assert classifier_names == expected_names

    def test_predict_ensemble_has_disagreement(self, client_with_ensemble):
        """Test response includes disagreement field."""
        response = client_with_ensemble.post(
            "/predict/ensemble", json={"url": "https://example.com"}
        )
        data = response.json()
        assert "disagreement" in data

        # Check disagreement structure
        disagreement = data["disagreement"]
        assert "score" in disagreement
        assert "is_edge_case" in disagreement
        assert "vote_distribution" in disagreement
        assert "agreeing_classifiers" in disagreement
        assert "dissenting_classifiers" in disagreement

    def test_predict_ensemble_response_structure(self, client_with_ensemble):
        """Test response contains all required fields."""
        response = client_with_ensemble.post(
            "/predict/ensemble", json={"url": "https://example.com"}
        )
        data = response.json()

        # Check all required fields
        assert "url" in data
        assert "ensemble_prediction" in data
        assert "ensemble_probability" in data
        assert "ensemble_confidence" in data
        assert "individual_predictions" in data
        assert "disagreement" in data
        assert "voting_method" in data
        assert "processing_time_ms" in data

    def test_predict_ensemble_latency(self, client_with_ensemble):
        """Test response time <500ms."""
        start = time.time()
        response = client_with_ensemble.post(
            "/predict/ensemble", json={"url": "https://example.com"}
        )
        duration_ms = (time.time() - start) * 1000

        assert response.status_code == 200
        assert duration_ms < 500, f"Ensemble prediction took {duration_ms:.2f}ms (>500ms)"

        # Verify reported processing time is reasonable
        data = response.json()
        assert 0 < data["processing_time_ms"] < 500

    def test_predict_ensemble_invalid_url(self, client_with_ensemble):
        """Test returns 422 for invalid URL."""
        response = client_with_ensemble.post(
            "/predict/ensemble", json={"url": "invalid-url"}
        )
        assert response.status_code == 422

    def test_predict_ensemble_model_not_loaded(self):
        """Test returns 503 if ensemble not loaded."""
        from src.api.main import app, ml_models

        ml_models.clear()  # Remove all models
        client = TestClient(app)
        response = client.post(
            "/predict/ensemble", json={"url": "https://example.com"}
        )
        assert response.status_code == 503
        assert "Ensemble models not loaded" in response.json()["detail"]

    def test_predict_ensemble_classifier_result_structure(self, client_with_ensemble):
        """Test each classifier result has correct structure."""
        response = client_with_ensemble.post(
            "/predict/ensemble", json={"url": "https://example.com"}
        )
        data = response.json()

        for pred in data["individual_predictions"]:
            assert "name" in pred
            assert "phishing_probability" in pred
            assert "prediction" in pred
            assert "confidence" in pred

            # Validate types and ranges
            assert isinstance(pred["name"], str)
            assert 0.0 <= pred["phishing_probability"] <= 1.0
            assert pred["prediction"] in ["phishing", "legitimate"]
            assert 0.5 <= pred["confidence"] <= 1.0

    def test_predict_ensemble_voting_method(self, client_with_ensemble):
        """Test voting_method is set correctly."""
        response = client_with_ensemble.post(
            "/predict/ensemble", json={"url": "https://example.com"}
        )
        data = response.json()
        assert data["voting_method"] == "soft"
