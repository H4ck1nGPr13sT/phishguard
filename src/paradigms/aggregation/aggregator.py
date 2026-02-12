"""Multi-paradigm aggregation layer for phishing detection.

Combines predictions from:
- ML ensemble (7 classifiers with weighted voting)
- Rule-based expert system (weighted rule scoring)
- Bayesian probabilistic classifier (posterior probabilities)

Produces final verdict with configurable paradigm weights and
cross-paradigm disagreement detection.
"""

from typing import Dict, Optional
import logging

from src.paradigms.aggregation.weights import ParadigmWeights, DEFAULT_WEIGHTS
from src.paradigms.aggregation.disagreement import (
    calculate_paradigm_disagreement,
    get_disagreement_explanation
)

logger = logging.getLogger(__name__)


class MultiParadigmAggregator:
    """Aggregates predictions from ML, rule-based, and Bayesian paradigms.

    The aggregator:
    1. Receives prediction results from each paradigm
    2. Applies configurable weights to combine probabilities
    3. Detects cross-paradigm disagreements
    4. Produces final verdict with confidence and explanations

    Example:
        >>> aggregator = MultiParadigmAggregator()
        >>> result = aggregator.aggregate(
        ...     ml_result={'ensemble_probability': 0.85, 'prediction': 'phishing'},
        ...     rule_result={'score': 0.6, 'prediction': 'phishing', 'fired_rules': [...]},
        ...     bayesian_result={'posterior_phishing': 0.75, 'prediction': 'phishing'}
        ... )
        >>> print(result['final_prediction'])
        'phishing'
    """

    def __init__(self, weights: Optional[ParadigmWeights] = None):
        """Initialize aggregator with paradigm weights.

        Args:
            weights: ParadigmWeights instance. Uses defaults if None.
                     Defaults: ML=0.5, Rules=0.3, Bayesian=0.2
        """
        self.weights = weights or DEFAULT_WEIGHTS
        logger.info(f"Aggregator initialized with weights: {self.weights.to_dict()}")

    def aggregate(
        self,
        ml_result: Dict,
        rule_result: Dict,
        bayesian_result: Dict
    ) -> Dict:
        """Aggregate predictions from all three paradigms.

        Args:
            ml_result: Dict with keys:
                - 'ensemble_probability': float (0-1)
                - 'prediction': 'phishing' or 'legitimate'
                - 'individual_predictions': optional list of classifier results

            rule_result: Dict with keys:
                - 'score': float (0-1)
                - 'prediction': 'phishing' or 'legitimate'
                - 'fired_rules': list of rule dicts
                - 'rule_count': int

            bayesian_result: Dict with keys:
                - 'posterior_phishing': float (0-1)
                - 'prediction': 'phishing' or 'legitimate'
                - 'confidence': float
                - 'prior_info': optional dict

        Returns:
            Dict with:
                - 'final_prediction': 'phishing' or 'legitimate'
                - 'final_probability': float (0-1)
                - 'confidence': float
                - 'paradigm_contributions': dict with each paradigm's contribution
                - 'disagreement': dict with cross-paradigm disagreement info
                - 'active_rules': list of fired rules from rule engine
                - 'explanation': human-readable summary
        """
        # Extract probabilities from each paradigm
        ml_prob = ml_result.get('ensemble_probability', 0.5)
        rule_prob = rule_result.get('score', 0.0)
        bayes_prob = bayesian_result.get('posterior_phishing', 0.5)

        # Extract predictions
        ml_pred = ml_result.get('prediction', 'legitimate')
        rule_pred = rule_result.get('prediction', 'legitimate')
        bayes_pred = bayesian_result.get('prediction', 'legitimate')

        # Weighted aggregation
        final_probability = (
            self.weights.ml_ensemble * ml_prob +
            self.weights.rules * rule_prob +
            self.weights.bayesian * bayes_prob
        )

        # Final prediction based on 0.5 threshold
        final_prediction = 'phishing' if final_probability > 0.5 else 'legitimate'

        # Calculate confidence (distance from threshold, scaled to 0.5-1.0)
        confidence = 0.5 + abs(final_probability - 0.5)

        # Calculate cross-paradigm disagreement
        disagreement_info = calculate_paradigm_disagreement(
            ml_pred, ml_prob,
            rule_pred, rule_prob,
            bayes_pred, bayes_prob
        )

        # Generate explanation
        explanation = self._generate_explanation(
            final_prediction,
            final_probability,
            ml_prob,
            rule_prob,
            bayes_prob,
            rule_result.get('fired_rules', []),
            disagreement_info
        )

        return {
            'final_prediction': final_prediction,
            'final_probability': float(final_probability),
            'confidence': float(confidence),
            'paradigm_contributions': {
                'ml_ensemble': {
                    'probability': float(ml_prob),
                    'weight': self.weights.ml_ensemble,
                    'weighted_contribution': float(ml_prob * self.weights.ml_ensemble),
                    'prediction': ml_pred
                },
                'rules': {
                    'probability': float(rule_prob),
                    'weight': self.weights.rules,
                    'weighted_contribution': float(rule_prob * self.weights.rules),
                    'prediction': rule_pred,
                    'rule_count': rule_result.get('rule_count', 0)
                },
                'bayesian': {
                    'probability': float(bayes_prob),
                    'weight': self.weights.bayesian,
                    'weighted_contribution': float(bayes_prob * self.weights.bayesian),
                    'prediction': bayes_pred
                }
            },
            'disagreement': disagreement_info,
            'active_rules': rule_result.get('fired_rules', []),
            'explanation': explanation
        }

    def _generate_explanation(
        self,
        final_prediction: str,
        final_prob: float,
        ml_prob: float,
        rule_prob: float,
        bayes_prob: float,
        fired_rules: list,
        disagreement_info: Dict
    ) -> str:
        """Generate human-readable explanation of aggregated prediction."""
        parts = []

        # Overall verdict
        confidence_level = (
            "high" if final_prob > 0.8 or final_prob < 0.2 else
            "moderate" if final_prob > 0.65 or final_prob < 0.35 else
            "low"
        )
        parts.append(
            f"Prediction: {final_prediction.upper()} "
            f"({final_prob:.1%} probability, {confidence_level} confidence)"
        )

        # Paradigm summary
        paradigm_summary = (
            f"ML ensemble: {ml_prob:.1%}, "
            f"Rules: {rule_prob:.1%}, "
            f"Bayesian: {bayes_prob:.1%}"
        )
        parts.append(f"Paradigm scores: {paradigm_summary}")

        # Active rules if any
        if fired_rules:
            rule_names = [r['name'] for r in fired_rules[:3]]  # Top 3
            if len(fired_rules) > 3:
                rule_names.append(f"...+{len(fired_rules)-3} more")
            parts.append(f"Active rules: {', '.join(rule_names)}")

        # Disagreement warning
        if disagreement_info['is_edge_case']:
            parts.append(
                f"WARNING: High paradigm disagreement "
                f"(score={disagreement_info['score']:.2f}). "
                f"Manual review recommended."
            )

        return " | ".join(parts)

    def update_weights(self, weights: ParadigmWeights) -> None:
        """Update paradigm weights."""
        self.weights = weights
        logger.info(f"Weights updated to: {weights.to_dict()}")
