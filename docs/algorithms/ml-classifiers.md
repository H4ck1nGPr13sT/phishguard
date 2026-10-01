# The 7 ML Classifiers (DOC-06 / DOC-07)

> Source: `src/models/classifiers.py` (configuration), `.planning/STATE.md`
> "From 03-01"/"From 04-02" decisions, and `praca-inzynierska.pdf` §4.3 /
> Tables 4-5b (measured figures, cited below for consistency — not
> reproduced verbatim). See [data-pipeline.md](./data-pipeline.md) for what
> feeds these classifiers and [ensemble.md](./ensemble.md) for how their
> outputs are combined.

`create_classifiers()` in `src/models/classifiers.py` builds seven
scikit-learn / XGBoost classifiers, each wrapped in an identical
`sklearn.pipeline.Pipeline` shape:

```python
Pipeline([
    ('scaler', StandardScaler()),
    ('classifier', classifier_class(**params)),
])
```

Wrapping every classifier in a `Pipeline` with `StandardScaler` is not
cosmetic: it guarantees the scaler is `fit()` only on whatever data the
pipeline itself is trained on. When the pipeline is cross-validated or
trained on the (already leakage-safe) training split from
[data-pipeline.md](./data-pipeline.md), the scaler's mean/variance never
see validation or test rows — a second, classifier-level layer of leakage
prevention on top of the temporal split.

Each classifier is trained with `class_weight='balanced'` where the
algorithm supports it (RF, SVM, LR, DT), which reweights the loss inversely
proportional to class frequency so the SMOTE-balanced-but-still-imperfect
training distribution does not bias the decision boundary toward the
majority class. All classifiers use `random_state=42` for reproducibility,
consistent with the pipeline-wide seed discussed in
[data-pipeline.md](./data-pipeline.md). Baseline validation uses 5-fold
cross-validation rather than a single held-out split, matching the
structure of the already-split training data; the genetic-algorithm
optimization layer (a later `docs/algorithms/genetic-algorithm.md` plan)
subsequently tunes each classifier's hyperparameters against the same
5-fold F1 metric.

## 1. Random Forest

**Principle.** An ensemble of decision trees, each trained on a bootstrap
sample of the training set and a random subset of features per split
(Breiman, 2001). The final prediction is the majority vote (classification)
across all trees. The double randomization — bootstrapped rows *and*
randomized feature subsets per node — decorrelates individual trees; a
single unpruned decision tree has very low bias but very high variance,
and averaging many decorrelated high-variance, low-bias trees reduces
variance without increasing bias, which is the formal justification for
why the ensemble outperforms any single tree in it.

**Configuration in this project** (`CLASSIFIER_CONFIGS['rf']`):
`n_estimators=200`, `max_depth=15`, `min_samples_split=10`,
`min_samples_leaf=5`, `class_weight='balanced'`, `oob_score=True`,
`n_jobs=-1`. The `oob_score=True` flag enables **out-of-bag estimation**:
because each tree's bootstrap sample sees on average only
`1 - 1/e ≈ 63.2%` of the training rows, the remaining ~36.8% act as a
built-in per-tree validation set, letting Random Forest estimate
generalization error without sacrificing any data to an explicit
validation split.

**Why it suits URL features.** Random Forest handles the mixed feature
types produced by `url_features.py` well — raw lengths (hundreds), counts,
binary flags (0/1), and information-theoretic measures (Shannon entropy)
can sit in the same feature matrix without requiring scaling for the tree
splits themselves (though this project still scales via the shared
`Pipeline`), and random per-node feature subsetting makes the trees robust
to uninformative columns, since irrelevant features are simply less likely
to be chosen at any given split.

## 2. Support Vector Machine (SVM, RBF kernel)

**Principle.** SVM finds the separating hyperplane that maximizes the
margin between classes (Cortes & Vapnik). The kernel trick (here, the RBF
— Gaussian radial basis function — kernel) lets SVM operate implicitly in
a very high-dimensional feature space without explicitly computing the
transformation, which is what gives it the capacity to model non-linear
decision boundaries.

**Configuration:** `CLASSIFIER_CONFIGS['svm']` uses `C=1.0`,
`kernel='rbf'`, `gamma='scale'`, `class_weight='balanced'`, and critically
**`probability=True`**. By default `SVC` only produces hard class labels;
`probability=True` makes scikit-learn internally run a 5-fold cross-
validated Platt scaling procedure after the main fit to calibrate
`predict_proba()` outputs. This is a hard requirement for the ensemble's
soft-voting mode (see [ensemble.md](./ensemble.md)), which averages
`predict_proba()` across all seven classifiers — without it, SVM could
only contribute to hard voting.

