"""Multi-paradigm aggregation layer for phishing detection.

This module combines predictions from three detection paradigms:
- ML ensemble (7 classifiers with weighted voting)
- Rule-based expert system (weighted rule scoring)
- Bayesian probabilistic classifier (posterior probabilities)

The aggregation layer provides:
- Configurable paradigm weights with validation
- Cross-paradigm disagreement detection using normalized entropy
- Final verdict with confidence scores and active rules list
"""

from src.paradigms.aggregation.aggregator import MultiParadigmAggregator
from src.paradigms.aggregation.weights import ParadigmWeights, DEFAULT_WEIGHTS
from src.paradigms.aggregation.disagreement import (
    calculate_paradigm_disagreement,
    get_disagreement_explanation,
    PARADIGM_DISAGREEMENT_THRESHOLD
)

__all__ = [
    'MultiParadigmAggregator',
    'ParadigmWeights',
    'DEFAULT_WEIGHTS',
    'calculate_paradigm_disagreement',
    'get_disagreement_explanation',
    'PARADIGM_DISAGREEMENT_THRESHOLD'
]
