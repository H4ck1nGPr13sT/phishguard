"""Rule-based phishing detection engine with weighted scoring.

This module implements the RuleEngine class that:
1. Loads phishing detection rules from YAML
2. Validates rules using Pydantic models
3. Evaluates URL features against all rules
4. Aggregates weighted scores with explanations

The engine provides interpretable detection with detailed information
about which rules fired and what values triggered them.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.paradigms.rules.definitions import RuleSet, PhishingRule, RuleCondition

logger = logging.getLogger(__name__)


class RuleEngine:
    """Weighted rule engine for phishing URL detection.
    
    Loads rules from YAML, evaluates them against extracted URL features,
    and returns structured results with scores and explanations.
    
    Example:
        >>> engine = RuleEngine()
        >>> features = extract_url_features('http://192.168.1.1/login')
        >>> result = engine.evaluate(features, raw_url='http://192.168.1.1/login')
        >>> print(f"Score: {result['score']:.2f}")
        Score: 0.50
        >>> print(f"Prediction: {result['prediction']}")
        Prediction: phishing
    """
    
    def __init__(self, rules_path: Optional[Path] = None):
        """Initialize RuleEngine with rules from YAML file.
        
        Args:
            rules_path: Path to YAML rules file. If None, uses default
                       phishing_rules.yaml in same directory as this module.
        
        Raises:
            FileNotFoundError: If rules file doesn't exist
            ValidationError: If rules don't match Pydantic schema
        """
        if rules_path is None:
            # Default to phishing_rules.yaml in same directory
            rules_path = Path(__file__).parent / 'phishing_rules.yaml'
        else:
            rules_path = Path(rules_path)
        
        if not rules_path.exists():
            raise FileNotFoundError(f"Rules file not found: {rules_path}")
        
        # Load and validate rules
        with open(rules_path, 'r') as f:
            rules_data = yaml.safe_load(f)
        
        # Validate with Pydantic (will raise ValidationError if invalid)
        self.ruleset = RuleSet(**rules_data)
        
        logger.info(f"Loaded {len(self.ruleset.rules)} rules from {rules_path}")
        logger.info(f"Rule version: {self.ruleset.version}")
    
    def evaluate(self, features: Dict[str, Any], raw_url: Optional[str] = None) -> Dict:
        """Evaluate all rules against extracted URL features.
        
        Args:
            features: Dict from extract_url_features() with 30 numeric features
            raw_url: Optional raw URL string for keyword_match evaluation
        
        Returns:
            Dict with:
                'score': float (0.0-1.0, capped) - total weighted score
                'prediction': str - 'phishing' or 'legitimate' (threshold 0.5)
                'confidence': float - distance from threshold (0.0-0.5)
                'fired_rules': list of dicts with name, description, weight, matched_values
                'rule_count': int - number of rules that fired
                'max_possible_score': float - sum of all rule weights
        
        Example:
            >>> result = engine.evaluate(features, raw_url='http://phish.tk/verify')
            >>> print(result['fired_rules'])
            [
                {
                    'name': 'suspicious_tld',
                    'description': 'URL uses suspicious top-level domain',
                    'weight': 0.25,
                    'matched_values': ['has_suspicious_tld=1']
                },
                {
                    'name': 'urgent_keywords',
                    'description': 'URL contains urgent/pressure keywords',
                    'weight': 0.20,
                    'matched_values': ['verify']
                }
            ]
        """
        # Handle empty features
        if not features:
            return self._empty_result()
        
        fired_rules = []
        total_score = 0.0
        
        # Evaluate each rule
        for rule in self.ruleset.rules:
            result = self._evaluate_rule(rule, features, raw_url)
            if result['fired']:
                fired_rules.append({
                    'name': rule.name,
                    'description': rule.description,
                    'weight': rule.weight,
                    'category': rule.category,
                    'matched_values': result['matched_values']
                })
                total_score += rule.weight
        
        # Normalize score to [0, 1] range
        normalized_score = min(total_score, 1.0)
        
        # Make prediction with 0.5 threshold
        prediction = 'phishing' if normalized_score >= 0.5 else 'legitimate'
        
        # Calculate confidence as distance from threshold
        confidence = abs(normalized_score - 0.5)
        
        max_possible_score = sum(rule.weight for rule in self.ruleset.rules)
        
        return {
            'score': normalized_score,
            'prediction': prediction,
            'confidence': confidence,
            'fired_rules': fired_rules,
            'rule_count': len(fired_rules),
            'max_possible_score': max_possible_score
        }
    
    def _evaluate_rule(self, rule: PhishingRule, features: Dict[str, Any], 
                      raw_url: Optional[str]) -> Dict[str, Any]:
        """Evaluate a single rule against features.
        
        Args:
            rule: PhishingRule to evaluate
            features: Feature dictionary
            raw_url: Optional raw URL for keyword matching
        
        Returns:
            Dict with 'fired' (bool) and 'matched_values' (list)
        """
        condition = rule.condition
        
        try:
            if condition.type == 'keyword_match':
                return self._evaluate_keyword_match(condition, raw_url)
            elif condition.type == 'feature_check':
                return self._evaluate_feature_check(condition, features)
            elif condition.type == 'domain_match':
                return self._evaluate_domain_match(condition, features, raw_url)
            else:
                logger.warning(f"Unknown condition type: {condition.type}")
                return {'fired': False, 'matched_values': []}
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.name}: {e}")
            return {'fired': False, 'matched_values': []}
    
    def _evaluate_keyword_match(self, condition: RuleCondition, 
                               raw_url: Optional[str]) -> Dict[str, Any]:
        """Evaluate keyword_match condition.
        
        Checks if any keyword in condition.keywords appears in raw_url
        (case-insensitive substring match).
        
        Args:
            condition: RuleCondition with type='keyword_match'
            raw_url: Raw URL string to check
        
        Returns:
            Dict with 'fired' and 'matched_values' (list of matched keywords)
        """
        if not raw_url or not condition.keywords:
            return {'fired': False, 'matched_values': []}
        
        url_lower = raw_url.lower()
        matched = [kw for kw in condition.keywords if kw.lower() in url_lower]
        
        return {
            'fired': len(matched) > 0,
            'matched_values': matched
        }
    
    def _evaluate_feature_check(self, condition: RuleCondition, 
                                features: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate feature_check condition.
        
        Compares feature value using operator (equals, greater_than, less_than, contains).
        
        Args:
            condition: RuleCondition with type='feature_check'
            features: Feature dictionary
        
        Returns:
            Dict with 'fired' and 'matched_values' (description of match)
        """
        if condition.feature not in features:
            return {'fired': False, 'matched_values': []}
        
        feature_value = features[condition.feature]
        target_value = condition.value
        operator = condition.operator
        
        fired = False
        if operator == 'equals':
            fired = feature_value == target_value
        elif operator == 'greater_than':
            fired = feature_value > target_value
        elif operator == 'less_than':
            fired = feature_value < target_value
        elif operator == 'contains':
            # For string features
            if isinstance(feature_value, str) and isinstance(target_value, str):
                fired = target_value.lower() in feature_value.lower()
        
        matched_values = []
        if fired:
            matched_values = [f"{condition.feature}={feature_value}"]
        
        return {
            'fired': fired,
            'matched_values': matched_values
        }
    
    def _evaluate_domain_match(self, condition: RuleCondition, 
                               features: Dict[str, Any],
                               raw_url: Optional[str]) -> Dict[str, Any]:
        """Evaluate domain_match condition.
        
        Checks if URL domain matches any in condition.domains list.
        For URL shorteners and known domains.
        
        Args:
            condition: RuleCondition with type='domain_match'
            features: Feature dictionary
            raw_url: Raw URL for domain extraction
        
        Returns:
            Dict with 'fired' and 'matched_values' (list of matched domains)
        """
        if not raw_url or not condition.domains:
            return {'fired': False, 'matched_values': []}
        
        url_lower = raw_url.lower()
        
        # Check if any of the domains appear in the URL
        # This handles both exact domain matches and domains within the URL
        matched = [domain for domain in condition.domains 
                  if domain.lower() in url_lower]
        
        return {
            'fired': len(matched) > 0,
            'matched_values': matched
        }
    
    def _empty_result(self) -> Dict:
        """Return empty result for invalid/empty inputs."""
        return {
            'score': 0.0,
            'prediction': 'legitimate',
            'confidence': 0.5,
            'fired_rules': [],
            'rule_count': 0,
            'max_possible_score': sum(rule.weight for rule in self.ruleset.rules)
        }
