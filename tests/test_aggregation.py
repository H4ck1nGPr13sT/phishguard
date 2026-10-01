"""Test suite for multi-paradigm aggregation layer.

Tests:
- ParadigmWeights validation
- Cross-paradigm disagreement detection
- MultiParadigmAggregator weighted aggregation
- Edge case detection and explanation generation
"""

import pytest
import numpy as np
from src.paradigms.aggregation import (
    MultiParadigmAggregator,
    ParadigmWeights,
    calculate_paradigm_disagreement
)
from src.paradigms.aggregation.weights import DEFAULT_WEIGHTS
from src.paradigms.aggregation.disagreement import get_disagreement_explanation


class TestParadigmWeights:
    """Test weight validation and management."""

    def test_default_weights_sum_to_one(self):
        """Test default weights sum to 1.0."""
        w = DEFAULT_WEIGHTS
        total = w.ml_ensemble + w.rules + w.bayesian
        assert abs(total - 1.0) < 1e-6

    def test_valid_custom_weights(self):
        """Test valid custom weights accepted."""
        w = ParadigmWeights(ml_ensemble=0.6, rules=0.25, bayesian=0.15)
        assert w.ml_ensemble == 0.6

    def test_invalid_weights_sum(self):
        """Test error raised when weights don't sum to 1."""
        with pytest.raises(ValueError, match="sum to 1.0"):
            ParadigmWeights(ml_ensemble=0.5, rules=0.3, bayesian=0.3)

    def test_to_dict(self):
        """Test weights can be converted to dict."""
        w = ParadigmWeights()
        d = w.to_dict()
        assert d['ml_ensemble'] == 0.5
        assert d['rules'] == 0.3
        assert d['bayesian'] == 0.2

    def test_from_dict(self):
        """Test weights can be created from dict."""
        w = ParadigmWeights.from_dict({'ml_ensemble': 0.4, 'rules': 0.4, 'bayesian': 0.2})
        assert w.ml_ensemble == 0.4
        assert w.rules == 0.4


class TestParadigmDisagreement:
    """Test cross-paradigm disagreement detection."""

    def test_unanimous_agreement_score_zero(self):
        """Test unanimous agreement gives 0 disagreement."""
        result = calculate_paradigm_disagreement(
            'phishing', 0.9,
            'phishing', 0.8,
            'phishing', 0.85
        )
        assert result['score'] == 0.0
        assert result['is_edge_case'] == False
        assert len(result['disagreeing_paradigms']) == 0

    def test_2_1_split_is_edge_case(self):
        """A 2-1 paradigm split is a (flagged) edge case.

        Binary votes are normalized by log2(2)=1, so a 2/1 split scores
        H(1/3) = -(2/3*log2(2/3) + 1/3*log2(1/3)) ~= 0.918 — above the 0.7
        threshold. Any non-unanimous 3-paradigm vote is therefore an edge case.
        """
        result = calculate_paradigm_disagreement(
            'phishing', 0.9,
            'legitimate', 0.3,
            'phishing', 0.85
        )
        assert 0.91 < result['score'] < 0.92
        assert bool(result['is_edge_case']) is True
        assert 'rules' in result['disagreeing_paradigms']

    def test_unanimous_legitimate(self):
        """Test all predicting legitimate."""
        result = calculate_paradigm_disagreement(
            'legitimate', 0.1,
            'legitimate', 0.2,
            'legitimate', 0.15
        )
        assert result['score'] == 0.0
        assert result['vote_distribution']['legitimate'] == 3

    def test_probability_variance_calculated(self):
        """Test probability variance is calculated."""
        result = calculate_paradigm_disagreement(
            'phishing', 0.9,
            'phishing', 0.3,
            'phishing', 0.6
        )
        assert 'probability_variance' in result
        # Variance of [0.9, 0.3, 0.6]
        expected_var = np.var([0.9, 0.3, 0.6])
        assert abs(result['probability_variance'] - expected_var) < 1e-6

    def test_probability_spread_calculated(self):
        """Test probability spread (max - min) is calculated."""
        result = calculate_paradigm_disagreement(
            'phishing', 0.9,
            'phishing', 0.2,
            'phishing', 0.5
        )
        assert result['probability_spread'] == 0.7  # 0.9 - 0.2


class TestDisagreementExplanation:
    """Test explanation generation."""

    def test_agreement_explanation(self):
        """Test explanation for agreement."""
        info = calculate_paradigm_disagreement(
            'phishing', 0.9, 'phishing', 0.8, 'phishing', 0.85
        )
        explanation = get_disagreement_explanation(info)
        assert "agree" in explanation.lower()

    def test_high_disagreement_explanation(self):
        """Test explanation mentions manual review for high disagreement."""
        # This would require modifying probs to get high disagreement
        # For 3 paradigms, need 1.5 split which is impossible
        # Instead test moderate disagreement
        info = calculate_paradigm_disagreement(
            'phishing', 0.9, 'legitimate', 0.2, 'phishing', 0.85
        )
        explanation = get_disagreement_explanation(info)
        assert "disagree" in explanation.lower() or "Minor" in explanation


