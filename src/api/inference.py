"""Shared per-content-type inference helpers.

Single code path used by BOTH the single-sample endpoints
(src/api/endpoints.py) and the batch runner (src/api/batch.py).
"""

import numpy as np

from src.features.extractors import (
    extract_url_features,
    extract_email_features,
    extract_sms_features,
)
from src.api.main import ml_models


class ModelsNotLoaded(RuntimeError):
    """Raised when required models are missing from ml_models."""

    def __init__(self, missing):
        self.missing = list(missing)
        super().__init__(f"Required models not loaded: {self.missing}")


def _require(*keys):
    missing = [k for k in keys if k not in ml_models]
    if missing:
        raise ModelsNotLoaded(missing)


def predict_url_multi(url: str) -> dict:
    """Multi-paradigm URL pipeline. Returns the aggregator output dict
    (final_prediction, final_probability, confidence, paradigm_contributions,
    disagreement, active_rules, explanation)."""
    _require("voting_soft", "rule_engine", "bayesian", "aggregator")

    features = extract_url_features(url)
    feature_array = np.array([list(features.values())])

    ensemble_proba = ml_models["voting_soft"].predict_proba(feature_array)[0]
    ml_result = {
        "ensemble_probability": float(ensemble_proba[1]),
        "prediction": "phishing" if ensemble_proba[1] > 0.5 else "legitimate",
    }
    rule_result = ml_models["rule_engine"].evaluate(features, raw_url=url)
    bayesian_result = ml_models["bayesian"].predict_with_posterior(feature_array)
    return ml_models["aggregator"].aggregate(ml_result, rule_result, bayesian_result)


def _explain(label: str, n_features: int, prediction: str, confidence: float) -> str:
    explanation = f"{label} analyzed with {n_features} features. "
    if confidence > 0.9:
        explanation += f"High confidence {prediction} ({confidence:.1%})."
    elif confidence > 0.7:
        explanation += f"Moderate confidence {prediction} ({confidence:.1%})."
    else:
        explanation += f"Low confidence {prediction} ({confidence:.1%}). Consider manual review."
    return explanation


def _text_result(model_key: str, label: str, features: dict) -> dict:
    feature_array = np.array([list(features.values())])
    proba = ml_models[model_key].predict_proba(feature_array)[0]
    phishing_prob = float(proba[1])
    prediction = "phishing" if phishing_prob > 0.5 else "legitimate"
    confidence = float(max(proba))
    return {
        "final_prediction": prediction,
        "final_probability": phishing_prob,
        "confidence": confidence,
        "feature_count": len(features),
        "explanation": _explain(label, len(features), prediction, confidence),
        "active_rules": [],
    }


def predict_email_text(raw_email: str) -> dict:
    _require("email_ensemble")
    features = extract_email_features(raw_email.encode("utf-8"))
    return _text_result("email_ensemble", "Email", features)


def predict_sms_text(message: str) -> dict:
    _require("sms_ensemble")
    features = extract_sms_features(message)
    return _text_result("sms_ensemble", "SMS message", features)
