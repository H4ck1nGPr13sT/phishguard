# Algorithm Theory (DOC-06 / DOC-07)

This is the index for PhishGuard's thesis-grade algorithm documentation: one
file per algorithm family, describing the theory behind each technique
*and* how it is actually configured and used in `src/`. These pages are
written fresh from the code (see each file's `Source` note) using
terminology consistent with `praca-inzynierska.pdf`, not copied from it.

For the system's static structure and request-time behavior, see
[../architecture.md](../architecture.md) and [../data-flow.md](../data-flow.md).
For the live route reference, see [../api.md](../api.md).

## Contents

| Doc | Covers | Status |
|-----|--------|--------|
| [data-pipeline.md](./data-pipeline.md) | Dataset sources, Pandera validation, deduplication, temporal train/val/test split, SMOTE + undersampling class balancing, joblib feature caching | Written (this plan) |
| [ml-classifiers.md](./ml-classifiers.md) | The 7 ML classifiers (Random Forest, SVM, MLP, XGBoost, Logistic Regression, Naive Bayes, Decision Tree): theory, project configuration, measured performance, ensemble role | Written (this plan) |
| [ensemble.md](./ensemble.md) | Soft voting, hard voting, stacking (LogisticRegression meta-model), and normalized-Shannon-entropy classifier disagreement | Written (this plan) |
| genetic-algorithm.md | DEAP-based hyperparameter optimization, binary GA feature selection, GA ensemble-weight optimization | Added by a later plan (10-05) |
| rule-based-system.md | YAML-configured weighted expert-rule engine | Added by a later plan (10-05) |
| bayesian.md | Gaussian Naive Bayes posterior-probability classifier | Added by a later plan (10-05) |
| aggregation.md | Cross-paradigm `MultiParadigmAggregator` and cross-paradigm disagreement | Added by a later plan (10-06) |
| ocr-visual.md | EasyOCR text extraction and visual/brand-similarity heuristics | Added by a later plan (10-06) |
| explainability.md | SHAP `TreeExplainer`-based explanation generation | Added by a later plan (10-06) |

The six rows above without a link are listed here as forward references
only (plain text, not Markdown links) so the internal-link test does not
see a dangling target before Plans 10-05/10-06 land and extend this table
with their own linked rows.

## Reading order

For a first read, `data-pipeline.md` → `ml-classifiers.md` → `ensemble.md`
mirrors the order data actually flows through the system: raw datasets are
acquired and split before any classifier is trained, and the 7 classifiers
exist before they can be combined into an ensemble.
