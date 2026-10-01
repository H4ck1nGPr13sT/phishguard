"""Tests for disagreement detection module.

Tests the calculation of disagreement scores using normalized Shannon entropy
and edge case detection functionality.
"""

import pytest
import numpy as np
from src.models.disagreement import (
    calculate_disagreement,
    is_edge_case,
    get_disagreement_summary,
    DISAGREEMENT_THRESHOLD,
)


class TestCalculateDisagreement:
    """Tests for calculate_disagreement function."""

    def test_calculate_disagreement_perfect_agreement(self):
        """All classifiers agree -> score = 0.0"""
        # All classifiers predict phishing with high probability
        predictions = {
            "rf": {"phishing_probability": 0.9},
            "svm": {"phishing_probability": 0.85},
            "mlp": {"phishing_probability": 0.92},
            "xgb": {"phishing_probability": 0.88},
            "lr": {"phishing_probability": 0.91},
            "nb": {"phishing_probability": 0.87},
            "dt": {"phishing_probability": 0.89},
        }
        score = calculate_disagreement(predictions)
        assert score == 0.0, f"Perfect agreement should yield 0.0, got {score}"

    def test_calculate_disagreement_maximum_disagreement(self):
        """Near-even split (4-3) -> score ~0.985 (normalized binary entropy).

        Binary votes are normalized by the maximum BINARY entropy log2(2)=1,
        not by log2(n_classifiers). A 4-3 split of 7 votes is the most even
        possible and yields H = -(4/7*log2(4/7) + 3/7*log2(3/7)) ~= 0.985, the
        maximum reachable disagreement for 7 classifiers.
        """
        predictions = {
            "rf": {"phishing_probability": 0.9},  # phishing
            "svm": {"phishing_probability": 0.85},  # phishing
            "mlp": {"phishing_probability": 0.8},  # phishing
            "xgb": {"phishing_probability": 0.75},  # phishing
            "lr": {"phishing_probability": 0.2},  # legitimate
            "nb": {"phishing_probability": 0.3},  # legitimate
            "dt": {"phishing_probability": 0.1},  # legitimate
        }
        score = calculate_disagreement(predictions)
        assert 0.98 < score < 0.99, f"4-3 split should yield ~0.985, got {score}"
        assert is_edge_case(score), "4-3 split must be an edge case (> 0.7 threshold)"

    def test_calculate_disagreement_partial_agreement(self):
        """5-2 split -> 0 < score < 0.35"""
        # 5 classifiers predict phishing, 2 predict legitimate
        predictions = {
            "rf": {"phishing_probability": 0.9},  # phishing
            "svm": {"phishing_probability": 0.85},  # phishing
            "mlp": {"phishing_probability": 0.8},  # phishing
            "xgb": {"phishing_probability": 0.75},  # phishing
            "lr": {"phishing_probability": 0.7},  # phishing
            "nb": {"phishing_probability": 0.3},  # legitimate
            "dt": {"phishing_probability": 0.2},  # legitimate
        }
        score = calculate_disagreement(predictions)
        # 5-2 split: H(2/7) ~= 0.863, lower than the 4-3 split (~0.985) but still
        # above the 0.7 edge-case threshold (>= 2 dissenting classifiers).
        assert 0.85 < score < 0.88, f"5-2 split should yield ~0.863, got {score}"
        assert score < 0.985, "5-2 split must be below the most-even 4-3 split"
        assert is_edge_case(score), "5-2 split (2 dissenters) is an edge case"

    def test_disagreement_with_single_classifier(self):
        """Single classifier should return 0.0"""
        predictions = {"rf": {"phishing_probability": 0.9}}
        score = calculate_disagreement(predictions)
        assert score == 0.0, f"Single classifier should yield 0.0, got {score}"

    def test_disagreement_with_empty_predictions(self):
        """Empty predictions should return 0.0"""
        predictions = {}
        score = calculate_disagreement(predictions)
        assert score == 0.0, f"Empty predictions should yield 0.0, got {score}"

    def test_disagreement_two_classifiers_even_split(self):
        """Two classifiers with even split (1-1) -> score = 1.0"""
        predictions = {
            "rf": {"phishing_probability": 0.9},  # phishing
            "svm": {"phishing_probability": 0.1},  # legitimate
        }
        score = calculate_disagreement(predictions)
        assert score == 1.0, f"Even split for 2 classifiers should yield 1.0, got {score}"


