"""API endpoint tests for POST /explain (Phase 9 Plan 01 — Wave 0).

These tests encode the consolidated /explain response contract BEFORE the
endpoint implementation lands (09-02). They are RED by design until 09-02
ships — that is the expected and correct state for this plan; do not "fix"
these tests here, they define the target behavior for a later wave.

Module-top imports are limited to stdlib, pytest, numpy, FastAPI's
TestClient, and `from src.api.main import app, ml_models` so this file
always collects cleanly even before the /explain endpoint or the
`src.api.endpoints.shap_top_features` seam exists.

Contract reference: .planning/phases/09-explainability-dashboard/09-01-PLAN.md
  200 JSON keys: url, final_prediction, final_probability, confidence,
  individual_predictions (list of 7 -> {name, phishing_probability,
  prediction, confidence}), paradigm_contributions (ml_ensemble/rules/
  bayesian -> {probability, weight, weighted_contribution, prediction}),
  shap (-> {available, content_type, model, top_features, note}),
  active_rules, disagreement, disagreement_explanation, explanation,
  processing_time_ms.
"""

import pytest
import numpy as np
from fastapi.testclient import TestClient

from src.api.main import app, ml_models


# ---------------------------------------------------------------------------
# Fixtures / test doubles
# ---------------------------------------------------------------------------


class FakeShapExplainer:
    """Placeholder for ml_models["shap_explainer"] — the fast/mocked tests
    never actually call into this object (shap_top_features is monkeypatched
    at the src.api.endpoints module level instead); its only job is to
    satisfy the "shap_explainer" in ml_models presence guard.
    """


# Canned top-10 SHAP features, descending by |shap_value|, matching the
# {feature, shap_value, raw_value} contract.
CANNED_TOP_FEATURES = [
    {"feature": "path_length", "shap_value": 0.1102, "raw_value": 7.0},
    {"feature": "slash_count", "shap_value": -0.0874, "raw_value": 3.0},
    {"feature": "special_char_count", "shap_value": 0.0610, "raw_value": 9.0},
    {"feature": "url_length", "shap_value": -0.0453, "raw_value": 46.0},
    {"feature": "hostname_length", "shap_value": 0.0418, "raw_value": 24.0},
    {"feature": "has_ip_address", "shap_value": -0.0390, "raw_value": 1.0},
    {"feature": "digit_count", "shap_value": 0.0271, "raw_value": 4.0},
    {"feature": "has_https", "shap_value": -0.0212, "raw_value": 0.0},
    {"feature": "subdomain_count", "shap_value": 0.0150, "raw_value": 2.0},
    {"feature": "query_length", "shap_value": -0.0091, "raw_value": 12.0},
]

CONSOLIDATED_KEYS = [
    "url",
    "final_prediction",
    "final_probability",
    "confidence",
    "individual_predictions",
    "paradigm_contributions",
    "shap",
    "active_rules",
    "disagreement",
    "disagreement_explanation",
    "explanation",
    "processing_time_ms",
]


@pytest.fixture
def client():
    """FastAPI test client — runs the real lifespan (loads real
    phishing_detector/voting_soft/rule_engine/bayesian/aggregator; shap
    warming is 09-02's responsibility).
    """
    with TestClient(app) as c:
        yield c


def _mock_explain_seams(monkeypatch):
    """Install the shap-free monkeypatch seams the fast tests depend on.

    Keeps the fast suite shap-free: setitem-ing any object into
    ml_models["shap_explainer"] satisfies the presence guard, and
    monkeypatching src.api.endpoints.shap_top_features means real shap
    never runs.
    """
    monkeypatch.setitem(ml_models, "shap_explainer", FakeShapExplainer())
    monkeypatch.setattr(
        "src.api.endpoints.shap_top_features",
        lambda url, top_n=10: CANNED_TOP_FEATURES[:top_n],
        raising=False,
    )


# ---------------------------------------------------------------------------
# Happy path (mocked SHAP)
# ---------------------------------------------------------------------------


def test_explain_happy_path_mocked(client, monkeypatch):
    """POST /explain returns 200 with every consolidated contract key."""
    _mock_explain_seams(monkeypatch)
    response = client.post("/explain", json={"url": "http://192.168.1.1/login"})
    assert response.status_code == 200
    data = response.json()
    for key in CONSOLIDATED_KEYS:
        assert key in data, f"Missing field: {key}"


def test_individual_predictions_has_seven(client, monkeypatch):
    """individual_predictions has all 7 classifiers (EXPL-03)."""
    _mock_explain_seams(monkeypatch)
    response = client.post("/explain", json={"url": "http://192.168.1.1/login"})
    data = response.json()
    preds = data["individual_predictions"]
    assert len(preds) == 7
    for item in preds:
        assert "name" in item
        assert "phishing_probability" in item
        assert "prediction" in item
        assert "confidence" in item


def test_paradigm_contributions_structure(client, monkeypatch):
    """paradigm_contributions has ml_ensemble/rules/bayesian structure (EXPL-03)."""
    _mock_explain_seams(monkeypatch)
    response = client.post("/explain", json={"url": "http://192.168.1.1/login"})
    data = response.json()
    contributions = data["paradigm_contributions"]
    for paradigm in ("ml_ensemble", "rules", "bayesian"):
        assert paradigm in contributions
        assert "probability" in contributions[paradigm]
        assert "weight" in contributions[paradigm]
        assert "weighted_contribution" in contributions[paradigm]
        assert "prediction" in contributions[paradigm]


