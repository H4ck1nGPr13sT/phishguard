"""Cross-paradigm disagreement detection using normalized Shannon entropy.

Extends Phase 3 classifier disagreement approach to detect disagreements
between the three paradigms: ML ensemble, rule-based, and Bayesian.

Key differences from classifier disagreement:
- 3 paradigms vs 7 classifiers
- Max entropy for 3 paradigms: log2(3) = 1.585
- Different probability scales (ML proba, rule score, Bayesian posterior)
"""

import numpy as np
from scipy.stats import entropy
from typing import Dict, List, Tuple

# Threshold for edge case detection (consistent with Phase 3)
PARADIGM_DISAGREEMENT_THRESHOLD = 0.7


def calculate_paradigm_disagreement(
    ml_prediction: str,
    ml_probability: float,
    rule_prediction: str,
    rule_probability: float,
    bayesian_prediction: str,
    bayesian_probability: float
) -> Dict:
    """Calculate disagreement across three paradigms.

    Args:
        ml_prediction: 'phishing' or 'legitimate' from ML ensemble
        ml_probability: Phishing probability from ML (0-1)
        rule_prediction: 'phishing' or 'legitimate' from rules
        rule_probability: Rule score (0-1)
        bayesian_prediction: 'phishing' or 'legitimate' from Bayesian
        bayesian_probability: Posterior phishing probability (0-1)

    Returns:
        Dict with:
            'score': Normalized entropy (0-1)
            'is_edge_case': True if score > threshold
            'vote_distribution': {'phishing': N, 'legitimate': M}
            'probability_variance': Variance across paradigm probabilities
            'disagreeing_paradigms': List of paradigms disagreeing with majority
            'probability_spread': Max - min probability across paradigms
    """
    predictions = {
        'ml_ensemble': ml_prediction,
        'rules': rule_prediction,
        'bayesian': bayesian_prediction
    }
    probabilities = [ml_probability, rule_probability, bayesian_probability]

    # Count votes
    votes = {}
    for paradigm, pred in predictions.items():
        votes[pred] = votes.get(pred, 0) + 1

    # Convert to binary for entropy calculation
    binary_preds = [1 if pred == 'phishing' else 0
                   for pred in predictions.values()]

    # Calculate normalized Shannon entropy
    unique, counts = np.unique(binary_preds, return_counts=True)
    pk = counts / len(binary_preds)

    H = entropy(pk, base=2)
    max_H = np.log2(3)  # 3 paradigms, max entropy = log2(3)
    disagreement_score = H / max_H if max_H > 0 else 0.0

    # Identify majority and dissenters
    majority_pred = max(votes.items(), key=lambda x: x[1])[0]
    disagreeing = [paradigm for paradigm, pred in predictions.items()
                  if pred != majority_pred]

    # Probability variance and spread
    prob_variance = float(np.var(probabilities))
    prob_spread = float(max(probabilities) - min(probabilities))

    return {
        'score': float(disagreement_score),
        'is_edge_case': disagreement_score > PARADIGM_DISAGREEMENT_THRESHOLD,
        'vote_distribution': votes,
        'probability_variance': prob_variance,
        'disagreeing_paradigms': disagreeing,
        'probability_spread': prob_spread,
        'paradigm_probabilities': {
            'ml_ensemble': ml_probability,
            'rules': rule_probability,
            'bayesian': bayesian_probability
        }
    }


def get_disagreement_explanation(disagreement_info: Dict) -> str:
    """Generate human-readable explanation of paradigm disagreement.

    Args:
        disagreement_info: Result from calculate_paradigm_disagreement()

    Returns:
        String explanation of disagreement pattern
    """
    score = disagreement_info['score']
    dissenters = disagreement_info['disagreeing_paradigms']
    votes = disagreement_info['vote_distribution']
    probs = disagreement_info['paradigm_probabilities']

    if score < 0.3:
        return "All paradigms agree on the prediction."

    if score < 0.7:
        majority = max(votes.items(), key=lambda x: x[1])[0]
        return (
            f"Minor disagreement: {dissenters} predicts differently. "
            f"Majority ({2}/3) predicts {majority}."
        )

    # High disagreement
    prob_details = ", ".join(
        f"{p}={v:.1%}" for p, v in probs.items()
    )
    return (
        f"High paradigm disagreement (score={score:.2f}). "
        f"Probabilities: {prob_details}. "
        f"Consider manual review."
    )
