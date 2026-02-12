"""Test suite for Bayesian probabilistic classifier.

Tests BayesianClassifier wrapper including:
- Model training and fitting
- Posterior probability extraction
- Prior information retrieval
- Model persistence (save/load)
- Edge cases and error handling
"""

import pytest
import numpy as np
from pathlib import Path
import tempfile

from src.paradigms.bayesian import BayesianClassifier


@pytest.fixture
def sample_data():
    """Generate simple 2-class dataset for testing."""
    np.random.seed(42)
    # Class 0 (legitimate): low values
    X0 = np.random.randn(50, 10) - 1
    # Class 1 (phishing): high values
    X1 = np.random.randn(50, 10) + 1
    X = np.vstack([X0, X1])
    y = np.array([0]*50 + [1]*50)
    return X, y


@pytest.fixture
def trained_classifier(sample_data):
    """Return a fitted BayesianClassifier."""
    X, y = sample_data
    classifier = BayesianClassifier()
    classifier.fit(X, y)
    return classifier


class TestBayesianClassifierInit:
    """Test classifier initialization."""

    def test_default_initialization(self):
        """Test classifier initializes with default parameters."""
        clf = BayesianClassifier()
        assert clf.is_fitted is False
        assert clf.pipeline is not None

    def test_custom_var_smoothing(self):
        """Test custom var_smoothing parameter."""
        clf = BayesianClassifier(var_smoothing=1e-6)
        nb = clf.pipeline.named_steps['classifier']
        assert nb.var_smoothing == 1e-6


class TestBayesianClassifierFit:
    """Test classifier training."""

    def test_fit_returns_self(self, sample_data):
        """Test fit returns self for method chaining."""
        X, y = sample_data
        clf = BayesianClassifier()
        result = clf.fit(X, y)
        assert result is clf

    def test_is_fitted_after_training(self, sample_data):
        """Test is_fitted flag set after training."""
        X, y = sample_data
        clf = BayesianClassifier()
        assert clf.is_fitted is False
        clf.fit(X, y)
        assert clf.is_fitted is True


class TestPredictWithPosterior:
    """Test posterior probability extraction."""

    def test_raises_before_fit(self, sample_data):
        """Test error raised if predict called before fit."""
        X, _ = sample_data
        clf = BayesianClassifier()
        with pytest.raises(ValueError, match="must be fitted"):
            clf.predict_with_posterior(X[:1])

    def test_posterior_structure(self, trained_classifier, sample_data):
        """Test predict_with_posterior returns correct structure."""
        X, _ = sample_data
        result = trained_classifier.predict_with_posterior(X[:1])

        assert 'posterior_phishing' in result
        assert 'posterior_legitimate' in result
        assert 'prediction' in result
        assert 'confidence' in result
        assert 'prior_info' in result

    def test_posteriors_sum_to_one(self, trained_classifier, sample_data):
        """Test posterior probabilities sum to 1."""
        X, _ = sample_data
        result = trained_classifier.predict_with_posterior(X[:1])

        total = result['posterior_phishing'] + result['posterior_legitimate']
        assert abs(total - 1.0) < 1e-6

    def test_posteriors_in_valid_range(self, trained_classifier, sample_data):
        """Test posteriors are between 0 and 1."""
        X, _ = sample_data
        for i in range(10):
            result = trained_classifier.predict_with_posterior(X[i:i+1])
            assert 0.0 <= result['posterior_phishing'] <= 1.0
            assert 0.0 <= result['posterior_legitimate'] <= 1.0

    def test_prediction_matches_threshold(self, trained_classifier, sample_data):
        """Test prediction matches 0.5 threshold on posterior."""
        X, _ = sample_data
        for i in range(10):
            result = trained_classifier.predict_with_posterior(X[i:i+1])
            if result['posterior_phishing'] > 0.5:
                assert result['prediction'] == 'phishing'
            else:
                assert result['prediction'] == 'legitimate'

    def test_confidence_equals_max_posterior(self, trained_classifier, sample_data):
        """Test confidence equals max of posteriors."""
        X, _ = sample_data
        result = trained_classifier.predict_with_posterior(X[:1])

        expected_confidence = max(result['posterior_phishing'],
                                  result['posterior_legitimate'])
        assert abs(result['confidence'] - expected_confidence) < 1e-6

    def test_prior_info_contains_required_fields(self, trained_classifier, sample_data):
        """Test prior_info contains all required fields."""
        X, _ = sample_data
        result = trained_classifier.predict_with_posterior(X[:1])

        assert 'log_prior_legitimate' in result['prior_info']
        assert 'log_prior_phishing' in result['prior_info']
        assert 'prior_legitimate' in result['prior_info']
        assert 'prior_phishing' in result['prior_info']

    def test_priors_sum_to_one(self, trained_classifier, sample_data):
        """Test class priors sum to 1."""
        X, _ = sample_data
        result = trained_classifier.predict_with_posterior(X[:1])

        total_prior = (result['prior_info']['prior_legitimate'] +
                       result['prior_info']['prior_phishing'])
        assert abs(total_prior - 1.0) < 1e-6


class TestModelPersistence:
    """Test model save/load functionality."""

    def test_save_and_load(self, trained_classifier, sample_data):
        """Test model can be saved and loaded."""
        X, _ = sample_data

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.joblib"
            trained_classifier.save(path)

            # Load model
            loaded = BayesianClassifier.load(path)

            # Compare predictions
            orig_result = trained_classifier.predict_with_posterior(X[:1])
            loaded_result = loaded.predict_with_posterior(X[:1])

            assert orig_result['posterior_phishing'] == loaded_result['posterior_phishing']
            assert orig_result['prediction'] == loaded_result['prediction']

    def test_loaded_model_is_fitted(self, trained_classifier):
        """Test loaded model has is_fitted=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.joblib"
            trained_classifier.save(path)
            loaded = BayesianClassifier.load(path)
            assert loaded.is_fitted is True


class TestCompatibilityMethods:
    """Test sklearn-compatible interface methods."""

    def test_predict_returns_array(self, trained_classifier, sample_data):
        """Test predict returns numpy array."""
        X, _ = sample_data
        predictions = trained_classifier.predict(X[:5])
        assert isinstance(predictions, np.ndarray)
        assert len(predictions) == 5

    def test_predict_proba_shape(self, trained_classifier, sample_data):
        """Test predict_proba returns correct shape."""
        X, _ = sample_data
        probas = trained_classifier.predict_proba(X[:5])
        assert probas.shape == (5, 2)