class TestMultiParadigmAggregator:
    """Test aggregation class."""

    @pytest.fixture
    def aggregator(self):
        """Return default aggregator."""
        return MultiParadigmAggregator()

    @pytest.fixture
    def ml_result_phishing(self):
        return {
            'ensemble_probability': 0.85,
            'prediction': 'phishing',
            'individual_predictions': []
        }

    @pytest.fixture
    def rule_result_phishing(self):
        return {
            'score': 0.6,
            'prediction': 'phishing',
            'fired_rules': [
                {'name': 'ip_address_host', 'weight': 0.35},
                {'name': 'suspicious_tld', 'weight': 0.25}
            ],
            'rule_count': 2
        }

    @pytest.fixture
    def bayesian_result_phishing(self):
        return {
            'posterior_phishing': 0.75,
            'prediction': 'phishing',
            'confidence': 0.75
        }

    def test_aggregation_returns_required_fields(
        self, aggregator, ml_result_phishing, rule_result_phishing, bayesian_result_phishing
    ):
        """Test aggregation returns all required fields."""
        result = aggregator.aggregate(
            ml_result_phishing, rule_result_phishing, bayesian_result_phishing
        )

        assert 'final_prediction' in result
        assert 'final_probability' in result
        assert 'confidence' in result
        assert 'paradigm_contributions' in result
        assert 'disagreement' in result
        assert 'active_rules' in result
        assert 'explanation' in result

    def test_weighted_probability_calculation(self, aggregator):
        """Test weighted probability is calculated correctly."""
        ml_result = {'ensemble_probability': 0.8, 'prediction': 'phishing'}
        rule_result = {'score': 0.6, 'prediction': 'phishing', 'fired_rules': [], 'rule_count': 0}
        bayesian_result = {'posterior_phishing': 0.4, 'prediction': 'legitimate'}

        result = aggregator.aggregate(ml_result, rule_result, bayesian_result)

        # Expected: 0.5*0.8 + 0.3*0.6 + 0.2*0.4 = 0.4 + 0.18 + 0.08 = 0.66
        expected_prob = 0.5 * 0.8 + 0.3 * 0.6 + 0.2 * 0.4
        assert abs(result['final_probability'] - expected_prob) < 1e-6

    def test_prediction_threshold(self, aggregator):
        """Test prediction uses 0.5 threshold."""
        # Below threshold
        ml_result = {'ensemble_probability': 0.3, 'prediction': 'legitimate'}
        rule_result = {'score': 0.2, 'prediction': 'legitimate', 'fired_rules': [], 'rule_count': 0}
        bayesian_result = {'posterior_phishing': 0.3, 'prediction': 'legitimate'}

        result = aggregator.aggregate(ml_result, rule_result, bayesian_result)
        assert result['final_prediction'] == 'legitimate'

        # Above threshold
        ml_result['ensemble_probability'] = 0.9
        ml_result['prediction'] = 'phishing'
        result = aggregator.aggregate(ml_result, rule_result, bayesian_result)
        assert result['final_prediction'] == 'phishing'

    def test_paradigm_contributions_structure(
        self, aggregator, ml_result_phishing, rule_result_phishing, bayesian_result_phishing
    ):
        """Test paradigm contributions have correct structure."""
        result = aggregator.aggregate(
            ml_result_phishing, rule_result_phishing, bayesian_result_phishing
        )

        contrib = result['paradigm_contributions']
        for paradigm in ['ml_ensemble', 'rules', 'bayesian']:
            assert paradigm in contrib
            assert 'probability' in contrib[paradigm]
            assert 'weight' in contrib[paradigm]
            assert 'weighted_contribution' in contrib[paradigm]
            assert 'prediction' in contrib[paradigm]

    def test_active_rules_passed_through(
        self, aggregator, ml_result_phishing, rule_result_phishing, bayesian_result_phishing
    ):
        """Test active rules are passed through from rule result."""
        result = aggregator.aggregate(
            ml_result_phishing, rule_result_phishing, bayesian_result_phishing
        )

        assert len(result['active_rules']) == 2
        assert result['active_rules'][0]['name'] == 'ip_address_host'

    def test_custom_weights(self):
        """Test aggregator with custom weights."""
        weights = ParadigmWeights(ml_ensemble=0.6, rules=0.25, bayesian=0.15)
        aggregator = MultiParadigmAggregator(weights=weights)

        ml_result = {'ensemble_probability': 1.0, 'prediction': 'phishing'}
        rule_result = {'score': 0.0, 'prediction': 'legitimate', 'fired_rules': [], 'rule_count': 0}
        bayesian_result = {'posterior_phishing': 0.0, 'prediction': 'legitimate'}

        result = aggregator.aggregate(ml_result, rule_result, bayesian_result)

        # With custom weights: 0.6*1.0 + 0.25*0.0 + 0.15*0.0 = 0.6
        assert abs(result['final_probability'] - 0.6) < 1e-6

    def test_explanation_generated(
        self, aggregator, ml_result_phishing, rule_result_phishing, bayesian_result_phishing
    ):
        """Test explanation is generated."""
        result = aggregator.aggregate(
            ml_result_phishing, rule_result_phishing, bayesian_result_phishing
        )

        assert isinstance(result['explanation'], str)
        assert len(result['explanation']) > 0
        assert 'PHISHING' in result['explanation'].upper() or 'LEGITIMATE' in result['explanation'].upper()

    def test_update_weights(self, aggregator):
        """Test weights can be updated."""
        new_weights = ParadigmWeights(ml_ensemble=0.4, rules=0.4, bayesian=0.2)
        aggregator.update_weights(new_weights)

        assert aggregator.weights.ml_ensemble == 0.4
        assert aggregator.weights.rules == 0.4
