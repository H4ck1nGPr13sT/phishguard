"""Bayesian probabilistic classifier for phishing detection.

Wraps scikit-learn GaussianNB with enhanced output including
posterior probabilities and prior information for interpretability.

Note: Naive Bayes posteriors are NOT perfectly calibrated probabilities.
Use as ranking signal, not absolute probability.
"""

from pathlib import Path
from typing import Dict, Optional, Union
import numpy as np
import joblib
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


class BayesianClassifier:
    """Bayesian classifier wrapper with posterior probability extraction.

    Wraps GaussianNB from existing ensemble (Phase 3) with enhanced
    output format for multi-paradigm aggregation.

    Attributes:
        model: GaussianNB or Pipeline containing GaussianNB
        is_fitted: Whether the model has been trained
    """

    def __init__(self, var_smoothing: float = 1e-9):
        """Initialize Bayesian classifier.

        Args:
            var_smoothing: Portion of largest variance added to variances
                          for numerical stability. Default 1e-9.
        """
        self.pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', GaussianNB(var_smoothing=var_smoothing))
        ])
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> 'BayesianClassifier':
        """Train Bayesian classifier on features and labels.

        Args:
            X: Feature array shape (n_samples, n_features)
            y: Label array shape (n_samples,), 0=legitimate, 1=phishing

        Returns:
            Self for method chaining.
        """
        self.pipeline.fit(X, y)
        self.is_fitted = True
        return self

    def predict_with_posterior(self, X: np.ndarray) -> Dict:
        """Predict with detailed posterior probability output.

        Args:
            X: Feature array for single sample shape (1, n_features)

        Returns:
            Dict with:
                'posterior_phishing': float - P(phishing|features)
                'posterior_legitimate': float - P(legitimate|features)
                'prediction': str - 'phishing' or 'legitimate'
                'confidence': float - max(posteriors)
                'prior_info': dict with class prior probabilities

        Note:
            Posteriors may be poorly calibrated (extreme values 0.99/0.01).
            Use for ranking, not absolute probability interpretation.
        """
        if not self.is_fitted:
            raise ValueError("Classifier must be fitted before prediction")

        # Get posterior probabilities
        posterior = self.pipeline.predict_proba(X)[0]

        # Extract class priors from underlying GaussianNB
        classifier = self.pipeline.named_steps['classifier']
        prior_log_probs = classifier.class_log_prior_

        # Build response
        phishing_prob = float(posterior[1])
        legitimate_prob = float(posterior[0])

        return {
            'posterior_phishing': phishing_prob,
            'posterior_legitimate': legitimate_prob,
            'prediction': 'phishing' if phishing_prob > 0.5 else 'legitimate',
            'confidence': float(max(posterior)),
            'prior_info': {
                'log_prior_legitimate': float(prior_log_probs[0]),
                'log_prior_phishing': float(prior_log_probs[1]),
                'prior_legitimate': float(np.exp(prior_log_probs[0])),
                'prior_phishing': float(np.exp(prior_log_probs[1]))
            }
        }

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Standard predict method for compatibility."""
        return self.pipeline.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Standard predict_proba for compatibility."""
        return self.pipeline.predict_proba(X)

    def save(self, path: Path) -> None:
        """Save trained model to disk."""
        joblib.dump(
            {'pipeline': self.pipeline, 'is_fitted': self.is_fitted},
            path,
            compress=3,
            protocol=5
        )

    @classmethod
    def load(cls, path: Path) -> 'BayesianClassifier':
        """Load trained model from disk."""
        data = joblib.load(path)
        instance = cls()
        instance.pipeline = data['pipeline']
        instance.is_fitted = data['is_fitted']
        return instance
