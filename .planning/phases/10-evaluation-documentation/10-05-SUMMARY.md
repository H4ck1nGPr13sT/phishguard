---
phase: 10-evaluation-documentation
plan: 05
subsystem: documentation
tags: [docs, genetic-algorithm, deap, rule-engine, bayesian, naive-bayes, thesis]
dependency-graph:
  requires:
    - docs/algorithms/README.md (10-04, index scaffold)
    - docs/algorithms/ml-classifiers.md (10-04, cross-linked)
    - docs/algorithms/ensemble.md (10-04, cross-linked)
    - src/optimization/ (ga_optimizer.py, fitness.py, feature_selection.py, ensemble_weights.py, search_spaces.py, mlflow_tracker.py)
    - src/paradigms/rules/ (engine.py, definitions.py, phishing_rules.yaml)
    - src/paradigms/bayesian/classifier.py
  provides:
    - docs/algorithms/genetic-algorithm.md
    - docs/algorithms/rule-based-system.md
    - docs/algorithms/bayesian.md
  affects:
    - docs/algorithms/README.md (index rows converted to links)
    - Plan 10-06 (aggregation.md will cross-link back into these three)
tech-stack:
  added: []
  patterns:
    - "Module-structured theory docs (one file per algorithm family), not thesis-chapter mirroring"
    - "Every numeric claim traces to src/ code, STATE.md decision log, or praca-inzynierska.pdf (cited, not reproduced)"
key-files:
  created:
    - docs/algorithms/genetic-algorithm.md
    - docs/algorithms/rule-based-system.md
    - docs/algorithms/bayesian.md
  modified:
    - docs/algorithms/README.md
decisions:
  - "Forward references between docs written in the same plan (rule-based-system.md -> bayesian.md) use plain-text module-path mentions instead of Markdown links while the target file does not yet exist mid-plan, to keep tests/test_docs.py::test_markdown_internal_links_resolve green after every individual task commit"
  - "bayesian.md explicitly distinguishes the ensemble's GA-tuned Naive Bayes member (ml-classifiers.md) from the standalone BayesianClassifier paradigm documented here, since both wrap GaussianNB but serve different architectural roles"
metrics:
  duration: "~45 min"
  completed: "2026-10-01"
---

# Phase 10 Plan 05: Algorithm Theory Docs Part II (GA / Rules / Bayesian) Summary

Wrote three thesis-grade theory docs — DEAP-based genetic algorithm optimization
(hyperparameters, feature selection, ensemble weights), the 16-rule weighted YAML
expert system, and the standalone GaussianNB Bayesian paradigm — and converted their
`docs/algorithms/README.md` index rows from forward-reference plain text into
resolving Markdown links.

## What Was Built

**`docs/algorithms/genetic-algorithm.md`** (328 lines): formal GA theory (why GA over
grid/random/Bayesian search) followed by DEAP 1.4.3 specifics for all three
optimization targets implemented in `src/optimization/`:
- Hyperparameter tuning (`ga_optimizer.py` + `fitness.py` + `search_spaces.py`):
  mixed-type individuals, tournament selection (`tournsize=3`), `cxBlend(alpha=0.5)`,
  `mutPolynomialBounded(eta=20.0, indpb=0.2)`, the `checkBounds` decorator that fixes
  out-of-range/complex-number values from blend crossover, F1 5-fold stratified-CV
  fitness, `HallOfFame(maxsize=10)` elitism, MLflow fitness-history logging
  (`mlflow_tracker.py`).
- Binary GA feature selection (`feature_selection.py`): 30-gene binary individuals,
  `cxTwoPoint`, `mutFlipBit(indpb=1/n_features)`, RF proxy-classifier fitness,
  30→16 feature reduction (46.7%).
- Ensemble weight optimization (`ensemble_weights.py`): 7-gene continuous
  individuals, `mutGaussian(mu=0, sigma=0.1, indpb=0.3)`, `normalize_weights()`
  (floor 0.01, sum to 1.0), weighted `VotingClassifier` fitness.
- Measured gains table sourced from `.planning/STATE.md` "From 04-02/03/04/05":
  +1.75% avg classifier F1, 46.7% feature reduction with +0.56% F1, +0.53-1.96%
  ensemble F1 improvement.

