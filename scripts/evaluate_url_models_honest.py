#!/usr/bin/env python3
"""Honest, single-protocol evaluation of URL models (review findings U2/U3).

Every variant — the 7 baseline classifiers, their GA-optimized counterparts, and
the ensembles — is evaluated on the SAME held-out test set from one documented
dataset artifact. This makes the "GA gain" and "ensemble advantage" claims
derivable from a common protocol, instead of mixing orientation baselines with
cross-validation fitness (U2) or quoting numbers with no traceable split (U3).

Dataset provenance (printed in the report header):
  - artifact: cache/url_training_data.joblib
  - split:    random stratified (sklearn train_test_split, random_state=42),
              NOT temporal — the thesis wording "temporal test" is inaccurate.
  - sizes:    200 train / 50 test, 30 URL features, 2 classes (balanced 25/25).

The GA column reports BOTH the test-set F1 (comparable to the baseline on the
same test) AND, separately, the 5-fold CV fitness stored in the optimizer
metadata — they are different quantities and are kept in different columns.
"""

import csv
import glob
import json
import os
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, roc_auc_score, confusion_matrix)

warnings.filterwarnings("ignore")  # silence sklearn 1.6.1->1.8.0 unpickle notes
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CLFS = ["rf", "svm", "mlp", "xgb", "lr", "nb", "dt"]
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)


def load_estimator(path):
    """Load a model, unwrapping the {'model': est, 'metadata': {...}} dicts
    used by the GA-optimized artifacts."""
    obj = joblib.load(path)
    if isinstance(obj, dict) and "model" in obj:
        return obj["model"]
    return obj


def metrics(model, X, y):
    yp = model.predict(X)
    out = {
        "accuracy": accuracy_score(y, yp),
        "precision": precision_score(y, yp, zero_division=0),
        "recall": recall_score(y, yp, zero_division=0),
        "f1": f1_score(y, yp, zero_division=0),
    }
    try:
        proba = model.predict_proba(X)[:, 1]
        out["roc_auc"] = roc_auc_score(y, proba)
    except Exception:
        out["roc_auc"] = float("nan")
    out["cm"] = confusion_matrix(y, yp).tolist()
    return out


def main():
    d = joblib.load(ROOT / "cache/url_training_data.joblib")
    Xte, yte = d["X_test"], d["y_test"]
    n_test = len(yte)
    n_phish = int(np.sum(yte))
    ts = d.get("timestamp", "unknown")

    print("=" * 78)
    print("HONEST URL EVALUATION — single held-out test protocol")
    print(f"  dataset: cache/url_training_data.joblib (built {ts})")
    print(f"  split:   random stratified (random_state=42) — NOT temporal")
    print(f"  test set: {n_test} samples ({n_phish} phishing / {n_test - n_phish} legit), 30 features")
    print("=" * 78)

    rows = []
    hdr = f"{'model':20s} {'variant':9s} {'acc':>6s} {'prec':>6s} {'rec':>6s} {'F1':>7s} {'AUC':>6s} {'CV_fit':>7s}"
    print(hdr)
    print("-" * len(hdr))

    for clf in CLFS:
        base_f = ROOT / f"models/{clf}_pipeline.joblib"
        opt_f = ROOT / f"models/optimized/{clf}_optimized.joblib"
        meta_f = ROOT / f"models/optimized/{clf}_metadata.json"
        cv_fit = None
        if meta_f.exists():
            try:
                meta = json.loads(meta_f.read_text())
                cv_fit = meta.get("fitness") or meta.get("best_fitness") or meta.get("cv_f1")
            except Exception:
                pass

        base_m = metrics(load_estimator(base_f), Xte, yte) if base_f.exists() else None
        opt_m = metrics(load_estimator(opt_f), Xte, yte) if opt_f.exists() else None

        if base_m:
            print(f"{clf:20s} {'baseline':9s} {base_m['accuracy']:6.3f} {base_m['precision']:6.3f} "
                  f"{base_m['recall']:6.3f} {base_m['f1']:7.4f} {base_m['roc_auc']:6.3f} {'-':>7s}")
            rows.append([clf, "baseline", base_m['accuracy'], base_m['precision'], base_m['recall'],
                         base_m['f1'], base_m['roc_auc'], "", base_m['cm']])
        if opt_m:
            cvs = f"{cv_fit:.4f}" if isinstance(cv_fit, (int, float)) else "-"
            print(f"{clf:20s} {'GA':9s} {opt_m['accuracy']:6.3f} {opt_m['precision']:6.3f} "
                  f"{opt_m['recall']:6.3f} {opt_m['f1']:7.4f} {opt_m['roc_auc']:6.3f} {cvs:>7s}")
            rows.append([clf, "GA", opt_m['accuracy'], opt_m['precision'], opt_m['recall'],
                         opt_m['f1'], opt_m['roc_auc'], cv_fit if cv_fit is not None else "", opt_m['cm']])
        if base_m and opt_m:
            gain = opt_m['f1'] - base_m['f1']
            print(f"{'':20s} {'(GA gain on same test, F1)':9s}  = {gain:+.4f}"
                  + (f"   [CV fitness {cv_fit:.4f} is a DIFFERENT quantity]" if isinstance(cv_fit, (int, float)) else ""))

    # Ensembles on the same test
    print("-" * len(hdr))
    for name, path in [("voting_soft", "models/ensemble/voting_soft.joblib"),
                       ("voting_hard", "models/ensemble/voting_hard.joblib"),
                       ("stacking", "models/ensemble/stacking.joblib")]:
        p = ROOT / path
        if p.exists():
            m = metrics(load_estimator(p), Xte, yte)
            print(f"{name:20s} {'ensemble':9s} {m['accuracy']:6.3f} {m['precision']:6.3f} "
                  f"{m['recall']:6.3f} {m['f1']:7.4f} {m['roc_auc']:6.3f} {'-':>7s}")
            rows.append([name, "ensemble", m['accuracy'], m['precision'], m['recall'],
                         m['f1'], m['roc_auc'], "", m['cm']])

    # Write CSV with provenance header
    out_csv = REPORTS / "url_eval_honest.csv"
    with out_csv.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["# dataset", "cache/url_training_data.joblib", f"built={ts}"])
        w.writerow(["# split", "random stratified random_state=42 (NOT temporal)",
                    f"test_n={n_test}", f"phishing={n_phish}"])
        w.writerow(["model", "variant", "accuracy", "precision", "recall", "f1", "roc_auc",
                    "cv_fitness", "confusion_matrix"])
        for r in rows:
            w.writerow(r)
    print("=" * 78)
    print(f"Wrote {out_csv.relative_to(ROOT)} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