**Trade-off for phishing detection.** SVM is robust to uninformative
features because only the support vectors (samples on or near the decision
boundary) influence the final model — most training rows end up
irrelevant to the fitted boundary. Its weakness is that training time and
memory scale at least quadratically with sample count, making it a poor
fit for very large datasets; at the scale of PhishGuard's URL dataset
(thousands, not millions, of rows) this limitation is not yet a practical
concern.

## 3. Multi-Layer Perceptron (MLP)

**Principle.** A feed-forward artificial neural network: an input layer, one
or more hidden layers, and an output layer, where each neuron computes a
weighted sum of its inputs plus a bias and passes the result through a
non-linear activation function. Training uses backpropagation with the
chain rule to compute gradients of the loss with respect to every weight.

**Configuration:** `CLASSIFIER_CONFIGS['mlp']` uses a single hidden layer
of 100 neurons (`hidden_layer_sizes=(100,)`), ReLU activation, the Adam
optimizer, `alpha=0.0001` (L2 regularization strength), and
`max_iter=500`. A single moderately wide hidden layer is consistent with
the *universal approximation theorem*: a network with one sufficiently wide
hidden layer and a non-linear activation can approximate any continuous
function to arbitrary precision, so for a 30-dimensional URL feature
vector, adding depth beyond this point tends to raise overfitting risk
without measurably improving test-set performance. The genetic-algorithm
layer tunes the hidden-layer width and `alpha` per
`docs/algorithms/genetic-algorithm.md` (later plan).

## 4. XGBoost (Gradient Boosting)

**Principle.** Gradient boosting builds an ensemble of trees *sequentially*:
each new tree is fit to the residual error of the ensemble so far, and each
tree's contribution is scaled by a learning rate. XGBoost specifically adds
(a) a second-order Taylor expansion of the loss function for faster
convergence and (b) built-in regularization — penalties on the number of
leaves and on the L1/L2 norm of leaf weights — to control overfitting.

