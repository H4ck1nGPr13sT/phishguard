#!/usr/bin/env python3
"""Honest email/SMS evaluation and Table-7 reconciliation (review finding U4).

The stored ensembles record test_accuracy=1.0, while the thesis Table 7 quotes
email 0.9840 / SMS 0.9716. Both are on SYNTHETIC data (200 samples per type) and
there is no separate held-out split artifact. This script:
  1. evaluates the stored VotingClassifier on the full synthetic set (reproduces
     the memorized ~1.0 that the model metadata records), and
  2. runs a stratified 5-fold CV with a fresh clone refit per fold, giving an
     honest generalization estimate ON THE SYNTHETIC DATA.
It prints both so Table 7 can be reconciled, and states the hard limitation:
these numbers measure synthetic data only, not real-world messages.
"""
import os
# OpenMP guard BEFORE any import that loads torch (spaCy) or xgboost — avoids the
# macOS dual-runtime segfault (same fix as src/api/main.py / conftest.py).
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import json
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
from sklearn.base import clone
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score, f1_score

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.features.extractors import extract_email_features, extract_sms_features  # noqa: E402


def build_X(samples, kind, feature_names):
    rows = []
    for s in samples:
        content = s["content"]
        if kind == "email":
            feats = extract_email_features(content.encode("utf-8", "replace"))
        else:
            feats = extract_sms_features(content)
        rows.append([float(feats.get(name, 0.0)) for name in feature_names])
    return np.array(rows)


def main():
    for kind, model_path, data_path in [
        ("email", "models/email_sms/ensemble_email.joblib", "data/email_sms/email_samples.json"),
        ("sms", "models/email_sms/ensemble_sms.joblib", "data/email_sms/sms_samples.json"),
    ]:
        bundle = joblib.load(ROOT / model_path)
        model, fnames = bundle["model"], bundle["feature_names"]
        stored = bundle.get("test_accuracy")
        samples = json.loads((ROOT / data_path).read_text())
        y = np.array([int(s["label"]) for s in samples])
        X = build_X(samples, kind, fnames)

        # 1) stored model on the full synthetic set (= what metadata records)
        yp_full = model.predict(X)
        full_acc = accuracy_score(y, yp_full)
        full_f1 = f1_score(y, yp_full, zero_division=0)

        # 2) honest 5-fold stratified CV with a refit clone per fold
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_acc, cv_f1 = [], []
        for tr, te in skf.split(X, y):
            m = clone(model)
            m.fit(X[tr], y[tr])
            yp = m.predict(X[te])
            cv_acc.append(accuracy_score(y[te], yp))
            cv_f1.append(f1_score(y[te], yp, zero_division=0))

        print("=" * 70)
        print(f"{kind.upper()} — {len(samples)} synthetic samples, {len(fnames)} features")
        print(f"  stored metadata test_accuracy : {stored}")
        print(f"  stored model on FULL set      : acc={full_acc:.4f}  F1={full_f1:.4f}  (memorization)")
        print(f"  honest 5-fold CV (refit)      : acc={np.mean(cv_acc):.4f}±{np.std(cv_acc):.4f}  "
              f"F1={np.mean(cv_f1):.4f}±{np.std(cv_f1):.4f}")
    print("=" * 70)
    print("LIMITATION: synthetic data only — not a measurement on real messages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