class TestIsEdgeCase:
    """Tests for is_edge_case function."""

    def test_is_edge_case_above_threshold(self):
        """Score > 0.7 returns True"""
        assert is_edge_case(0.85) == True
        assert is_edge_case(0.71) == True
        assert is_edge_case(1.0) == True

    def test_is_edge_case_below_threshold(self):
        """Score < 0.7 returns False"""
        assert is_edge_case(0.3) == False
        assert is_edge_case(0.69) == False
        assert is_edge_case(0.0) == False

    def test_is_edge_case_at_threshold(self):
        """Score = 0.7 returns False (not exceeding)"""
        assert is_edge_case(0.7) == False

    def test_is_edge_case_custom_threshold(self):
        """Custom threshold works correctly"""
        assert is_edge_case(0.6, threshold=0.5) == True
        assert is_edge_case(0.4, threshold=0.5) == False


class TestGetDisagreementSummary:
    """Tests for get_disagreement_summary function."""

    def test_get_disagreement_summary_fields(self):
        """Returns all required fields"""
        predictions = {
            "rf": {"phishing_probability": 0.9, "prediction": "phishing"},
            "svm": {"phishing_probability": 0.8, "prediction": "phishing"},
            "mlp": {"phishing_probability": 0.2, "prediction": "legitimate"},
        }
        summary = get_disagreement_summary(predictions)

        # Check all required fields exist
        assert "score" in summary
        assert "is_edge_case" in summary
        assert "vote_distribution" in summary
        assert "agreeing_classifiers" in summary
        assert "dissenting_classifiers" in summary

        # Check types
        assert isinstance(summary["score"], float)
        assert isinstance(summary["is_edge_case"], bool)
        assert isinstance(summary["vote_distribution"], dict)
        assert isinstance(summary["agreeing_classifiers"], list)
        assert isinstance(summary["dissenting_classifiers"], list)

    def test_get_disagreement_summary_vote_distribution(self):
        """Vote distribution counts correctly"""
        predictions = {
            "rf": {"phishing_probability": 0.9, "prediction": "phishing"},
            "svm": {"phishing_probability": 0.8, "prediction": "phishing"},
            "mlp": {"phishing_probability": 0.2, "prediction": "legitimate"},
        }
        summary = get_disagreement_summary(predictions)

        assert summary["vote_distribution"]["phishing"] == 2
        assert summary["vote_distribution"]["legitimate"] == 1

    def test_get_disagreement_summary_agreeing_dissenting(self):
        """Agreeing and dissenting classifiers identified correctly"""
        predictions = {
            "rf": {"phishing_probability": 0.9, "prediction": "phishing"},
            "svm": {"phishing_probability": 0.8, "prediction": "phishing"},
            "mlp": {"phishing_probability": 0.75, "prediction": "phishing"},
            "xgb": {"phishing_probability": 0.2, "prediction": "legitimate"},
        }
        summary = get_disagreement_summary(predictions)

        # Majority is phishing (3 votes)
        assert set(summary["agreeing_classifiers"]) == {"mlp", "rf", "svm"}
        assert summary["dissenting_classifiers"] == ["xgb"]

    def test_get_disagreement_summary_empty_predictions(self):
        """Empty predictions handled gracefully"""
        predictions = {}
        summary = get_disagreement_summary(predictions)

        assert summary["score"] == 0.0
        assert summary["is_edge_case"] == False
        assert summary["vote_distribution"] == {}
        assert summary["agreeing_classifiers"] == []
        assert summary["dissenting_classifiers"] == []

    def test_get_disagreement_summary_edge_case_detection(self):
        """Edge case flag set correctly based on threshold.

        With binary votes normalized by log2(2)=1, a 4-3 split of 7
        classifiers scores ~0.985 and IS flagged as an edge case (> 0.7),
        while a unanimous vote scores 0.0 and is not. A single dissenter
        (6-1, score ~0.592) stays below the threshold.
        """
        # High disagreement (4-3 split) - above 0.7 threshold
        predictions_moderate = {
            f"clf{i}": {
                "phishing_probability": 0.9 if i < 4 else 0.1,
                "prediction": "phishing" if i < 4 else "legitimate",
            }
            for i in range(7)
        }
        summary_moderate = get_disagreement_summary(predictions_moderate)
        assert summary_moderate["is_edge_case"] == True

        # A single dissenter (6-1 split, ~0.592) stays below the threshold
        predictions_one_dissenter = {
            f"clf{i}": {
                "phishing_probability": 0.9 if i < 6 else 0.1,
                "prediction": "phishing" if i < 6 else "legitimate",
            }
            for i in range(7)
        }
        assert get_disagreement_summary(predictions_one_dissenter)["is_edge_case"] == False

        # Low disagreement (all agree)
        predictions_low = {
            f"clf{i}": {"phishing_probability": 0.9, "prediction": "phishing"}
            for i in range(7)
        }
        summary_low = get_disagreement_summary(predictions_low)
        assert summary_low["is_edge_case"] == False

        # Test that threshold can be adjusted to trigger edge cases
        predictions_4_3 = {
            f"clf{i}": {
                "phishing_probability": 0.9 if i < 4 else 0.1,
                "prediction": "phishing" if i < 4 else "legitimate",
            }
            for i in range(7)
        }
        # With lower threshold (0.3), 4-3 split (~0.35) should be edge case
        score = calculate_disagreement(predictions_4_3)
        assert is_edge_case(score, threshold=0.3) == True