def test_shap_top_features_shape_and_order(client, monkeypatch):
    """shap.top_features is <=10 entries, correctly shaped, descending by
    |shap_value|; content_type/model are fixed to "url"/"rf" (EXPL-02).
    """
    _mock_explain_seams(monkeypatch)
    response = client.post("/explain", json={"url": "http://192.168.1.1/login"})
    data = response.json()
    shap_block = data["shap"]
    assert shap_block["content_type"] == "url"
    assert shap_block["model"] == "rf"
    top_features = shap_block["top_features"]
    assert len(top_features) <= 10
    for feat in top_features:
        assert "feature" in feat
        assert "shap_value" in feat
        assert "raw_value" in feat
    magnitudes = [abs(f["shap_value"]) for f in top_features]
    assert magnitudes == sorted(magnitudes, reverse=True)


def test_active_rules_present(client, monkeypatch):
    """active_rules is a list; fired rules carry name/description/weight/
    matched_values (EXPL-01).
    """
    _mock_explain_seams(monkeypatch)
    response = client.post("/explain", json={"url": "http://192.168.1.1/login"})
    data = response.json()
    assert isinstance(data["active_rules"], list)
    for rule in data["active_rules"]:
        assert "name" in rule
        assert "description" in rule
        assert "weight" in rule
        assert "matched_values" in rule


def test_disagreement_explanation_roundtrips(client, monkeypatch):
    """disagreement_explanation is a non-empty string (EXPL-04).

    Co-located here (rather than tests/test_disagreement.py, which tests
    the DIFFERENT classifier-level module src.models.disagreement) since
    this asserts the paradigm-level get_disagreement_explanation output as
    surfaced through the consolidated /explain payload.
    """
    _mock_explain_seams(monkeypatch)
    response = client.post("/explain", json={"url": "http://192.168.1.1/login"})
    data = response.json()
    assert isinstance(data["disagreement_explanation"], str)
    assert len(data["disagreement_explanation"]) > 0


def test_explanation_is_string_nonempty(client, monkeypatch):
    """explanation (NL verdict, SHAP-enriched) is a non-empty string (EXPL-05)."""
    _mock_explain_seams(monkeypatch)
    response = client.post("/explain", json={"url": "http://192.168.1.1/login"})
    data = response.json()
    assert isinstance(data["explanation"], str)
    assert len(data["explanation"]) > 0


# ---------------------------------------------------------------------------
# Request validation (reuses URLRequest)
# ---------------------------------------------------------------------------


def test_invalid_url_returns_422(client, monkeypatch):
    _mock_explain_seams(monkeypatch)
    response = client.post("/explain", json={"url": "not-a-url"})
    assert response.status_code == 422


def test_missing_url_returns_422(client, monkeypatch):
    _mock_explain_seams(monkeypatch)
    response = client.post("/explain", json={})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 503 paths
# ---------------------------------------------------------------------------


def test_explain_503_when_detector_missing():
    """Clear ml_models after lifespan loaded them (simulates runtime
    failure); mirrors TestMultiParadigmMissingModels.
    """
    with TestClient(app) as client:
        original_models = ml_models.copy()
        ml_models.clear()
        try:
            response = client.post(
                "/explain", json={"url": "http://192.168.1.1/login"}
            )
            assert response.status_code == 503
        finally:
            ml_models.update(original_models)


def test_explain_503_when_shap_missing(client):
    """With the rest of the models loaded but no shap_explainer key,
    /explain returns 503 with a shap/"not available"-style detail.
    """
    ml_models.pop("shap_explainer", None)
    response = client.post("/explain", json={"url": "http://192.168.1.1/login"})
    assert response.status_code == 503
    detail = response.json().get("detail", "").lower()
    assert "shap" in detail or "not available" in detail


# ---------------------------------------------------------------------------
# Graceful degrade on shap warm failure (checker WARNING 2 fix)
# ---------------------------------------------------------------------------


def test_app_starts_when_shap_warm_raises(monkeypatch):
    """If shap warm-import fails at lifespan startup, the app must still
    start successfully (no crash) — "shap_explainer" absent from ml_models,
    and POST /explain degrades to 503 instead of taking down the whole
    server. Proves EXPL-02's hard dependency on shap does not turn a
    missing/broken shap install into a full-server outage.
    """
    monkeypatch.setattr(
        "src.api.main.warm_shap_explainer",
        lambda: (_ for _ in ()).throw(ImportError("shap not installed")),
        raising=False,
    )
    with TestClient(app) as c:
        assert "shap_explainer" not in ml_models
        response = c.post("/explain", json={"url": "http://192.168.1.1/login"})
        assert response.status_code == 503


# ---------------------------------------------------------------------------
# Real SHAP (slow, opt-in)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_explain_real_shap_slow():
    """Real end-to-end SHAP via TreeExplainer against the live rf model
    (no monkeypatch) — proves EXPL-05's SHAP-enrichment sentence against a
    real explainer, not just the canned mock.
    """
    pytest.importorskip("shap")
    with TestClient(app) as c:
        response = c.post(
            "/explain",
            json={"url": "http://paypal-login-security.tk/verify?acct=1"},
        )
        assert response.status_code == 200
        data = response.json()
        top_features = data["shap"]["top_features"]
        assert len(top_features) > 0
        assert len(top_features) <= 10
        for feat in top_features:
            assert "feature" in feat
            assert "shap_value" in feat
            assert "raw_value" in feat
        top_feature_name = top_features[0]["feature"]
        assert top_feature_name in data["explanation"]
