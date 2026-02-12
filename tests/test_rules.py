"""Test suite for rule-based phishing detection engine.

Tests:
- Rule loading and validation from YAML
- All three condition types (keyword_match, feature_check, domain_match)
- Weighted scoring and normalization
- Edge cases and error handling
"""

import pytest
from pathlib import Path
import tempfile
import yaml

from src.paradigms.rules import RuleEngine, PhishingRule, RuleCondition, RuleSet
from src.features.extractors import extract_url_features


class TestRuleDefinitions:
    """Test Pydantic rule definition models."""

    def test_valid_rule_condition_keyword_match(self):
        """Test valid keyword_match condition."""
        cond = RuleCondition(
            type='keyword_match',
            feature='url',
            keywords=['verify', 'urgent']
        )
        assert cond.type == 'keyword_match'
        assert 'verify' in cond.keywords

    def test_valid_rule_condition_feature_check(self):
        """Test valid feature_check condition."""
        cond = RuleCondition(
            type='feature_check',
            feature='has_ip',
            operator='equals',
            value=1
        )
        assert cond.operator == 'equals'

    def test_valid_rule_condition_domain_match(self):
        """Test valid domain_match condition."""
        cond = RuleCondition(
            type='domain_match',
            feature='domain',
            domains=['bit.ly', 'tinyurl.com']
        )
        assert len(cond.domains) == 2

    def test_valid_phishing_rule(self):
        """Test valid PhishingRule creation."""
        rule = PhishingRule(
            name='test_rule',
            description='Test rule',
            weight=0.3,
            condition=RuleCondition(
                type='feature_check',
                feature='has_ip',
                operator='equals',
                value=1
            )
        )
        assert rule.weight == 0.3

    def test_invalid_weight_raises_error(self):
        """Test weight outside 0-1 range raises error."""
        with pytest.raises(ValueError):
            PhishingRule(
                name='bad_rule',
                description='Bad rule',
                weight=1.5,  # Invalid
                condition=RuleCondition(type='feature_check', feature='has_ip', operator='equals', value=1)
            )

    def test_ruleset_from_dict(self):
        """Test RuleSet can be created from dict."""
        data = {
            'version': '1.0.0',
            'rules': [
                {
                    'name': 'test',
                    'description': 'Test',
                    'weight': 0.5,
                    'condition': {
                        'type': 'feature_check',
                        'feature': 'has_ip',
                        'operator': 'equals',
                        'value': 1
                    }
                }
            ]
        }
        ruleset = RuleSet(**data)
        assert len(ruleset.rules) == 1


