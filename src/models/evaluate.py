"""Model evaluation module for comprehensive performance metrics.

This module provides functions to evaluate trained models with all required
metrics: accuracy, precision, recall, F1, AUC-ROC, and confusion matrix.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Union

import matplotlib

matplotlib.use("Agg")  # Must precede any pyplot import (non-interactive backend, Pitfall 2)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report
)
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)


def evaluate_model(
    model: Pipeline,
    X_test: pd.DataFrame,
    y_test: pd.Series
) -> Dict[str, Any]:
    """Comprehensive model evaluation matching requirements EVAL-01, EVAL-02, EVAL-03.

    Args:
        model: Trained sklearn Pipeline
        X_test: Test features
        y_test: Test labels

    Returns:
        Dict with:
        - accuracy, precision, recall, f1_score, roc_auc
        - confusion_matrix: {true_negative, false_positive, false_negative, true_positive}
        - classification_report: detailed per-class metrics

    Example:
        >>> model = load_model(Path('models/rf_pipeline.joblib'))
        >>> metrics = evaluate_model(model, X_test, y_test)
        >>> print(f"Accuracy: {metrics['accuracy']:.4f}")
        >>> print_evaluation_report(metrics)
    """
    logger.info("Evaluating model on test data...")

    # Get predictions and probabilities
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]  # Probability of phishing class (1)

    # Calculate all metrics
    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred, zero_division=0),
        'recall': recall_score(y_test, y_pred, zero_division=0),
        'f1_score': f1_score(y_test, y_pred, zero_division=0),
        'roc_auc': roc_auc_score(y_test, y_proba)
    }

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    metrics['confusion_matrix'] = {
        'true_negative': int(cm[0, 0]),
        'false_positive': int(cm[0, 1]),
        'false_negative': int(cm[1, 0]),
        'true_positive': int(cm[1, 1])
    }

    # Classification report (string format)
    metrics['classification_report'] = classification_report(
        y_test,
        y_pred,
        target_names=['Legitimate', 'Phishing'],
        zero_division=0
    )

    # Test data metadata
    metrics['test_samples'] = len(X_test)

    logger.info(f"Evaluation complete: accuracy={metrics['accuracy']:.4f}")

    return metrics


def print_evaluation_report(metrics: Dict[str, Any]) -> None:
    """Print formatted evaluation report for thesis documentation.

    Args:
        metrics: Metrics dictionary from evaluate_model()

    Example:
        >>> metrics = evaluate_model(model, X_test, y_test)
        >>> print_evaluation_report(metrics)
        ============================================================
        MODEL EVALUATION REPORT
        ============================================================
        Accuracy:  0.9234
        Precision: 0.9012
        ...
    """
    print("=" * 80)
    print("MODEL EVALUATION REPORT")
    print("=" * 80)
    print(f"Test samples: {metrics['test_samples']}")
    print()
    print(f"Accuracy:  {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall:    {metrics['recall']:.4f}")
    print(f"F1 Score:  {metrics['f1_score']:.4f}")
    print(f"ROC AUC:   {metrics['roc_auc']:.4f}")
    print()

    # Confusion matrix
    cm = metrics['confusion_matrix']
    print("Confusion Matrix:")
    print(f"                 Predicted")
    print(f"              Legit  Phishing")
    print(f"Actual Legit  {cm['true_negative']:5d}  {cm['false_positive']:5d}")
    print(f"    Phishing  {cm['false_negative']:5d}  {cm['true_positive']:5d}")
    print()

    # Classification report
    print("Classification Report:")
    print(metrics['classification_report'])

    # Check success criteria
    print("=" * 80)
    if metrics['accuracy'] >= 0.90:
        print("✓ SUCCESS: Accuracy meets 90%+ requirement")
    else:
        print(f"✗ FAIL: Accuracy {metrics['accuracy']:.2%} below 90% threshold")
    print("=" * 80)


# ---------------------------------------------------------------------------
# EVAL-05: feature-group ablation (by zeroing, no retraining)
# ---------------------------------------------------------------------------

_TEXT_GROUPS = {
    "lexical": [
        "text_" + c for c in (
            "length", "word_count", "avg_word_length", "digit_count", "digit_ratio",
            "uppercase_count", "uppercase_ratio", "exclamation_count", "question_count",
            "dollar_count", "url_count", "email_count", "phone_pattern_count",
            "special_char_ratio", "whitespace_ratio",
        )
    ],
    "syntactic": [
        "text_" + c for c in (
            "sentence_count", "avg_sentence_length", "token_count", "verb_count",
            "verb_ratio", "noun_count", "noun_ratio", "pronoun_count", "pronoun_ratio",
            "adjective_count", "adjective_ratio", "adverb_count", "adverb_ratio",
            "punct_count", "imperative_verb_count",
        )
    ],
    "stylometric": [
        "text_" + c for c in (
            "flesch_reading_ease", "flesch_kincaid_grade", "gunning_fog", "smog_index",
            "coleman_liau_index", "automated_readability_index", "syllable_count",
            "lexicon_count", "difficult_words", "lexical_diversity",
        )
    ],
    "sentiment": [
        "text_" + c for c in (
            "urgency_keyword_count", "threat_keyword_count", "action_keyword_count",
            "reward_keyword_count", "has_urgency", "has_threat", "has_action_request",
            "has_reward_claim", "personal_pronoun_ratio", "impersonal_greeting",
        )
    ],
}

# Visual features: feature extraction only, NO trained classifier consumes them.
VISUAL_GROUP: List[str] = [
    "visual_hash_distance",
    "visual_brand_similarity_flag",
    "visual_edge_density",
    "visual_color_concentration",
    "visual_rect_element_count",
]

VISUAL_NA_NOTE = (
    "No trained classifier consumes these features; visual signal is "
    "heuristic-only - see _visual_signal_probability()"
)

FEATURE_GROUPS: Dict[str, Dict[str, List[str]] | List[str]] = {
    "url": {
        "url.length": [
            "url_length", "domain_length", "path_length", "hostname_length",
            "subdomain_length", "tld_length", "query_length",
        ],
        "url.char": [
            "dot_count", "hyphen_count", "underscore_count", "slash_count",
            "question_count", "equal_count", "at_count", "ampersand_count",
            "digit_count", "special_char_count",
        ],
        "url.binary": [
            "has_https", "has_ip", "has_port", "has_subdomain", "has_query",
            "has_fragment", "is_valid", "has_suspicious_tld",
        ],
        "url.structure": [
            "path_depth", "subdomain_count", "param_count", "entropy", "digit_ratio",
        ],
    },
    "email": {
        "header": [
            "has_spf_pass", "has_dkim_pass", "has_dmarc_pass", "sender_domain_length",
            "from_domain_suspicious", "reply_to_mismatch", "has_multiple_recipients",
            "subject_length", "has_urgent_subject", "has_re_prefix", "has_fwd_prefix",
            "header_count", "has_x_headers", "has_received_headers",
            "received_header_count",
        ],
        **{k: list(v) for k, v in _TEXT_GROUPS.items()},
    },
    "sms": {
        "sms_specific": [
            "sms_length", "sms_segment_count", "exceeds_single_sms", "char_per_word_avg",
            "url_count", "has_shortened_url", "shortened_url_count", "url_to_text_ratio",
            "has_phone_number", "phone_number_count", "has_emoji", "emoji_count",
            "uppercase_word_count", "exclamation_density", "has_call_to_action",
            "has_urgency_caps", "has_prize_claim", "has_account_alert",
            "shorthand_ratio", "numeric_string_count",
        ],
        **{k: list(v) for k, v in _TEXT_GROUPS.items()},
    },
    "visual": VISUAL_GROUP,
}


def ablate_feature_groups(
    model: Any,
    X_test: np.ndarray,
    y_test: Any,
    feature_names: List[str],
    groups: Dict[str, List[str]],
) -> pd.DataFrame:
    """Measure each feature group's marginal contribution via zeroing (EVAL-05).

    The already-trained model is NOT retrained. For every group the group's
    columns are set to 0.0 in a copy of ``X_test`` and the model is re-scored.
    Zeroing preserves the trained decision boundary and isolates the group's
    signal contribution rather than re-optimizing around its absence.

    Args:
        model: Fitted estimator exposing ``predict``.
        X_test: Feature matrix; column order MUST match ``feature_names``.
        y_test: True labels.
        feature_names: Ordered column names of ``X_test``.
        groups: Mapping group name -> column names. Groups with no column in
            ``feature_names`` are skipped (not applicable to this model).

    Returns:
        DataFrame [group, baseline_accuracy, ablated_accuracy, delta] sorted by
        delta descending, where delta = baseline - ablated.
    """
    from sklearn.metrics import accuracy_score

    X_arr = np.asarray(X_test, dtype=float)
    name_to_idx = {name: i for i, name in enumerate(feature_names)}
    baseline_acc = float(accuracy_score(y_test, model.predict(X_arr)))

    rows = []
    for group_name, cols in groups.items():
        idx = [name_to_idx[c] for c in cols if c in name_to_idx]
        if not idx:
            continue
        X_ablated = X_arr.copy()
        X_ablated[:, idx] = 0.0
        ablated_acc = float(accuracy_score(y_test, model.predict(X_ablated)))
        rows.append({
            "group": group_name,
            "baseline_accuracy": baseline_acc,
            "ablated_accuracy": ablated_acc,
            "delta": baseline_acc - ablated_acc,
        })

    df = pd.DataFrame(
        rows, columns=["group", "baseline_accuracy", "ablated_accuracy", "delta"]
    )
    return df.sort_values("delta", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# EVAL-06: exportable PDF / CSV reports
# ---------------------------------------------------------------------------

def _add_classifier_pages(pdf: Any, model: Any, X_test: Any, y_test: Any, name: str) -> None:
    """Append confusion-matrix and ROC pages for one classifier to an open PdfPages."""
    import matplotlib.pyplot as plt
    from sklearn.metrics import ConfusionMatrixDisplay, RocCurveDisplay

    fig, ax = plt.subplots(figsize=(6, 5))
    ConfusionMatrixDisplay.from_estimator(
        model, X_test, y_test, display_labels=["Legitimate", "Phishing"],
        cmap="Blues", ax=ax,
    )
    ax.set_title(f"{name} - Confusion Matrix")
    pdf.savefig(fig)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 5))
    RocCurveDisplay.from_predictions(
        y_test, model.predict_proba(X_test)[:, 1], ax=ax, name=name
    )
    ax.set_title(f"{name} - ROC Curve")
    pdf.savefig(fig)
    plt.close(fig)


def export_pdf_report(
    model: Any,
    X_test: Any,
    y_test: Any,
    output_path: Union[str, Path],
    classifier_name: str = "model",
) -> None:
    """Write a 2-page PDF (confusion matrix, ROC curve) for one classifier."""
    from matplotlib.backends.backend_pdf import PdfPages

    with PdfPages(str(output_path)) as pdf:
        _add_classifier_pages(pdf, model, X_test, y_test, classifier_name)


def export_pdf_report_multi(
    models: Dict[str, Any],
    X_test: Any,
    y_test: Any,
    output_path: Union[str, Path],
) -> None:
    """Write one PDF holding confusion-matrix + ROC pages for every classifier."""
    from matplotlib.backends.backend_pdf import PdfPages

    with PdfPages(str(output_path)) as pdf:
        for name, model in models.items():
            _add_classifier_pages(pdf, model, X_test, y_test, name)


def export_csv_report(
    metrics_by_classifier: Dict[str, Dict[str, Any]],
    output_path: Union[str, Path],
) -> None:
    """Write accuracy/precision/recall/f1_score/roc_auc per classifier to CSV."""
    cols = ["accuracy", "precision", "recall", "f1_score", "roc_auc"]
    rows = [
        {"classifier": name, **{c: float(m[c]) for c in cols}}
        for name, m in metrics_by_classifier.items()
    ]
    pd.DataFrame(rows, columns=["classifier"] + cols).to_csv(output_path, index=False)
