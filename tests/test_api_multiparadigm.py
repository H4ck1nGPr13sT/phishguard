"""Test suite for /predict/multi-paradigm API endpoint.

Tests the multi-paradigm phishing detection endpoint that combines
ML ensemble, rule-based, and Bayesian predictions.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
import numpy as np

from src.api.main import app, ml_models


@pytest.fixture
def client():
    """Create test client with mocked models."""
    # Mock all required models
    mock_ensemble = Mock()
    mock_ensemble.predict_proba.return_value = np.array([[0.2, 0.8]])

    mock_rule_engine = Mock()
    mock_rule_engine.evaluate.return_value = {
        'score': 0.6,
        'prediction': 'phishing',
        'fired_rules': [
            {'name': 'ip_address_host', 'description': 'URL uses IP', 'weight': 0.35, 'matched_values': ['192.168.1.1']}
        ],
        'rule_count': 1
    }

    mock_bayesian = Mock()
    mock_bayesian.predict_with_posterior.return_value = {
        'posterior_phishing': 0.75,
        'posterior_legitimate': 0.25,
        'prediction': 'phishing',
        'confidence': 0.75
    }

    mock_aggregator = Mock()
    mock_aggregator.aggregate.return_value = {
        'final_prediction': 'phishing',
        'final_probability': 0.72,
        'confidence': 0.72,
        'paradigm_contributions': {
            'ml_ensemble': {'probability': 0.8, 'weight': 0.5, 'weighted_contribution': 0.4, 'prediction': 'phishing'},
            'rules': {'probability': 0.6, 'weight': 0.3, 'weighted_contribution': 0.18, 'prediction': 'phishing'},
            'bayesian': {'probability': 0.75, 'weight': 0.2, 'weighted_contribution': 0.15, 'prediction': 'phishing'}
        },
        'disagreement': {
            'score': 0.0,
            'is_edge_case': False,
            'vote_distribution': {'phishing': 3},
            'probability_variance': 0.01,
            'disagreeing_paradigms': [],
            'probability_spread': 0.2
        },
        'active_rules': [
            {'name': 'ip_address_host', 'description': 'URL uses IP', 'weight': 0.35, 'matched_values': ['192.168.1.1']}
        ],
        'explanation': 'Prediction: PHISHING (72% probability)'
    }

    # Inject mocks
    ml_models["voting_soft"] = mock_ensemble
    ml_models["rule_engine"] = mock_rule_engine
    ml_models["bayesian"] = mock_bayesian
    ml_models["aggregator"] = mock_aggregator

    with TestClient(app) as client:
        yield client

    # Cleanup
    for key in ["voting_soft", "rule_engine", "bayesian", "aggregator"]:
        ml_models.pop(key, None)


class TestMultiParadigmEndpoint:
    """Test /predict/multi-paradigm endpoint."""

    def test_valid_url_returns_200(self, client):
        """Test valid URL returns 200 OK."""
        response = client.post(
            "/predict/multi-paradigm",
            json={"url": "http://192.168.1.1/login"}
        )
        assert response.status_code == 200

    def test_response_contains_required_fields(self, client):
        """Test response contains all required fields."""
        response = client.post(
            "/predict/multi-paradigm",
            json={"url": "http://example.com"}
        )
        data = response.json()

        required_fields = [
            'url', 'final_prediction', 'final_probability', 'confidence',
            'paradigm_contributions', 'disagreement', 'active_rules',
            'explanation', 'processing_time_ms'
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_paradigm_contributions_structure(self, client):
        """Test paradigm contributions have correct structure."""
        response = client.post(
            "/predict/multi-paradigm",
            json={"url": "http://example.com"}
        )
        data = response.json()

        contributions = data['paradigm_contributions']
        for paradigm in ['ml_ensemble', 'rules', 'bayesian']:
            assert paradigm in contributions
            assert 'probability' in contributions[paradigm]
            assert 'weight' in contributions[paradigm]
            assert 'weighted_contribution' in contributions[paradigm]
            assert 'prediction' in contributions[paradigm]

    def test_disagreement_structure(self, client):
        """Test disagreement info has correct structure."""
        response = client.post(
            "/predict/multi-paradigm",
            json={"url": "http://example.com"}
        )
        data = response.json()

        disagreement = data['disagreement']
        assert 'score' in disagreement
        assert 'is_edge_case' in disagreement
        assert 'vote_distribution' in disagreement
        assert 'disagreeing_paradigms' in disagreement

    def test_active_rules_structure(self, client):
        """Test active rules have correct structure."""
        response = client.post(
            "/predict/multi-paradigm",
            json={"url": "http://192.168.1.1/login"}
        )
        data = response.json()

        assert isinstance(data['active_rules'], list)
        if data['active_rules']:
            rule = data['active_rules'][0]
            assert 'name' in rule
            assert 'description' in rule
            assert 'weight' in rule

    def test_invalid_url_returns_422(self, client):
        """Test invalid URL returns 422 validation error."""
        response = client.post(
            "/predict/multi-paradigm",
            json={"url": "not-a-url"}
        )
        assert response.status_code == 422

    def test_missing_url_returns_422(self, client):
        """Test missing URL returns 422."""
        response = client.post(
            "/predict/multi-paradigm",
            json={}
        )
        assert response.status_code == 422

    def test_probability_in_valid_range(self, client):
        """Test probabilities are in 0-1 range."""
        response = client.post(
            "/predict/multi-paradigm",
            json={"url": "http://example.com"}
        )
        data = response.json()

        assert 0.0 <= data['final_probability'] <= 1.0
        assert 0.5 <= data['confidence'] <= 1.0

        for paradigm in data['paradigm_contributions'].values():
            assert 0.0 <= paradigm['probability'] <= 1.0
            assert 0.0 <= paradigm['weight'] <= 1.0

    def test_processing_time_recorded(self, client):
        """Test processing time is recorded."""
        response = client.post(
            "/predict/multi-paradigm",
            json={"url": "http://example.com"}
        )
        data = response.json()

        assert data['processing_time_ms'] > 0
        assert data['processing_time_ms'] < 10000  # Reasonable upper bound

    def test_explanation_is_string(self, client):
        """Test explanation is non-empty string."""
        response = client.post(
            "/predict/multi-paradigm",
            json={"url": "http://example.com"}
        )
        data = response.json()

        assert isinstance(data['explanation'], str)
        assert len(data['explanation']) > 0


class TestMultiParadigmMissingModels:
    """Test error handling when models are missing."""

    def test_missing_models_returns_503(self):
        """Test 503 returned when required models missing.

        Note: This test clears models AFTER lifespan has loaded them,
        simulating a scenario where models become unavailable.
        """
        with TestClient(app) as client:
            # Clear models after lifespan has run (simulates runtime failure)
            original_models = ml_models.copy()
            ml_models.clear()

            try:
                response = client.post(
                    "/predict/multi-paradigm",
                    json={"url": "http://example.com"}
                )
                assert response.status_code == 503
                assert "not loaded" in response.json()['detail'].lower()
            finally:
                # Restore models for other tests
                ml_models.update(original_models)


class TestRootEndpoint:
    """Test API info endpoint includes multi-paradigm.

    Phase 8: the JSON info payload moved from GET / to GET /api/info
    (GET / now serves the HTML web UI; see src/api/web.py).
    """

    def test_root_lists_multiparadigm_endpoint(self):
        """Test /api/info endpoint lists /predict/multi-paradigm."""
        with TestClient(app) as client:
            response = client.get("/api/info")
            data = response.json()
            assert "/predict/multi-paradigm" in data['endpoints']
