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
| [genetic-algorithm.md](./genetic-algorithm.md) | DEAP-based hyperparameter optimization, binary GA feature selection, GA ensemble-weight optimization | Written (this plan) |
| [rule-based-system.md](./rule-based-system.md) | YAML-configured weighted expert-rule engine | Written (this plan) |
| [bayesian.md](./bayesian.md) | Gaussian Naive Bayes posterior-probability classifier | Written (this plan) |
| [aggregation.md](./aggregation.md) | Cross-paradigm `MultiParadigmAggregator`, weighted combination, and disagreement-as-signal (project core thesis) | Written (this plan) |
| [ocr-visual.md](./ocr-visual.md) | EasyOCR text extraction, perceptual-hash brand similarity, and OpenCV visual/layout heuristics | Written (this plan) |
| [explainability.md](./explainability.md) | SHAP `TreeExplainer`-based explanation generation, consolidated `/explain` endpoint (EXPL-01..05) | Written (this plan) |

## Reading order

For a first read, `data-pipeline.md` → `ml-classifiers.md` → `ensemble.md`
mirrors the order data actually flows through the system: raw datasets are
acquired and split before any classifier is trained, and the 7 classifiers
exist before they can be combined into an ensemble. From there,
`rule-based-system.md` and `bayesian.md` introduce the two non-ML paradigms,
`aggregation.md` shows how all three paradigms (and their classifier-level
and cross-paradigm disagreement signals) are combined into one verdict —
the project's core thesis — and `ocr-visual.md`/`explainability.md` cover
the multimodal image path and the on-demand explainability layer built on
top of that same aggregation foundation.