class TestDisagreementVoteDistributions:
    """Sweep every possible vote split to document the measure's range and
    the reachability of the edge-case threshold (review finding U1)."""

    def test_seven_classifier_distributions(self):
        from src.models.disagreement import DISAGREEMENT_THRESHOLD
        expected_edge = {0: False, 1: False, 2: True, 3: True,
                         4: True, 5: True, 6: False, 7: False}
        max_score = 0.0
        for k in range(8):
            preds = {f"c{i}": {"phishing_probability": 0.9 if i < k else 0.1,
                               "prediction": "phishing" if i < k else "legitimate"}
                     for i in range(7)}
            s = calculate_disagreement(preds)
            max_score = max(max_score, s)
            assert is_edge_case(s) == expected_edge[k], (
                f"{k}/7 split: score={s:.4f}, edge={is_edge_case(s)}")
        # The most-even 4-3 split is the reachable maximum (~0.985); the 0.7
        # threshold is genuinely reachable (regression guard against the old
        # log2(n) normalization bug that capped the max at 0.351).
        assert 0.98 < max_score < 1.0
        assert max_score > DISAGREEMENT_THRESHOLD

    def test_three_paradigm_distributions(self):
        from src.paradigms.aggregation.disagreement import calculate_paradigm_disagreement
        # Any non-unanimous 3-paradigm vote scores ~0.918 and is flagged;
        # unanimous votes score 0.0.
        cases = [
            (("phishing", "phishing", "phishing"), False),
            (("phishing", "phishing", "legitimate"), True),
            (("phishing", "legitimate", "legitimate"), True),
            (("legitimate", "legitimate", "legitimate"), False),
        ]
        for (ml, ru, ba), expected in cases:
            r = calculate_paradigm_disagreement(
                ml, 0.9 if ml == "phishing" else 0.1,
                ru, 0.9 if ru == "phishing" else 0.1,
                ba, 0.9 if ba == "phishing" else 0.1)
            assert r["is_edge_case"] == expected, (ml, ru, ba, r["score"])
            if expected:
                assert 0.91 < r["score"] < 0.92
