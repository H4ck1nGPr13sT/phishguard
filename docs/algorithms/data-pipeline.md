# Data Pipeline (DOC-06 / DOC-07)

> Source: `src/data/pipeline.py`, `src/data/downloaders/`,
> `src/data/validators/`, `src/data/preprocessors/`, `src/utils/cache.py`.
> See [ml-classifiers.md](./ml-classifiers.md) for what consumes this
> pipeline's output, and [../architecture.md](../architecture.md) for where
> `src/data` sits in the overall system.

Before any classifier can be trained, PhishGuard needs a labelled dataset
that is (a) acquired from multiple independent sources, (b) schema-valid,
(c) free of leakage between train/validation/test, and (d) free of
pathological class imbalance in the training split specifically. The
`run_pipeline()` function in `src/data/pipeline.py` orchestrates all of
this as nine sequential stages — download, merge, validate, deduplicate,
temporal split, verify temporal integrity, balance, cache, report — and
returns ready-to-train `(X, y)` tuples for train/validation/test.

## 1. Dataset sources

Three independent sources are combined, each downloaded by its own module
under `src/data/downloaders/` and standardized into one schema by
`merge_datasets()` (`src/data/preprocessors/merger.py`):

| Source | Module | Provides | Label | Raw URL present? |
|--------|--------|----------|-------|-------------------|
| **PhishTank** | `downloaders/phishtank.py` | Community-verified phishing URLs, hourly-updated JSON feed (API key optional; cached fallback on failure) | Always `1` (phishing) | Yes |
| **UCI ML Phishing Websites** | `downloaders/uci_ml.py` | 11,055 samples, pre-extracted URL features in ARFF format (Mohammad, Thabtah & McCluskey, 2014) | `Result` column mapped `1 → 1` (phishing), everything else `→ 0` (legitimate) | No — `url` is set to the empty string explicitly; the dataset's own feature columns are preserved alongside the standardized ones |
| **Nazario phishing corpus** | `downloaders/nazario.py` | Real phishing e-mails in mbox format; every URL found in an e-mail becomes its own sample (one e-mail can contribute several rows) | Always `1` (phishing) | Yes |

This is a deliberate design choice, not an oversight: PhishTank and Nazario
are phishing-only feeds, so **the legitimate (label `0`) class comes
primarily from the UCI ML dataset's negative examples**. Later retraining
work (Phase 3) supplemented this with a separate balanced legitimate/phishing
URL set fetched via OpenPhish, because the UCI ML dataset's own
pre-extracted features are not compatible with PhishGuard's custom
30-feature `url_features.py` extractor (see
[ml-classifiers.md](./ml-classifiers.md)) — but the acquisition/validation/
split/balance pipeline documented here is the same regardless of which
concrete URL list feeds it.

`download_all_sources()` treats each source independently: a failed
PhishTank download (e.g. missing API key) does not block the pipeline as
long as at least one source succeeds, and each source's success/failure and
sample count is recorded in the pipeline's `reports['download']` section
for traceability.

## 2. Merging into one schema

`merge_datasets()` standardizes every source into five common columns —
`url`, `label`, `content`, `timestamp`, `source` — with source-specific
mapping rules (e.g. PhishTank's `verified_at` becomes `timestamp`; Nazario's
e-mail `body` becomes `content`). UCI ML's own feature columns are kept
alongside the standardized ones rather than discarded, since they are
legitimate additional signal for that subset of rows.

## 3. Validation (Pandera, lazy)

`validate_dataset()` (`src/data/validators/schemas.py`) checks the merged
DataFrame against a `pandera.DataFrameSchema` (`PhishingDataSchema`) that
enforces, per row:

- `url` is either empty (feature-only UCI rows) or begins with `http://`/`https://`
- `label` is in `{0, 1}`
- `source` is one of `phishtank`, `uci_ml`, `nazario`
- `content`/`timestamp` may be null (not every source provides them)

The schema is run with `lazy=True`, i.e. **lazy validation**: instead of
raising on the first invalid row, Pandera collects every failing row and
every failing check across the whole DataFrame. `validate_dataset()` then
removes only the rows that actually failed a check and returns the
remainder, together with a `rejected` dict of `{check_name: count}` and a
`statistics` block (null-timestamp count, per-source counts, class
distribution). This design choice — filter invalid rows instead of hard
failing the whole pipeline — maximizes usable data from imperfect
real-world feeds while still keeping a complete audit trail of what was
rejected and why, which matters for a thesis that needs to justify its
final sample count.

## 4. Deduplication

`deduplicate_dataset()` (`src/data/validators/quality.py`) supports two
strategies, selected by `dedup_method`:

- **`exact`** (default): drops exact-match duplicate URLs, keeping the
  first occurrence.
- **`fuzzy`**: normalizes URLs first (lowercase, trailing-slash stripped,
  leading `www.` removed after the scheme) before comparing, so
  `https://Example.com/` and `http://www.example.com` are treated as the
  same entry.

If every URL in the frame is empty — the UCI ML feature-only subset —
deduplication is skipped entirely rather than treating all those rows as
duplicates of each other, since the empty `url` column carries no identity
information for that source.

