"""Integration tests for Phase 5 multi-paradigm detection system.

Tests the complete flow from URL input through all three paradigms
to aggregated output. Requires trained models to be present.
"""

import pytest
import numpy as np
from pathlib import Path

from src.features.extractors import extract_url_features
from src.paradigms.rules import RuleEngine
from src.paradigms.bayesian import BayesianClassifier
from src.paradigms.aggregation import MultiParadigmAggregator


class TestPhase5Integration:
    """Integration tests for Phase 5 components."""

    @pytest.fixture
    def rule_engine(self):
        """Load rule engine."""
        return RuleEngine()

    @pytest.fixture
    def bayesian_classifier(self):
        """Load Bayesian classifier if available."""
        path = Path("models/bayesian/bayesian_classifier.joblib")
        if path.exists():
            return BayesianClassifier.load(path)
        pytest.skip("Bayesian model not trained yet")

    @pytest.fixture
    def aggregator(self):
        """Create aggregator."""
        return MultiParadigmAggregator()

    def test_feature_extraction_to_rules(self, rule_engine):
        """Test features can be passed to rule engine."""
        url = "http://192.168.1.1/login/verify"
        features = extract_url_features(url)

        result = rule_engine.evaluate(features)

        assert 'score' in result
        assert 'fired_rules' in result
        assert result['score'] > 0, "IP-based URL should trigger rules"

    def test_feature_extraction_to_bayesian(self, bayesian_classifier):
        """Test features can be passed to Bayesian classifier."""
        url = "https://www.google.com"
        features = extract_url_features(url)
        feature_array = np.array([list(features.values())])

        result = bayesian_classifier.predict_with_posterior(feature_array)

        assert 'posterior_phishing' in result
        assert 'prediction' in result
        assert 0 <= result['posterior_phishing'] <= 1

    def test_full_aggregation_flow(self, rule_engine, bayesian_classifier, aggregator):
        """Test complete aggregation from URL to verdict."""
        url = "http://192.168.1.1/admin"
        features = extract_url_features(url)
        feature_array = np.array([list(features.values())])

        # Get predictions from each paradigm
        ml_result = {
            'ensemble_probability': 0.85,  # Mocked - would come from ensemble
            'prediction': 'phishing'
        }
        rule_result = rule_engine.evaluate(features)
        bayesian_result = bayesian_classifier.predict_with_posterior(feature_array)

        # Aggregate
        aggregated = aggregator.aggregate(ml_result, rule_result, bayesian_result)

        # Verify structure
        assert 'final_prediction' in aggregated
        assert 'final_probability' in aggregated
        assert 'paradigm_contributions' in aggregated
        assert 'disagreement' in aggregated
        assert 'active_rules' in aggregated

    def test_legitimate_url_low_scores(self, rule_engine, bayesian_classifier, aggregator):
        """Test legitimate URL gets low phishing scores."""
        url = "https://www.google.com"
        features = extract_url_features(url)
        feature_array = np.array([list(features.values())])

        rule_result = rule_engine.evaluate(features)
        bayesian_result = bayesian_classifier.predict_with_posterior(feature_array)

        # Google should have low rule score
        assert rule_result['score'] < 0.5, "Google should not trigger many rules"

    def test_suspicious_url_high_scores(self, rule_engine, bayesian_classifier, aggregator):
        """Test suspicious URL gets high phishing scores."""
        url = "http://192.168.1.1/verify-account-urgent"
        features = extract_url_features(url)

        rule_result = rule_engine.evaluate(features)

        # IP-based URL should trigger rules
        assert rule_result['score'] > 0, "IP URL should trigger rules"

    def test_paradigm_disagreement_detected(self, aggregator):
        """Test paradigm disagreement is detected."""
        # Simulate disagreement: ML says phishing, rules say legitimate
        ml_result = {'ensemble_probability': 0.9, 'prediction': 'phishing'}
        rule_result = {
            'score': 0.2,
            'prediction': 'legitimate',
            'fired_rules': [],
            'rule_count': 0
        }
        bayesian_result = {
            'posterior_phishing': 0.85,
            'prediction': 'phishing'
        }

        aggregated = aggregator.aggregate(ml_result, rule_result, bayesian_result)

        # Should detect that rules disagree
        assert 'rules' in aggregated['disagreement']['disagreeing_paradigms']

    def test_weights_affect_final_probability(self, aggregator):
        """Test paradigm weights affect final probability."""
        ml_result = {'ensemble_probability': 1.0, 'prediction': 'phishing'}
        rule_result = {'score': 0.0, 'prediction': 'legitimate', 'fired_rules': [], 'rule_count': 0}
        bayesian_result = {'posterior_phishing': 0.0, 'prediction': 'legitimate'}

        aggregated = aggregator.aggregate(ml_result, rule_result, bayesian_result)

        # With default weights (0.5, 0.3, 0.2), final prob = 0.5*1.0 + 0.3*0.0 + 0.2*0.0 = 0.5
        assert abs(aggregated['final_probability'] - 0.5) < 0.01


