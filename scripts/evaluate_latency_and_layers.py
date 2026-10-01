#!/usr/bin/env python3
"""Latency measurement (U9) and layer-contribution analysis (U10).

U9: time POST /predict/multi-paradigm over a warmed TestClient and report the
    median and 95th percentile (the thesis quotes a single 56 ms observation).
U10: for a labeled set of raw URLs, compare the ML-ensemble-only decision with
     the full three-layer aggregator decision, and report how many decisions the
     aggregator CHANGED and whether those changes were correct — the minimal test
     the review asks for (ML vs ML+rules+Bayes on the same inputs, with labels).

Scope: synthetic/opportunistic label set (openphish = phishing; a short list of
well-known domains = legitimate). It demonstrates the mechanism and quantifies
the aggregator's effect; it is not a large benchmark.
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import statistics
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient  # noqa: E402
from src.api.main import app  # noqa: E402

LEGIT = [
    "https://www.google.com/", "https://github.com/", "https://www.wikipedia.org/",
    "https://www.paypal.com/signin", "https://www.microsoft.com/", "https://www.amazon.com/",
    "https://www.apple.com/", "https://stackoverflow.com/questions", "https://www.bbc.com/news",
    "https://www.python.org/downloads/",
]


def pct(xs, p):
    xs = sorted(xs)
    k = max(0, min(len(xs) - 1, int(round((p / 100) * (len(xs) - 1)))))
    return xs[k]


def main():
    phish = [u.strip() for u in (ROOT / "cache/openphish_urls.txt").read_text().splitlines() if u.strip()][:40]
    labeled = [(u, 1) for u in phish] + [(u, 0) for u in LEGIT]

    with TestClient(app) as c:
        # warm-up
        c.post("/predict/multi-paradigm", json={"url": "https://example.com/"})

        times, rows = [], []
        for url, label in labeled:
            t0 = time.perf_counter()
            r = c.post("/predict/multi-paradigm", json={"url": url})
            dt = (time.perf_counter() - t0) * 1000.0
            if r.status_code != 200:
                continue
            times.append(dt)
            d = r.json()
            final_p = d["final_probability"]
            ml_p = d["paradigm_contributions"]["ml_ensemble"]["probability"]
            ml_dec = 1 if ml_p >= 0.5 else 0
            agg_dec = 1 if final_p >= 0.5 else 0
            rows.append((url, label, ml_p, ml_dec, final_p, agg_dec,
                         bool(d.get("disagreement", {}).get("is_edge_case", False))))

    # U9 latency
    print("=" * 74)
    print(f"U9 LATENCY — POST /predict/multi-paradigm, n={len(times)} (warmed, in-process)")
    print(f"  median = {statistics.median(times):.1f} ms   p95 = {pct(times,95):.1f} ms   "
          f"min = {min(times):.1f}   max = {max(times):.1f}")
    print(f"  under 500 ms budget at p95: {pct(times,95) < 500}")

    # U10 layer contribution
    ml_correct = sum(1 for _, y, _, md, _, _, _ in rows if md == y)
    agg_correct = sum(1 for _, y, _, _, _, ad, _ in rows if ad == y)
    changed = [r for r in rows if r[3] != r[5]]
    print("=" * 74)
    print(f"U10 LAYER CONTRIBUTION — n={len(rows)} labeled URLs "
          f"({sum(1 for r in rows if r[1]==1)} phishing / {sum(1 for r in rows if r[1]==0)} legit)")
    print(f"  ML-only accuracy    : {ml_correct}/{len(rows)} = {ml_correct/len(rows):.3f}")
    print(f"  aggregator accuracy : {agg_correct}/{len(rows)} = {agg_correct/len(rows):.3f}")
    print(f"  decisions changed by aggregator vs ML-only: {len(changed)}")
    for url, y, mlp, md, fp, ad, edge in changed:
        verdict = "correct" if ad == y else "WRONG"
        print(f"    [{verdict}] true={y} ML={md}(p={mlp:.2f}) -> AGG={ad}(p={fp:.2f}) edge={edge}  {url[:60]}")
    if not changed:
        print("    (aggregator did not change any ML-only decision on this set)")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
