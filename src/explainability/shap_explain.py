"""SHAP feature importance for URL phishing predictions (EXPL-02).

v1 is URL-only and explains a single REPRESENTATIVE model: the GA-optimized
RF `Pipeline` (`ml_models["phishing_detector"]` / `get_active_model("rf")`),
via `shap.TreeExplainer`. We deliberately do NOT attempt to explain
`ml_models["voting_soft"]` (a heterogeneous `VotingClassifier`) — SHAP has no
fast dedicated explainer for an arbitrary soft-voting ensemble; see
09-RESEARCH.md Pitfall 2.

Background sample: `cache/url_training_data.joblib["X_train"]` (200x30,
schema-matches `extract_url_features()` exactly). The three sibling cache
files (`train_balanced.joblib`, `test.joblib`, `validation.joblib`) use a
stale, incompatible 35-column UCI-encoded schema and must NEVER be used here
(09-RESEARCH.md Pitfall 1) — a column-count mismatch against the live
classifier's `n_features_in_` raises loudly rather than silently
misaligning.

`shap` itself (plus its transitive `numba`/`llvmlite` JIT deps) costs ~1.9s
to cold-import. `warm_shap_explainer()` is meant to be called ONCE from the
FastAPI lifespan (see `src/api/main.py`) so that cost is paid at startup,
not on the first `/explain` request (09-RESEARCH.md Pitfall 3). It is
IDEMPOTENT: a second call (e.g. from a test-suite TestClient that re-enters
the lifespan) returns the already-built explainer handle without
re-importing shap or rebuilding the TreeExplainer.
"""

from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np

from src.optimization.model_registry import get_active_model
from src.features.extractors import extract_url_features

BACKGROUND_PATH = Path("cache/url_training_data.joblib")

# Module-level cache populated by warm_shap_explainer(), read by
# shap_top_features(). Kept as a plain dict (rather than globals) so it is
# trivially inspectable/resettable in tests if ever needed.
_cache: dict[str, Any] = {
    "explainer": None,
    "pipeline": None,
}


def warm_shap_explainer(pipeline: Optional[Any] = None):
    """Build (once) and return the SHAP TreeExplainer handle for the
    representative RF pipeline.

    IDEMPOTENT: if the module-level cache is already populated, returns the
    cached explainer immediately WITHOUT re-importing shap or rebuilding —
    this keeps repeated lifespan entries (e.g. multiple TestClient context
    managers in the same test process) cheap.

    Args:
        pipeline: Optional pre-loaded RF sklearn Pipeline (as stored in
            `ml_models["phishing_detector"]`). If omitted, loads via
            `get_active_model("rf")`.

    Returns:
        The `shap.TreeExplainer` instance (also cached module-level).

    Raises:
        ImportError: if `shap` is not installed. Callers (the FastAPI
            lifespan) are expected to catch this and degrade gracefully
            (leave `ml_models["shap_explainer"]` unset -> /explain 503s).
        ValueError: if the background sample's column count does not match
            the classifier's `n_features_in_` (stale-cache guard).
    """
    if _cache["explainer"] is not None:
        return _cache["explainer"]

    import shap  # let ImportError propagate to the caller (lifespan)

    resolved_pipeline = pipeline if pipeline is not None else get_active_model("rf")
    clf = resolved_pipeline.named_steps["classifier"]
    scaler = resolved_pipeline.named_steps["scaler"]

    background_data = joblib.load(BACKGROUND_PATH)
    X_background = background_data["X_train"]

    if X_background.shape[1] != clf.n_features_in_:
        raise ValueError(
            f"SHAP background column count mismatch: "
            f"{BACKGROUND_PATH} has {X_background.shape[1]} columns but "
            f"the RF classifier expects {clf.n_features_in_}. This usually "
            f"means a stale/incompatible cache file is being loaded instead "
            f"of the 30-col url_training_data.joblib (see 09-RESEARCH.md "
            f"Pitfall 1) — never fall back to train_balanced/test/"
            f"validation.joblib here."
        )

    X_background_scaled = scaler.transform(X_background)

    explainer = shap.TreeExplainer(clf, X_background_scaled)

    _cache["explainer"] = explainer
    _cache["pipeline"] = resolved_pipeline

    return explainer


def shap_top_features(url: str, top_n: int = 10) -> list[dict]:
    """Top-|value|-ordered, signed SHAP feature contributions for `url`
    against the warm RF explainer.

    Args:
        url: URL to explain.
        top_n: Max number of features to return (default 10).

    Returns:
        List of up to `top_n` dicts, each `{"feature": str,
        "shap_value": float, "raw_value": float}`, ordered by descending
        abs(shap_value). `raw_value` is the UNSCALED feature value (the
        SHAP value itself was computed in standardized-feature space —
        presented as a "relative contribution", not a probability unit;
        09-RESEARCH.md Pitfall 5).

    Raises:
        RuntimeError: if the explainer has not been warmed yet (call
            `warm_shap_explainer()` first — done at FastAPI lifespan
            startup in normal operation).
    """
    if _cache["explainer"] is None:
        warm_shap_explainer()

    explainer = _cache["explainer"]
    pipeline = _cache["pipeline"]

    features = extract_url_features(url)
    names = list(features.keys())
    X = np.array([list(features.values())])
    X_scaled = pipeline.named_steps["scaler"].transform(X)

    shap_values = explainer.shap_values(X_scaled)
    sv_arr = np.array(shap_values)

    # sklearn-native RF: shape (1, n_features, n_classes) -> take class 1
    # (phishing). Some shap/estimator version combos return (1, n_features)
    # directly. Branch on ndim (09-RESEARCH.md Pitfall 4).
    if sv_arr.ndim == 3:
        contrib = sv_arr[0, :, 1]
    else:
        contrib = sv_arr[0]

    top_idx = np.argsort(np.abs(contrib))[::-1][:top_n]

    return [
        {
            "feature": names[i],
            "shap_value": float(contrib[i]),
            "raw_value": float(X[0, i]),
        }
        for i in top_idx
    ]