**`docs/algorithms/rule-based-system.md`** (242 lines): theory of weighted
rule-based expert systems vs. propositional expert systems vs. statistical
classifiers, then the project's `RuleEngine` (`src/paradigms/rules/engine.py`):
the 16-rule catalog across 4 categories (URL structure 4, keywords 5, structure
indicators 4, domain indicators 3; total weight 3.05), the three condition types
(`keyword_match` against the raw URL, `feature_check` against numeric features with
4 operators, `domain_match` against a known-domain list), `min(total, 1.0)` score
normalization, Pydantic rule validation (`definitions.py`) with the `>2.0`
redundancy warning, and the fired-rules-with-justification output format that
serves as the engine's native, non-post-hoc explanation.

**`docs/algorithms/bayesian.md`** (274 lines): Bayes' theorem (posterior/
likelihood/prior/evidence) and Gaussian Naive Bayes conditional-independence
theory, then `src/paradigms/bayesian/classifier.py::BayesianClassifier`: the
`StandardScaler`+`GaussianNB` Pipeline, `predict_with_posterior()`'s structured
output (`posterior_phishing`/`posterior_legitimate`/`prediction`/`confidence`/
`prior_info` with both log-scale and probability-scale priors from `class_prior_`),
`var_smoothing=1e-9`, the posterior-miscalibration caveat (ranking signal, not
calibrated probability), and measured F1=0.9390. Explicitly distinguishes this
standalone paradigm from the ensemble's separately GA-tuned Naive Bayes member
(documented in `ml-classifiers.md`), noting the GA found `var_smoothing≈4.4e-11`
for that ensemble member specifically (per `praca-inzynierska.pdf` §4.6.2) — a
different, non-default value from this standalone classifier's fixed `1e-9`.

**`docs/algorithms/README.md`**: the three rows for `genetic-algorithm.md`,
`rule-based-system.md`, `bayesian.md` were converted from plain-text forward
references to resolving Markdown links; the explanatory footer paragraph was
updated to reference only the three remaining unlinked rows (`aggregation.md`,
`ocr-visual.md`, `explainability.md`, scoped to Plan 10-06).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Forward link to not-yet-written bayesian.md broke internal-link test mid-plan**
- **Found during:** Task 2 verification (`pytest tests/test_docs.py -k "internal_links or mermaid"`)
- **Issue:** `rule-based-system.md` originally linked to `[bayesian.md](./bayesian.md)` in two places, but `bayesian.md` is written in Task 3 of this same plan — at Task 2's commit point the target file did not exist yet, breaking `test_markdown_internal_links_resolve`.
- **Fix:** Changed both occurrences to plain-text module-path mentions (`` `docs/algorithms/bayesian.md`, written next ``) instead of Markdown links, consistent with the plan's own established pattern for the 10-06-scoped docs in `README.md`.
- **Files modified:** `docs/algorithms/rule-based-system.md`
- **Commit:** `67ae307`

No other deviations — all three docs and the index update were written and verified exactly as scoped by the plan's tasks and `must_haves`.

## Known Limitation (not a deviation, inherent to the wave design)

`tests/test_docs.py::test_expected_docs_exist` still fails after this plan: it
expects all 13 docs across Plans 10-03/04/05/06 to exist, but
`algorithms/aggregation.md`, `algorithms/ocr-visual.md`, and
`algorithms/explainability.md` are explicitly out of scope for 10-05 (they belong
to Plan 10-06, per the plan's own `frontmatter.files_modified` and the
`threat_model`'s `T-10-05-LINK` disposition, which keeps those three rows
plain-text specifically so this test doesn't see dangling links before 10-06
lands). This is the same single failure present before this plan ran (confirmed via
baseline `pytest tests/test_docs.py -q` showing 6 missing files before, 3 missing
after — progress, not regression). `test_mermaid_blocks_have_valid_diagram_type`
and `test_markdown_internal_links_resolve` both pass. Full suite:
461 passed, 1 skipped, 1 failed (the same `test_expected_docs_exist`), no
regressions anywhere else.

## Known Stubs

None — pure documentation plan, no code paths or data sources involved.

## Threat Flags

None — static Markdown documentation only; no new network endpoints, auth paths,
file-access patterns, or schema changes were introduced. Consistent with the plan's
`threat_model` disposition (`T-10-05-SC: N-A — zero new packages, pure Markdown`).

## Self-Check: PASSED

- FOUND: `docs/algorithms/genetic-algorithm.md`
- FOUND: `docs/algorithms/rule-based-system.md`
- FOUND: `docs/algorithms/bayesian.md`
- FOUND: `docs/algorithms/README.md` (modified)
- FOUND commit `6cb1372` (Task 1: genetic-algorithm.md)
- FOUND commit `67ae307` (Task 2: rule-based-system.md)
- FOUND commit `87b9c23` (Task 3: bayesian.md + README.md index)
