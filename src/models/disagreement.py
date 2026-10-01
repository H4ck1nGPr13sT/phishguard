"""Disagreement detection using normalized Shannon entropy.

This module calculates disagreement scores across ensemble classifiers
to detect edge cases where classifiers disagree on predictions.
"""

import numpy as np
from scipy.stats import entropy
from typing import Dict

# Configurable threshold for edge case detection
DISAGREEMENT_THRESHOLD = 0.7


def calculate_disagreement(individual_predictions: dict) -> float:
    """Calculate normalized Shannon entropy across classifier predictions.

    Args:
        individual_predictions: Dict from get_individual_predictions()
            {'rf': {'phishing_probability': 0.8, ...}, 'svm': {...}, ...}

    Returns:
        float: Disagreement score 0-1 where:
            0 = all classifiers agree (unanimous vote)
            1 = maximum disagreement (even split)

    Example:
        >>> preds = {
        ...     'rf': {'phishing_probability': 0.9},
        ...     'svm': {'phishing_probability': 0.1}
        ... }
        >>> score = calculate_disagreement(preds)
        >>> score
        1.0  # Maximum disagreement for 2 classifiers
    """
    if not individual_predictions:
        return 0.0

    # Extract binary predictions (0 or 1 based on >0.5 threshold)
    predictions = []
    for classifier_name, pred_data in individual_predictions.items():
        phishing_proba = pred_data['phishing_probability']
        binary_pred = 1 if phishing_proba >= 0.5 else 0
        predictions.append(binary_pred)

    predictions = np.array(predictions)

    # Count votes for each class
    unique_votes, counts = np.unique(predictions, return_counts=True)

    # Normalize to probability distribution
    pk = counts / len(predictions)

    # Calculate Shannon entropy with base=2 (bits)
    H = entropy(pk, base=2)

    # Normalize by the maximum entropy of the BINARY vote distribution.
    # Votes take at most 2 values (phishing / legitimate), so the maximum
    # Shannon entropy is log2(2) = 1 bit, independent of the number of voters.
    #
    # NOTE: dividing by log2(n_classifiers) was a defect — it made the score
    # unreachably small for n > 2. With 7 classifiers the most even split (4/3)
    # gave only 0.351, and with 3 paradigms (2/1) only 0.579, so the 0.7
    # edge-case threshold could never be crossed and is_edge_case was always
    # False. Normalizing by the number of CLASSES (2) fixes this: the score is
    # now the standard normalized binary entropy in [0, 1], reaching ~0.985 for
    # a 4/3 split of 7 votes and ~0.918 for a 2/1 split of 3 votes.
    n_classifiers = len(predictions)
    max_H = 1.0 if n_classifiers > 1 else 0.0  # log2(2) = 1 (two vote classes)

    # Return normalized entropy
    if max_H > 0:
        normalized_entropy = H / max_H
    else:
        normalized_entropy = 0.0

    return float(normalized_entropy)


def is_edge_case(disagreement_score: float, threshold: float = DISAGREEMENT_THRESHOLD) -> bool:
    """Check if disagreement score indicates an edge case.

    Args:
        disagreement_score: Normalized entropy from calculate_disagreement()
        threshold: Threshold for edge case detection (default: 0.7)

    Returns:
        bool: True if disagreement exceeds threshold

    Example:
        >>> is_edge_case(0.85)
        True
        >>> is_edge_case(0.3)
        False
    """
    return disagreement_score > threshold


def get_disagreement_summary(individual_predictions: dict) -> dict:
    """Get detailed disagreement analysis.

    Args:
        individual_predictions: Dict from get_individual_predictions()

    Returns:
        dict with:
            - score: normalized entropy (0-1)
            - is_edge_case: bool
            - vote_distribution: {'phishing': N, 'legitimate': M}
            - agreeing_classifiers: list of classifier names that agree with majority
            - dissenting_classifiers: list of classifier names that disagree

    Example:
        >>> preds = {
        ...     'rf': {'phishing_probability': 0.9, 'prediction': 'phishing'},
        ...     'svm': {'phishing_probability': 0.8, 'prediction': 'phishing'},
        ...     'mlp': {'phishing_probability': 0.2, 'prediction': 'legitimate'}
        ... }
        >>> summary = get_disagreement_summary(preds)
        >>> summary['vote_distribution']
        {'phishing': 2, 'legitimate': 1}
        >>> summary['agreeing_classifiers']
        ['rf', 'svm']
    """
    if not individual_predictions:
        return {
            'score': 0.0,
            'is_edge_case': False,
            'vote_distribution': {},
            'agreeing_classifiers': [],
            'dissenting_classifiers': []
        }

    # Calculate disagreement score
    score = calculate_disagreement(individual_predictions)

    # Count votes by prediction
    votes = {}
    classifier_votes = {}

    for classifier_name, pred_data in individual_predictions.items():
        prediction = pred_data['prediction']
        votes[prediction] = votes.get(prediction, 0) + 1
        classifier_votes[classifier_name] = prediction

    # Determine majority prediction
    if votes:
        majority_prediction = max(votes.items(), key=lambda x: x[1])[0]
    else:
        majority_prediction = None

    # Identify agreeing and dissenting classifiers
    agreeing = []
    dissenting = []

    for classifier_name, prediction in classifier_votes.items():
        if prediction == majority_prediction:
            agreeing.append(classifier_name)
        else:
            dissenting.append(classifier_name)

    return {
        'score': float(score),
        'is_edge_case': is_edge_case(score),
        'vote_distribution': votes,
        'agreeing_classifiers': sorted(agreeing),
        'dissenting_classifiers': sorted(dissenting)
    }
