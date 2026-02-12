"""Bayesian probabilistic paradigm for phishing detection.

This module implements Bayesian reasoning for phishing detection,
providing posterior probabilities and prior information for
interpretable multi-paradigm aggregation.

Key Features:
- GaussianNB wrapper with enhanced output format
- Posterior probability extraction
- Prior information for interpretability
- Integration with existing feature extraction pipeline
"""

from src.paradigms.bayesian.classifier import BayesianClassifier

__all__ = ["BayesianClassifier"]