**Configuration:** `CLASSIFIER_CONFIGS['xgb']` uses `n_estimators=100`,
`max_depth=6`, `learning_rate=0.1`, and, notably, **`n_jobs=1`** — this is
a deliberate project-level decision (see `STATE.md` "From 03-01": "XGBoost
n_jobs=1 to prevent thread thrashing when sklearn uses n_jobs=-1"), since
several other classifiers in the same ensemble already parallelize via
`n_jobs=-1`, and letting XGBoost spawn its own thread pool on top of that
causes contention rather than speedup. **There is no separate
`GradientBoostingClassifier`** in this project — XGBoost is used as the
gradient-boosting implementation throughout, since it is substantially
faster than scikit-learn's native implementation at comparable accuracy.

**Why it suits this task.** Trees naturally capture feature interactions
and non-monotonic relationships (e.g. a long URL with no urgency keywords
means something different from a long URL *with* several) that linear
models cannot. XGBoost's regularization protects against overfitting on
comparatively small training sets. Its main cost is a larger hyperparameter
surface (9 parameters were tuned by the GA layer) than simpler classifiers.

## 5. Logistic Regression

**Principle.** A linear model that predicts the log-odds of the positive
class as a linear combination of input features; despite the name, it is a
classifier, not a regression model. A sigmoid function maps the linear
score to a probability in `[0, 1]`, with the class boundary typically at
`0.5`.

**Configuration:** `CLASSIFIER_CONFIGS['lr']` uses `C=1.0`,
`max_iter=1000`, `class_weight='balanced'`. Despite its formal simplicity,
logistic regression is a frequent strong performer for phishing detection
with a low-dimensional, well-engineered feature set (PhishGuard's 30 URL
features): after GA hyperparameter tuning of the regularization strength
`C`, logistic regression became the single best-performing individual
classifier in this project (F1 ≈ 0.975 on the temporal test set — see
"Measured performance" below), ahead of both Random Forest and XGBoost.
Weak regularization (a relatively large `C`) is justified here precisely
because the feature space is low-dimensional, which keeps the overfitting
risk of a linear model low. A second practical advantage is full
interpretability: each feature has one learned coefficient, and the
class log-odds is a simple weighted sum, so the decision is directly
explainable without a separate explainability layer.

## 6. Gaussian Naive Bayes

**Principle.** Applies Bayes' theorem to compute the posterior probability
of each class given the observed features, under the "naive" assumption
that features are conditionally independent given the class. The Gaussian
variant further assumes each continuous feature is normally distributed
within each class, with mean and variance estimated from the training
data.

**Configuration:** `CLASSIFIER_CONFIGS['nb']` uses `var_smoothing=1e-9`
(scikit-learn's default, for numerical stability when a feature's
within-class variance is near zero).

**Why it is kept despite the lowest standalone accuracy.** The conditional-
independence assumption is clearly violated in practice — URL length
correlates with special-character count, dot count correlates with
subdomain count, and the keyword "verify" tends to co-occur with "account"
— yet naive Bayes classifiers often still perform surprisingly well,
because errors in the absolute probability estimates partially cancel out
when the two classes' probabilities are *compared* to each other, as long
as the correlation structure is roughly symmetric across classes. For
phishing detection specifically, Naive Bayes serves two roles: a cheap,
fast baseline, and — more importantly for the ensemble — a classifier
whose errors are largely *orthogonal* to the tree-based classifiers',
because it is built on fundamentally different assumptions. This diversity
is exactly what an ensemble needs to gain from combining classifiers
rather than just picking the single best one. (`BayesianClassifier`, a
related but distinct posterior-probability wrapper documented in a later
`docs/algorithms/bayesian.md` plan, additionally forms the third pillar of
the system's multi-paradigm aggregation layer.)

## 7. Decision Tree

**Principle.** A single decision tree recursively partitions the feature
space with binary splits chosen to maximize information gain (or minimize
Gini impurity). Each internal node asks a threshold question ("is feature
X less than T?"); each leaf holds a class prediction or class distribution.

**Configuration:** `CLASSIFIER_CONFIGS['dt']` uses `max_depth=10`,
`min_samples_split=10`, `min_samples_leaf=5`, `class_weight='balanced'`.

**Why it is kept despite being the weakest classifier in the set.** A
single decision tree is consistently the weakest of the seven (an
overly-deep tree overfits, an overly-shallow one underfits), but its
inclusion is methodologically justified rather than accidental: it is the
simplest form of an interpretable algorithmic decision, and its output can
be drawn directly as an if-then-else diagram. For a phishing-defense
context this has practical value — a security analyst can take the tree's
graphical representation and trace the exact path that led to flagging a
given URL as suspicious, something none of the other six classifiers offer
as directly.

## Comparison table

Figures below are GA-optimized per-classifier results on the temporal URL
test set, as reported in `praca-inzynierska.pdf` Tables 4/5b (sourced from
`models/optimized/{name}_metadata.json`, the project's "hard" evaluation
artifacts) — consistent with the ensemble totals cited in
[ensemble.md](./ensemble.md) and in the root `README.md`. Earlier,
pre-GA baseline figures from initial training (`.planning/STATE.md`,
"From 03-01") are shown alongside for reference; expect your own numbers
to vary with dataset snapshot and GA run (`python -m src.models.evaluate`
reproduces them against a given checkout), and see `reports/eval_report.csv`
for a separate, smaller reference evaluation generated in Phase 10.

| Classifier | Learning principle | Standalone F1 (GA-optimized) | Baseline accuracy (STATE.md, pre-GA) | Role in the ensemble |
|---|---|---|---|---|
| Logistic Regression | Linear, log-odds | **0.9749** (best single classifier) | 91.68% | Strong, fully-interpretable linear baseline; benefits most from GA's `C` tuning |
| Random Forest | Bagged decorrelated trees | 0.9705 | 96.14% (OOB) | Robust generalist; handles mixed feature types without scaling |
| MLP | Feed-forward neural net | 0.9697 | 96.29% | Captures non-linear interactions beyond what trees encode directly |
| Decision Tree | Single recursive-split tree | 0.9656 | 92.62% | Weakest individually, but fully interpretable (analyst-readable path) |
| XGBoost | Sequential gradient-boosted trees | 0.9623 | 95.52% | Handles feature interactions; strongest off-the-shelf before GA tuning |
| SVM (RBF) | Max-margin + kernel trick | 0.9502 | 94.74% | Robust to uninformative features via support vectors |
| Naive Bayes (Gaussian) | Bayesian posterior, feature independence assumed | 0.9438 | 64.07% | Weakest standalone accuracy, but orthogonal error profile — valuable ensemble diversity |

All seven classifiers feed into the voting/stacking ensembles described in
[ensemble.md](./ensemble.md), where their combined performance exceeds any
individual classifier's.
