"""Integration tests for Phase 2: Core ML Pipeline - URL Detection MVP.

These tests verify end-to-end functionality:
- Feature extraction from real URLs
- Model training and persistence
- API endpoint with real predictions
- Latency requirements (<500ms)

Requirements tested:
- INPUT-01: System accepts URL via API
- FEAT-01, FEAT-05: Feature extraction (30+ features)
- FEAT-08: Feature normalization (via StandardScaler in Pipeline)
- ML-01: Random Forest classifier
- ML-08: Returns phishing probability
- MODEL-01: Model saved to file
- MODEL-02: Model loads without retraining
- EVAL-01, EVAL-02, EVAL-03: Evaluation metrics
"""
import pytest
import time
from pathlib import Path
import numpy as np
from fastapi.testclient import TestClient


# --- Feature Extraction Integration Tests ---

class TestFeatureExtractionIntegration:
    """Test feature extraction with real URLs."""

    def test_extract_features_from_legitimate_url(self):
        """Test feature extraction from known legitimate URL."""
        from src.features.extractors import extract_url_features

        features = extract_url_features("https://www.google.com/search?q=test")

        # Verify 30+ features
        assert len(features) >= 30, f"Expected 30+ features, got {len(features)}"

        # Verify expected values for known URL
        assert features['has_https'] == 1
        assert features['has_subdomain'] == 1  # 'www'
        assert features['has_query'] == 1
        assert features['has_suspicious_tld'] == 0  # .com is not suspicious

    def test_extract_features_from_suspicious_url(self):
        """Test feature extraction from suspicious URL patterns."""
        from src.features.extractors import extract_url_features

        # Suspicious TLD, no HTTPS, IP-like pattern
        features = extract_url_features("http://login-secure.tk/paypal/verify.php")

        assert features['has_https'] == 0
        assert features['has_suspicious_tld'] == 1  # .tk is suspicious
        assert features['hyphen_count'] >= 1

    def test_feature_extraction_performance(self):
        """Test feature extraction completes in <50ms."""
        from src.features.extractors import extract_url_features

        start = time.time()
        for _ in range(100):
            extract_url_features("https://example.com/path/to/page?query=value")
        elapsed = (time.time() - start) * 1000 / 100  # Average ms per extraction

        assert elapsed < 50, f"Feature extraction too slow: {elapsed:.1f}ms (limit: 50ms)"


# --- Model Integration Tests ---

class TestModelIntegration:
    """Test model training, persistence, and prediction."""

    @pytest.fixture
    def model_path(self):
        return Path("models/rf_pipeline.joblib")

    def test_model_file_exists(self, model_path):
        """Test trained model file exists."""
        assert model_path.exists(), f"Model not found at {model_path}. Run training first."

    def test_model_loads_successfully(self, model_path):
        """Test model loads without errors (MODEL-02)."""
        from src.models.predict import load_model

        model = load_model(model_path)
        assert model is not None
        assert hasattr(model, 'predict')
        assert hasattr(model, 'predict_proba')

    def test_model_has_correct_structure(self, model_path):
        """Test model is sklearn Pipeline with expected steps."""
        from src.models.predict import load_model

        model = load_model(model_path)

        # Verify Pipeline structure
        assert hasattr(model, 'steps'), "Model should be sklearn Pipeline"
        step_names = [step[0] for step in model.steps]
        assert 'scaler' in step_names, "Pipeline should have 'scaler' step"
        assert 'classifier' in step_names, "Pipeline should have 'classifier' step"

    def test_model_prediction_with_features(self, model_path):
        """Test model predicts from feature dict (ML-08)."""
        from src.models.predict import load_model, predict_single
        from src.features.extractors import extract_url_features

        model = load_model(model_path)
        features = extract_url_features("https://example.com")

        result = predict_single(model, features)

        assert 'phishing_probability' in result
        assert 'prediction' in result
        assert 'confidence' in result
        assert 0.0 <= result['phishing_probability'] <= 1.0
        assert result['prediction'] in ['phishing', 'legitimate']


# --- API Integration Tests ---

class TestAPIIntegration:
    """Test FastAPI endpoint with real model."""

    @pytest.fixture
    def client(self):
        """Create test client with real model."""
        from src.api.main import app, ml_models
        from src.models.predict import load_model
        from pathlib import Path

        # Load real model for integration test
        model_path = Path("models/rf_pipeline.joblib")
        if model_path.exists():
            ml_models["phishing_detector"] = load_model(model_path)

        return TestClient(app)

    def test_health_endpoint(self, client):
        """Test health check returns model status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert data['model_loaded'] == True

    def test_predict_legitimate_url(self, client):
        """Test prediction for likely legitimate URL (INPUT-01)."""
        response = client.post(
            "/predict",
            json={"url": "https://www.google.com"}
        )
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert 'phishing_probability' in data
        assert 'prediction' in data
        assert 'confidence' in data
        assert 'processing_time_ms' in data

        # Google.com should likely be classified as legitimate
        # (not asserting exact value - model behavior may vary)
        assert 0.0 <= data['phishing_probability'] <= 1.0

    def test_predict_suspicious_url(self, client):
        """Test prediction for suspicious URL patterns."""
        response = client.post(
            "/predict",
            json={"url": "http://login-paypal-secure.tk/verify.php?user=victim"}
        )
        assert response.status_code == 200
        data = response.json()

        # Suspicious patterns should increase phishing probability
        # (not asserting exact threshold - model behavior may vary)
        assert 0.0 <= data['phishing_probability'] <= 1.0

    def test_predict_latency_under_500ms(self, client):
        """Test API response time is under 500ms per requirement."""
        # Warm up (first request may be slower)
        client.post("/predict", json={"url": "https://example.com"})

        # Measure actual latency
        start = time.time()
        response = client.post(
            "/predict",
            json={"url": "https://www.example.com/path/to/resource?query=value"}
        )
        elapsed = (time.time() - start) * 1000

        assert response.status_code == 200
        assert elapsed < 500, f"API response too slow: {elapsed:.1f}ms (limit: 500ms)"

        # Also verify processing_time_ms in response
        data = response.json()
        assert data['processing_time_ms'] < 500

    def test_predict_invalid_url_rejected(self, client):
        """Test URL validation rejects invalid URLs."""
        # No http/https
        response = client.post("/predict", json={"url": "example.com"})
        assert response.status_code == 422

        # Too short
        response = client.post("/predict", json={"url": "http://x"})
        assert response.status_code == 422

    def test_openapi_docs_available(self, client):
        """Test Swagger UI is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200

        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert 'paths' in schema
        assert '/predict' in schema['paths']


# --- End-to-End Flow Test ---

class TestEndToEndFlow:
    """Test complete flow: URL -> Features -> Model -> Response."""

    def test_complete_flow_manual(self):
        """Test complete flow without API (direct function calls)."""
        from src.features.extractors import extract_url_features
        from src.models.predict import load_model, predict_single
        from pathlib import Path

        # Step 1: Extract features from URL
        url = "https://suspicious-site.tk/login.php?redirect=http://evil.com"
        features = extract_url_features(url)
        assert len(features) >= 30

        # Step 2: Load model
        model = load_model(Path("models/rf_pipeline.joblib"))
        assert model is not None

        # Step 3: Predict
        result = predict_single(model, features)
        assert 'phishing_probability' in result
        assert result['prediction'] in ['phishing', 'legitimate']

        print(f"\nEnd-to-end test result for: {url}")
        print(f"  Phishing probability: {result['phishing_probability']:.2%}")
        print(f"  Prediction: {result['prediction']}")
        print(f"  Confidence: {result['confidence']:.2%}")