class TestPhase5Requirements:
    """Verify all Phase 5 requirements are met."""

    @pytest.fixture
    def rule_engine(self):
        return RuleEngine()

    def test_rule01_keyword_rules(self, rule_engine):
        """RULE-01: Rules for phishing keywords."""
        rules = rule_engine.ruleset.rules
        keyword_rules = [r for r in rules if r.condition.type == 'keyword_match']
        assert len(keyword_rules) > 0, "Should have keyword match rules"

    def test_rule02_url_structure_rules(self, rule_engine):
        """RULE-02: Rules for suspicious URL structures."""
        rules = rule_engine.ruleset.rules
        structure_rules = [r for r in rules
                         if r.name in ['ip_address_host', 'shortened_url', 'suspicious_tld']]
        assert len(structure_rules) > 0, "Should have URL structure rules"

    def test_rule05_rules_have_weights(self, rule_engine):
        """RULE-05: All rules have weights."""
        for rule in rule_engine.ruleset.rules:
            assert hasattr(rule, 'weight')
            assert 0 <= rule.weight <= 1

    def test_rule06_aggregates_to_score(self, rule_engine):
        """RULE-06: System aggregates rules to final score."""
        features = extract_url_features('http://192.168.1.1/login')
        result = rule_engine.evaluate(features)
        assert 'score' in result
        assert isinstance(result['score'], float)

    def test_rule07_returns_active_rules(self, rule_engine):
        """RULE-07: Returns list of active rules."""
        features = extract_url_features('http://192.168.1.1/login')
        result = rule_engine.evaluate(features)
        assert 'fired_rules' in result
        assert isinstance(result['fired_rules'], list)

    def test_prob01_naive_bayes_implemented(self):
        """PROB-01: Naive Bayes implemented."""
        path = Path("models/bayesian/bayesian_classifier.joblib")
        if not path.exists():
            pytest.skip("Bayesian model not trained")
        clf = BayesianClassifier.load(path)
        assert clf.is_fitted

    def test_prob03_returns_posterior(self):
        """PROB-03: Returns posterior probability."""
        path = Path("models/bayesian/bayesian_classifier.joblib")
        if not path.exists():
            pytest.skip("Bayesian model not trained")
        clf = BayesianClassifier.load(path)

        features = extract_url_features('http://example.com')
        X = np.array([list(features.values())])
        result = clf.predict_with_posterior(X)

        assert 'posterior_phishing' in result

    def test_agg01_combines_paradigms(self):
        """AGG-01: Combines ML, rules, Bayesian."""
        agg = MultiParadigmAggregator()
        result = agg.aggregate(
            {'ensemble_probability': 0.8, 'prediction': 'phishing'},
            {'score': 0.6, 'prediction': 'phishing', 'fired_rules': [], 'rule_count': 0},
            {'posterior_phishing': 0.7, 'prediction': 'phishing'}
        )
        assert 'paradigm_contributions' in result
        assert 'ml_ensemble' in result['paradigm_contributions']
        assert 'rules' in result['paradigm_contributions']
        assert 'bayesian' in result['paradigm_contributions']

    def test_agg02_detects_disagreement(self):
        """AGG-02: Detects paradigm disagreements."""
        agg = MultiParadigmAggregator()
        result = agg.aggregate(
            {'ensemble_probability': 0.9, 'prediction': 'phishing'},
            {'score': 0.1, 'prediction': 'legitimate', 'fired_rules': [], 'rule_count': 0},
            {'posterior_phishing': 0.9, 'prediction': 'phishing'}
        )
        assert 'disagreement' in result
        assert len(result['disagreement']['disagreeing_paradigms']) > 0

    def test_agg03_generates_decision(self):
        """AGG-03: Generates final decision with confidence."""
        agg = MultiParadigmAggregator()
        result = agg.aggregate(
            {'ensemble_probability': 0.8, 'prediction': 'phishing'},
            {'score': 0.6, 'prediction': 'phishing', 'fired_rules': [], 'rule_count': 0},
            {'posterior_phishing': 0.7, 'prediction': 'phishing'}
        )
        assert result['final_prediction'] in ['phishing', 'legitimate']
        assert 'confidence' in result

    def test_agg04_shows_weighted_contributions(self):
        """AGG-04: Shows weighted contributions."""
        agg = MultiParadigmAggregator()
        result = agg.aggregate(
            {'ensemble_probability': 0.8, 'prediction': 'phishing'},
            {'score': 0.6, 'prediction': 'phishing', 'fired_rules': [], 'rule_count': 0},
            {'posterior_phishing': 0.7, 'prediction': 'phishing'}
        )
        for paradigm in result['paradigm_contributions'].values():
            assert 'weight' in paradigm
            assert 'weighted_contribution' in paradigm