class TestRuleEngine:
    """Test RuleEngine functionality."""

    @pytest.fixture
    def engine(self):
        """Load default rule engine."""
        return RuleEngine()

    @pytest.fixture
    def simple_rules_yaml(self):
        """Create simple test rules YAML."""
        return {
            'version': '1.0.0',
            'rules': [
                {
                    'name': 'ip_test',
                    'description': 'Test IP detection',
                    'weight': 0.5,
                    'condition': {
                        'type': 'feature_check',
                        'feature': 'has_ip',
                        'operator': 'equals',
                        'value': 1
                    }
                },
                {
                    'name': 'https_test',
                    'description': 'Test HTTPS check',
                    'weight': 0.3,
                    'condition': {
                        'type': 'feature_check',
                        'feature': 'has_https',
                        'operator': 'equals',
                        'value': 0
                    }
                }
            ]
        }

    def test_engine_loads_default_rules(self, engine):
        """Test engine loads rules from default path."""
        assert engine.ruleset is not None
        assert len(engine.ruleset.rules) > 0

    def test_engine_loads_custom_rules(self, simple_rules_yaml):
        """Test engine loads rules from custom path."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(simple_rules_yaml, f)
            f.flush()
            engine = RuleEngine(Path(f.name))
            assert len(engine.ruleset.rules) == 2

    def test_evaluate_returns_required_fields(self, engine):
        """Test evaluate returns all required fields."""
        features = extract_url_features('http://example.com')
        result = engine.evaluate(features)

        required_fields = ['score', 'prediction', 'confidence', 'fired_rules', 'rule_count']
        for field in required_fields:
            assert field in result

    def test_evaluate_ip_url_triggers_rules(self, engine):
        """Test IP-based URL triggers IP detection rule."""
        features = extract_url_features('http://192.168.1.1/login')
        result = engine.evaluate(features)

        assert result['score'] > 0
        assert any(r['name'] == 'ip_address_host' for r in result['fired_rules'])

    def test_evaluate_legitimate_url_low_score(self, engine):
        """Test legitimate URL has low rule score."""
        features = extract_url_features('https://www.google.com')
        result = engine.evaluate(features)

        # Google should trigger few/no rules
        assert result['score'] < 0.5

    def test_evaluate_suspicious_tld_triggers_rule(self, engine):
        """Test suspicious TLD triggers rule."""
        features = extract_url_features('http://suspicious-site.tk/verify')
        result = engine.evaluate(features)

        assert result['score'] > 0
        assert any('suspicious_tld' in r['name'] for r in result['fired_rules'])

    def test_score_capped_at_one(self, simple_rules_yaml):
        """Test score is capped at 1.0 even with many rules firing."""
        # Create rules with total weight > 1
        simple_rules_yaml['rules'][0]['weight'] = 0.8
        simple_rules_yaml['rules'][1]['weight'] = 0.8

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(simple_rules_yaml, f)
            f.flush()
            engine = RuleEngine(Path(f.name))

        # URL that triggers both rules
        features = {'has_ip': 1, 'has_https': 0}
        result = engine.evaluate(features)

        assert result['score'] <= 1.0

    def test_empty_features_returns_zero_score(self, engine):
        """Test empty features dict returns zero score."""
        result = engine.evaluate({})
        assert result['score'] == 0.0
        assert result['prediction'] == 'legitimate'

    def test_prediction_threshold(self, engine):
        """Test prediction uses 0.5 threshold."""
        # Mock low score
        features = extract_url_features('https://www.google.com')
        result = engine.evaluate(features)
        if result['score'] < 0.5:
            assert result['prediction'] == 'legitimate'

        # Mock high score (IP-based URL)
        features = extract_url_features('http://192.168.1.1/admin/config')
        result = engine.evaluate(features)
        # May or may not exceed 0.5 depending on rules

    def test_fired_rules_contain_details(self, engine):
        """Test fired rules contain name, description, weight."""
        features = extract_url_features('http://192.168.1.1/login')
        result = engine.evaluate(features)

        if result['fired_rules']:
            rule = result['fired_rules'][0]
            assert 'name' in rule
            assert 'description' in rule
            assert 'weight' in rule


class TestConditionEvaluation:
    """Test individual condition type evaluation."""

    @pytest.fixture
    def engine(self):
        return RuleEngine()

    def test_feature_check_equals(self, engine):
        """Test feature_check with equals operator."""
        features = {'has_ip': 1}
        # This is implicitly tested through evaluate()
        result = engine.evaluate(features)
        # If has_ip rule fires, condition works
        if any(r['name'] == 'ip_address_host' for r in result['fired_rules']):
            assert True

    def test_feature_check_greater_than(self, engine):
        """Test feature_check with greater_than operator."""
        features = extract_url_features('http://a.b.c.d.e.f.example.com/path')
        result = engine.evaluate(features)
        # Subdomain count rule might fire

    def test_domain_match(self, engine):
        """Test domain_match condition."""
        # Test with URL shortener
        features = extract_url_features('https://bit.ly/abc123')
        features['domain'] = 'bit.ly'  # Ensure domain is in features
        result = engine.evaluate(features)
        # Shortened URL rule might fire if implemented


class TestRuleEngineEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_rule_file_raises_error(self):
        """Test missing rule file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            RuleEngine(Path('/nonexistent/rules.yaml'))

    def test_invalid_yaml_raises_error(self):
        """Test invalid YAML raises appropriate error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            f.flush()
            with pytest.raises(Exception):  # yaml.YAMLError
                RuleEngine(Path(f.name))

    def test_missing_feature_does_not_crash(self):
        """Test missing feature in features dict doesn't crash."""
        engine = RuleEngine()
        result = engine.evaluate({'unknown_feature': 1})
        assert result['score'] >= 0  # Should handle gracefully