## 5. Temporal train/validation/test split

`temporal_split()` (`src/data/preprocessors/temporal_split.py`) is the
pipeline's leakage-prevention core. Rather than a random split, it enforces
**strict temporal ordering: all training timestamps precede all validation
timestamps, which precede all test timestamps** — the model is never
evaluated on data that is chronologically older than data it trained on,
which would let it "see the future" relative to deployment and produce an
optimistic, non-representative accuracy estimate (an instance of the
concept-drift / data-leakage failure mode that is a central risk for any
phishing classifier, since attacker behavior and target brands change over
time).

Algorithm:
1. Split the frame into rows **with** a valid `timestamp` and rows
   **without** one.
2. **Samples without a timestamp are assigned to the training set only**
   (never validation or test) — a deliberately conservative choice, since
   there is no way to know where an undated sample belongs in time, and
   putting it in training is the only placement that cannot violate the
   ordering guarantee.
3. Sort the timestamped rows ascending and cut them at the configured
   ratios (`train_ratio=0.7`, `val_ratio=0.15`, `test_ratio=0.15` by
   default) — the earliest 70% become training, the next 15% validation,
   the final (most recent) 15% test.
4. Concatenate the undated rows onto the training split.

`verify_temporal_integrity()` then asserts, as a hard post-condition, that
`max(train.timestamp) < min(val.timestamp)` and
`max(val.timestamp) < min(test.timestamp)`. In `run_pipeline()` this check
is not advisory — a failure raises `RuntimeError` and aborts the pipeline
rather than silently proceeding with a leaky split, because a phishing
detector's test-set accuracy is only meaningful as an estimate of future
generalization if "future" is enforced literally at the data level.

## 6. Class balancing — training data only

`balance_training_data()` (`src/data/preprocessors/balancer.py`) applies a
**hybrid SMOTE + random-undersampling** strategy to produce a target class
ratio (`target_ratio=0.5` by default, i.e. a balanced 50/50 split):

1. **SMOTE** (Synthetic Minority Over-sampling Technique, Chawla et al.)
   oversamples the minority class by synthesizing new points along the
   line segments connecting each minority sample to its `k` nearest
   minority neighbors (`k_neighbors=5`, automatically reduced if the
   minority class has fewer than 6 samples, and falling back to
   `RandomOverSampler` if even that is infeasible). This adds synthetic —
   not duplicated — minority samples, which avoids the overfitting risk of
   naive oversampling by repetition.
2. **Random undersampling** then removes majority-class rows until the
   desired `target_ratio` is reached (if SMOTE's balanced 1:1 output
   already matches or undershoots the target majority count, this step is
   skipped and the SMOTE output is kept as-is).

Balancing is applied **exclusively to `X_train`/`y_train`, strictly after
the temporal split** — the module docstring states this as a hard
invariant: "These functions should ONLY be applied to training data, NEVER
to validation or test data. Applying balancing to validation/test would
cause data leakage and invalidate model evaluation." Synthetic SMOTE
samples are statistically derived from real samples; if they leaked into
validation/test, the evaluation would be partly measuring the model's
ability to recognize its own training-data interpolations rather than
unseen data.

A secondary, SMOTE-specific leakage boundary exists inside the feature
matrix itself: SMOTE requires purely numeric input, so `run_pipeline()`
separates metadata columns (`url`, `content`, `timestamp`, `source`) from
the numeric feature columns before calling `balance_training_data()`, runs
SMOTE/undersampling on the numeric features only, and reattaches metadata
afterward (synthetic rows get `None` metadata, since they have no
real-world URL/timestamp of their own).

Every balancing run returns a `balance_report` — original/final class
counts, the technique used, synthetic-sample and removed-sample counts,
and the random seed — which the pipeline threads into its final report for
reproducibility and for the thesis's data-description chapter.

## 7. Feature caching

`cache_dataset()` / `load_cached_dataset()` (`src/utils/cache.py`) persist
each split (`train_balanced.joblib`, `validation.joblib`, `test.joblib`)
via `joblib.dump(..., compress=3)`, wrapped with metadata (timestamp,
shape, columns, and a caller-supplied description/metadata dict).
`run_pipeline()` checks for all three cache files up front and, unless
`force_refresh=True`, skips the entire download → validate → split →
balance sequence and returns the cached splits directly — making repeated
experiment runs (hyperparameter search, GA optimization, re-evaluation)
fast and exactly reproducible from a fixed dataset snapshot rather than
re-downloading and re-splitting (which could, given upstream feed churn or
clock drift, silently produce a different split on a later run).

## Reproducibility notes

`run_pipeline()` calls `set_seeds(config.random_seed)` (default
`RANDOM_SEED=42`) before any stochastic step, so the same configuration
reproduces the same split, SMOTE synthesis, and undersampling selection —
a prerequisite for the evaluation numbers reported in
[ml-classifiers.md](./ml-classifiers.md) and
[ensemble.md](./ensemble.md) to be independently regenerable rather than
taken on faith.
