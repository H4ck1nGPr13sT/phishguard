"""RED-by-design test contract for EVAL-05 (feature-group ablation) and
EVAL-06 (exportable PDF/CSV evaluation reports).

Wave 0 of Phase 10: these tests describe behavior implemented in Plan 10-02
(``src/models/evaluate.py`` extensions + ``scripts/generate_eval_report.py``).
Until that plan lands, most tests here are expected to FAIL (RED) — the only
exception is ``test_ablation_uses_correct_cache_schema``, which is a pure
data-schema guard that must be GREEN from the moment this file is committed.

Pitfall 2 (interactive matplotlib backend hangs non-interactive runs): the
Agg backend MUST be forced before any ``pyplot`` import, so the two
statements below are intentionally the very first lines of this module.
"""

import matplotlib

matplotlib.use("Agg")  # noqa: E402 — must precede any pyplot import (Pitfall 2)

import os
import subprocess
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
URL_CACHE = REPO_ROOT / "cache" / "url_training_data.joblib"
STALE_CACHE = REPO_ROOT / "cache" / "train_balanced.joblib"


def test_ablation_uses_correct_cache_schema():
    """Regression guard for Pitfall 1 (stale 35-col cache landmine).

    ``cache/url_training_data.joblib`` is the ONLY schema-valid URL
    evaluation set: 200 train / 50 test rows, 30 feature columns matching
    ``extract_url_features()`` exactly. The stale caches
    (``train_balanced.joblib``, ``test.joblib``, ``validation.joblib``) use
    an old 35-column UCI pre-encoded schema and must never be mistaken for
    the live evaluation set. This test is GREEN immediately (pure data
    guard, no dependency on 10-02 code) and must stay green.
    """
    from src.features.extractors import extract_url_features

    assert URL_CACHE.exists(), f"Expected valid cache missing: {URL_CACHE}"
    data = joblib.load(URL_CACHE)

    assert data["X_test"].shape == (50, 30)
    assert len(data["feature_names"]) == 30

    live_feature_names = list(extract_url_features("https://example.com/path?q=1").keys())
    assert list(data["feature_names"]) == live_feature_names

    # Defensive negative guard: the stale 35-col cache must be distinguishable
    # from the valid 30-col set (documents Pitfall 1 explicitly).
    if STALE_CACHE.exists():
        stale = joblib.load(STALE_CACHE)
        stale_columns = stale.get("columns") if isinstance(stale, dict) else None
        assert stale_columns is not None
        assert len(stale_columns) != 30
        assert list(stale_columns) != live_feature_names


def test_ablate_feature_groups_url():
    """EVAL-05: ablate_feature_groups() on the URL model's 4 subgroups.

    RED until 10-02 implements ``ablate_feature_groups``/``FEATURE_GROUPS``
    in ``src.models.evaluate``.
    """
    from src.models.evaluate import FEATURE_GROUPS, ablate_feature_groups
    from src.optimization.model_registry import get_active_model

    data = joblib.load(URL_CACHE)
    X_test = data["X_test"]
    y_test = data["y_test"]
    feature_names = list(data["feature_names"])

    try:
        model = get_active_model("rf")
    except Exception:
        model = joblib.load(REPO_ROOT / "models" / "rf_pipeline.joblib")

    result = ablate_feature_groups(
        model, X_test, y_test, feature_names, FEATURE_GROUPS["url"]
    )

    assert isinstance(result, pd.DataFrame)
    expected_columns = {"group", "baseline_accuracy", "ablated_accuracy", "delta"}
    assert expected_columns.issubset(set(result.columns))

    expected_subgroups = {"url.length", "url.char", "url.binary", "url.structure"}
    assert set(result["group"]) == expected_subgroups
    assert len(result) == len(expected_subgroups)

    baseline_values = result["baseline_accuracy"].unique()
    assert len(baseline_values) == 1
    assert 0.0 <= baseline_values[0] <= 1.0

    for delta in result["delta"]:
        assert isinstance(delta, (float, np.floating))


def test_ablation_visual_group_marked_na():
    """EVAL-05 / Pitfall 3: the visual group has no trained classifier.

    FEATURE_GROUPS must still enumerate the 5 visual_* columns so the
    report can render an explicit N/A row rather than silently omitting it.
    RED until 10-02.
    """
    from src.models.evaluate import FEATURE_GROUPS

    assert "visual" in FEATURE_GROUPS
    assert len(FEATURE_GROUPS["visual"]) == 5


def test_export_csv_report_schema(tmp_path):
    """EVAL-06: export_csv_report() writes expected metric columns in [0, 1].

    RED until 10-02.
    """
    from src.models.evaluate import export_csv_report

    metrics_by_classifier = {
        "rf": {
            "accuracy": 0.91,
            "precision": 0.89,
            "recall": 0.92,
            "f1_score": 0.905,
            "roc_auc": 0.95,
        },
        "svm": {
            "accuracy": 0.87,
            "precision": 0.85,
            "recall": 0.88,
            "f1_score": 0.865,
            "roc_auc": 0.90,
        },
    }
    out_path = tmp_path / "m.csv"
    export_csv_report(metrics_by_classifier, out_path)

    assert out_path.exists()
    df = pd.read_csv(out_path)

    required_metric_columns = {"accuracy", "precision", "recall", "f1_score", "roc_auc"}
    assert required_metric_columns.issubset(set(df.columns))
    # A classifier-name identifying column must also be present.
    assert len(df.columns) > len(required_metric_columns)

    for col in required_metric_columns:
        assert df[col].between(0.0, 1.0).all()


def test_export_pdf_report_creates_file(tmp_path):
    """EVAL-06: export_pdf_report() writes a non-empty, valid PDF.

    RED until 10-02.
    """
    from src.models.evaluate import export_pdf_report
    from src.optimization.model_registry import get_active_model

    data = joblib.load(URL_CACHE)
    X_test = data["X_test"]
    y_test = data["y_test"]

    try:
        model = get_active_model("rf")
    except Exception:
        model = joblib.load(REPO_ROOT / "models" / "rf_pipeline.joblib")

    out_path = tmp_path / "r.pdf"
    export_pdf_report(model, X_test, y_test, out_path, "RF")

    assert out_path.exists()
    assert out_path.stat().st_size > 0
    with open(out_path, "rb") as fh:
        header = fh.read(4)
    assert header == b"%PDF"


@pytest.mark.slow
def test_generate_eval_report_script_smoke(tmp_path):
    """EVAL-05/EVAL-06: end-to-end smoke test of the report-generation CLI.

    Loads all models + live email/SMS extraction, so it's marked slow.
    RED until 10-02 ships ``scripts/generate_eval_report.py``.
    """
    script = REPO_ROOT / "scripts" / "generate_eval_report.py"
    assert script.exists(), f"Expected script missing: {script}"

    env = dict(os.environ)
    result = subprocess.run(
        [sys.executable, str(script), "--output-dir", str(tmp_path)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, (
        f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
    )

    pdf_path = tmp_path / "eval_report.pdf"
    csv_path = tmp_path / "eval_report.csv"
    ablation_path = tmp_path / "feature_ablation.csv"

    assert pdf_path.exists()
    assert csv_path.exists()
    assert ablation_path.exists()

    ablation_df = pd.read_csv(ablation_path)
    assert "group" in ablation_df.columns
    visual_rows = ablation_df[ablation_df["group"] == "visual"]
    assert len(visual_rows) == 1
    visual_value = visual_rows.iloc[0]["ablated_accuracy"]
    assert pd.isna(visual_value) or str(visual_value).strip().upper() == "N/A"
