#!/usr/bin/env python3
"""Generate EVAL-05 / EVAL-06 evaluation artifacts.

Writes to --output-dir (default reports/):
  eval_report.pdf       confusion matrix + ROC page per URL classifier
  eval_report.csv       accuracy/precision/recall/f1_score/roc_auc per classifier
  feature_ablation.csv  per-feature-group accuracy delta (ablation by zeroing)

Notes:
- URL evaluation uses ONLY cache/url_training_data.joblib (30 columns). The stale
  35-column caches (train_balanced/test/validation) are never read.
- Email/SMS ablation is evaluated on the training samples (no held-out split
  exists): a training-data-sensitivity measurement, not a generalization claim.
- The visual group has no trained classifier -> reported as N/A.

Import-order note (Rule 3 auto-fix, discovered during 10-02 execution): every
xgboost-containing joblib file (the 7 optimized URL classifiers, the URL
ensemble, and the email/SMS ensembles, all of which embed an XGBClassifier)
MUST be unpickled BEFORE `spacy` is imported anywhere in this process.
`src.features.extractors` imports `src.features.text_features`, which imports
`spacy` at module level; importing it before an XGBClassifier is unpickled
reliably segfaults (SIGSEGV) on this platform (xgboost/spacy native
extension conflict, not a GSD/plan bug). All joblib.load() calls that may
touch xgboost therefore happen in `load_all_models()` BEFORE
`src.features.extractors` is imported anywhere below.

Usage:
    .venv/bin/python scripts/generate_eval_report.py [--output-dir reports]
"""

import matplotlib

matplotlib.use("Agg")  # before any pyplot import

import argparse  # noqa: E402
import json  # noqa: E402
import logging  # noqa: E402
import sys  # noqa: E402
import warnings  # noqa: E402
from pathlib import Path  # noqa: E402

import joblib  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.models.evaluate import (  # noqa: E402
    FEATURE_GROUPS,
    VISUAL_GROUP,
    VISUAL_NA_NOTE,
    ablate_feature_groups,
    evaluate_model,
    export_csv_report,
    export_pdf_report_multi,
)

logger = logging.getLogger("generate_eval_report")

URL_CACHE = REPO_ROOT / "cache" / "url_training_data.joblib"
CLASSIFIERS = ["rf", "svm", "mlp", "xgb", "lr", "nb", "dt"]
LIMITATION_NOTE = (
    "training-data sensitivity (no held-out split exists); not a generalization claim"
)


def load_url_models() -> dict:
    """Load the 7 GA-optimized URL classifiers plus the active ensemble."""
    models = {}
    for name in CLASSIFIERS:
        obj = joblib.load(REPO_ROOT / "models" / "optimized" / f"{name}_optimized.joblib")
        models[name] = obj["model"] if isinstance(obj, dict) else obj
    try:
        from src.optimization.model_registry import get_active_model

        models["ensemble"] = get_active_model("ensemble")
    except Exception:
        models["ensemble"] = joblib.load(
            REPO_ROOT / "models" / "ensemble" / "voting_soft.joblib"
        )
    return models


def load_all_models() -> tuple:
    """Load every xgboost-containing joblib artifact up front.

    Must run to completion BEFORE anything imports `spacy` (transitively via
    `src.features.extractors`) — see the import-order note in the module
    docstring. Returns (url_models, email_model_data, sms_model_data).
    """
    url_models = load_url_models()
    email_md = joblib.load(REPO_ROOT / "models" / "email_sms" / "ensemble_email.joblib")
    sms_md = joblib.load(REPO_ROOT / "models" / "email_sms" / "ensemble_sms.joblib")
    return url_models, email_md, sms_md


def load_url_eval_set():
    """Load the 30-column URL evaluation set, guarding the schema (Pitfall 1).

    Caller must ensure `src.features.extractors` (and thus spacy) has not
    been imported before all xgboost models are loaded (see module docstring).
    """
    from src.features.extractors import extract_url_features

    data = joblib.load(URL_CACHE)
    live = list(extract_url_features("https://example.com/path?q=1").keys())
    names = list(data["feature_names"])
    if data["X_test"].shape[1] != 30 or names != live:
        raise RuntimeError(
            "url_training_data.joblib schema mismatch (expected 30 live columns)"
        )
    return np.asarray(data["X_test"], dtype=float), np.asarray(data["y_test"]), names


def text_ablation(kind: str, md: dict) -> pd.DataFrame:
    """Live-extract email/SMS features and ablate groups on the ensemble.

    No held-out split exists for email/SMS, so this is evaluated on the
    training samples and labelled as a training-data-sensitivity measurement
    (Open Question 1), not a generalization claim.

    Args:
        kind: "email" or "sms".
        md: Pre-loaded ensemble model-data dict (joblib.load'd by the caller
            BEFORE spacy was imported — see module docstring).
    """
    from src.features.extractors import extract_email_features, extract_sms_features

    names = list(md["feature_names"])
    samples = json.load(open(REPO_ROOT / "data" / "email_sms" / f"{kind}_samples.json"))
    rows, labels = [], []
    for s in samples:
        if kind == "email":
            feats = extract_email_features(s["content"].encode("utf-8"))
        else:
            feats = extract_sms_features(s["content"])
        rows.append([float(feats.get(n, 0.0)) for n in names])
        labels.append(s["label"])
    df = ablate_feature_groups(
        md["model"], np.asarray(rows), np.asarray(labels), names, FEATURE_GROUPS[kind]
    )
    df.insert(0, "content_type", kind)
    df["note"] = LIMITATION_NOTE
    return df


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", default="reports")
    args = parser.parse_args(argv)
    warnings.filterwarnings("ignore")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # All xgboost-containing joblib artifacts MUST load before spacy is
    # imported anywhere (see module docstring import-order note).
    models, email_md, sms_md = load_all_models()
    X_test, y_test, names = load_url_eval_set()

    metrics = {n: evaluate_model(m, X_test, y_test) for n, m in models.items()}
    export_csv_report(metrics, out / "eval_report.csv")
    export_pdf_report_multi(models, X_test, y_test, out / "eval_report.pdf")

    url_abl = ablate_feature_groups(
        models["ensemble"], X_test, y_test, names, FEATURE_GROUPS["url"]
    )
    url_abl.insert(0, "content_type", "url")
    url_abl["note"] = "held-out URL test split (50 samples)"
    parts = [url_abl, text_ablation("email", email_md), text_ablation("sms", sms_md)]
    visual = pd.DataFrame([{
        "content_type": "image",
        "group": "visual",
        "baseline_accuracy": "N/A",
        "ablated_accuracy": "N/A",
        "delta": "N/A",
        "note": f"N/A: no trained classifier. {VISUAL_NA_NOTE} ({len(VISUAL_GROUP)} features)",
    }])
    pd.concat(parts + [visual], ignore_index=True).to_csv(
        out / "feature_ablation.csv", index=False
    )
    logger.info("Wrote reports to %s", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
