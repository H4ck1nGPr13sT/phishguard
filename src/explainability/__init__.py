"""Explainability module (Phase 9).

URL-only SHAP feature importance (EXPL-02) via `shap.TreeExplainer` on the
representative GA-optimized RF Pipeline (`get_active_model("rf")`). See
`shap_explain.py` for the warm-import + computation functions.
"""

from src.explainability.shap_explain import shap_top_features, warm_shap_explainer

__all__ = ["shap_top_features", "warm_shap_explainer"]
