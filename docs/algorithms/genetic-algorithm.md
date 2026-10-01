# Genetic Algorithm Optimization (DOC-06 / DOC-07)

> Source: `src/optimization/` (`ga_optimizer.py`, `fitness.py`,
> `feature_selection.py`, `ensemble_weights.py`, `search_spaces.py`,
> `mlflow_tracker.py`); `.planning/STATE.md` "From 04-01" through "From
> 04-06"; `praca-inzynierska.pdf` §4.4 (measured figures and operator
> rationale, cited for consistency — not reproduced verbatim). See
> [ml-classifiers.md](./ml-classifiers.md) for the seven classifiers this
> layer tunes and [ensemble.md](./ensemble.md) for the voting/stacking
> combinations it feeds into.

## Why a genetic algorithm

Choosing hyperparameters for an ML classifier is a mixed-type optimization
problem: some parameters are integers (`n_estimators`, tree depth), some
are real-valued on a linear or logarithmic scale (`C` in SVM,
`learning_rate` in XGBoost), and some are categorical (kernel type,
splitting criterion). This search space is discontinuous and has no
usable gradient, which rules out gradient-based optimization outright.

Grid search scales exponentially with the number of dimensions — for
XGBoost's 9 tuned hyperparameters, even 3 values per dimension gives
3⁹ = 19,683 configurations, each requiring a 5-fold cross-validation
(~100,000 model fits). Random search is more sample-efficient than grid
search because most dimensions have low marginal impact and a fixed grid
step wastes evaluations on unimportant axes. Bayesian optimization
(e.g. Optuna) is more sample-efficient still, modeling the objective
function with a surrogate (typically a Gaussian process), but that
surrogate assumption fits categorical parameters awkwardly and can get
stuck in local optima.

A genetic algorithm (GA), formulated by John Holland in the 1970s and
developed since as evolutionary computation, takes a different approach:
it maintains a *population* of candidate solutions and evolves it through
selection, crossover, and mutation. This fits the hyperparameter problem
well for three reasons: a GA handles integer, continuous, and categorical
genes in the same individual without artificial remapping; the
population-based search helps escape local optima that a single-point
method (hill climbing, random search) can get trapped in; and fitness
evaluation within one generation is independent per individual, so it
parallelizes trivially. The trade-off is a higher computational cost than
Bayesian optimization and the need to tune the GA's own meta-parameters
(population size, crossover/mutation probability).

## DEAP framework

The project implements all GA optimization with
[DEAP](https://github.com/DEAP/deap) (Distributed Evolutionary Algorithms
in Python), version 1.4.3, chosen over higher-level wrappers like
`sklearn-genetic-opt` for full control over the evolution loop. DEAP
supplies ready-made selection, crossover, and mutation operators, composes
cleanly with scikit-learn pipelines, and leaves room to adopt more
advanced evolutionary variants (NSGA-II, CMA-ES, genetic programming)
without a framework change, should the project extend in that direction.

This optimization layer is applied to **three distinct targets**, each
with its own module, its own individual encoding, and its own (smaller or
larger) GA configuration:

| Target | Module | Individual encoding | Fitness |
|---|---|---|---|
| Per-classifier hyperparameters | `ga_optimizer.py` + `fitness.py` | Mixed-type list (int/float/categorical index), one gene per hyperparameter | F1, 5-fold stratified CV of that classifier |
| Feature selection | `feature_selection.py` | Binary list, one gene per URL feature (30 genes) | F1, 5-fold CV of an RF proxy classifier trained on the selected subset |
| Ensemble weights | `ensemble_weights.py` | 7 floats (one per classifier), normalized to sum to 1.0 | F1, 5-fold CV of a soft-voting `VotingClassifier` using those weights |

## Target 1: Hyperparameter optimization

`src/optimization/search_spaces.py::SEARCH_SPACES` defines a bounded
search space per classifier (`rf`, `svm`, `mlp`, `xgb`, `lr`, `nb`, `dt`),
with each parameter typed as `int`, `float` (optionally `log=True` for
log-scale sampling), or `categorical` (an index into a choice list).
Search spaces are deliberately 2-3x wider than the Phase 3 baseline
ranges to give the GA room to explore — for example RF's `n_estimators`
spans 50-300, and XGBoost alone contributes 9 tuned hyperparameters
(`n_estimators`, `max_depth`, `learning_rate`, `subsample`,
`colsample_bytree`, `gamma`, `min_child_weight`, `reg_alpha`,
`reg_lambda`).

`setup_toolbox(classifier_name, X_train, y_train)` in `ga_optimizer.py`
builds a DEAP `Toolbox`: one attribute generator per hyperparameter
(`random.randint` for int, `random.uniform` or log-uniform sampling for
float, `random.randint` over a choice index for categorical), assembled
into an `Individual` via `tools.initCycle`. `search_spaces.py::
decode_individual()` is the inverse operation — it converts a raw DEAP
individual (a flat list of numbers) back into a typed hyperparameter
dictionary that a scikit-learn constructor accepts, clamping every value
to its declared bounds and resolving categorical indices back to their
string choice.

`fitness.py::create_model_from_params()` wraps the decoded hyperparameters
plus a fixed set of project-level constants per classifier (e.g.
`class_weight='balanced'` for RF/SVM/LR/DT, `probability=True` for SVM,
`n_jobs=1` for XGBoost to avoid nested-parallelism thread thrashing — see
[ml-classifiers.md](./ml-classifiers.md)) into a
`Pipeline([('scaler', StandardScaler()), ('classifier', ...)])`, matching
the same pipeline shape used for the non-optimized baselines.

## Target 2: Binary GA feature selection

`feature_selection.py` searches over which of the 30 URL features
(`extract_url_features()`'s output columns) to keep. An individual here
is a binary vector of length 30 (`1` = feature selected, `0` = excluded),
built with `tools.initRepeat` over a `random.randint(0, 1)` generator. A
`min_features=5` constraint returns zero fitness for any individual that
selects fewer than 5 features, preventing degenerate near-empty subsets
from dominating early generations.

`evaluate_feature_subset()` uses a fixed `RandomForestClassifier` (100
trees, `class_weight='balanced'`, `random_state=42`) as a fast, robust
**proxy classifier** for scoring subsets — it is not the final model;
feature selection only decides *which columns survive* before all 7
classifiers are subsequently hyperparameter-tuned on that reduced
feature set. Using RF as a cheap proxy avoids training all 7 classifiers
for every candidate subset across 30 × 20 = 600 fitness evaluations.

GA feature selection reduced the feature set from 30 to **16 features
(46.7% reduction)**, with a **+0.56% F1** improvement over the full
30-feature baseline, per `.planning/STATE.md` "From 04-03". Structural
features (`entropy`, `special_char_count`, `dot_count`) proved most
discriminative; many length-derived features turned out redundant once
`url_length` was retained (`hostname_length`, `domain_length`,
`tld_length` contributed comparatively little marginal signal).

## Target 3: Ensemble weight optimization

`ensemble_weights.py` replaces the default equal-weight soft voting
(1/7 per classifier — see [ensemble.md](./ensemble.md)) with GA-learned
weights that better reflect each classifier's reliability. An individual
is 7 floats, one per classifier, sampled uniformly in `[0.0, 1.0]`.
`normalize_weights()` is applied inside the fitness function (not baked
into the individual's genes) so crossover/mutation can keep operating on
unconstrained floats: it floors every weight at `0.01` (to preserve
ensemble diversity — no classifier is ever fully zeroed out) and then
rescales the vector to sum to 1.0. The fitness function builds a
`VotingClassifier(voting='soft', weights=weights_normalized)` from all 7
already-trained classifier pipelines and scores it with 5-fold CV F1.

GA weight optimization found weights favoring SVM, MLP, and XGBoost
(0.25-0.26 each), while sharply down-weighting Random Forest (to as low
as 0.015) despite RF's typically strong standalone accuracy — on this
project's comparatively small dataset, SVM/MLP generalize better in
combination, and the GA's fitness signal (not a hand-tuned prior) is what
surfaces this. The GA-weighted ensemble reaches **F1 = 0.9654** versus
**F1 = 0.9602** for the equal-weight soft-voting baseline, a **+0.53%**
improvement (`.planning/STATE.md` "From 04-04"); per "From 04-05", the
improvement over the pre-GA soft-voting figure is reported as **+1.96% F1**
once the GA-optimized per-classifier models (not just the baseline
models) feed the weighted ensemble.

## Genetic operators actually used

All three optimization targets share the same operator family, configured
per-target to fit each individual's representation:

| Operator role | Hyperparameter tuning | Feature selection | Weight optimization |
|---|---|---|---|
| Selection | `tools.selTournament(tournsize=3)` | `tools.selTournament(tournsize=3)` | `tools.selTournament(tournsize=3)` |
| Crossover | `tools.cxBlend(alpha=0.5)` | `tools.cxTwoPoint` | `tools.cxBlend(alpha=0.5)` |
| Mutation | `tools.mutPolynomialBounded(eta=20.0, indpb=0.2)` | `tools.mutFlipBit(indpb=1/n_features)` | `tools.mutGaussian(mu=0, sigma=0.1, indpb=0.3)` |
| Bounds enforcement | `checkBounds` decorator | implicit (binary genes) | `checkBounds` decorator |

**Tournament selection (`tournsize=3`)** picks 3 individuals at random
from the population and advances the fittest of the three. A tournament
size of 3 is a standard middle ground: too small (size 2) weakens
selection pressure and slows convergence; too large pushes the population
toward premature convergence on a single early winner. This balances
exploration (worse individuals still occasionally survive) against
exploitation (fitter individuals are still favored), and is used
identically across all three optimization targets.

**Blend crossover (`cxBlend`, alpha=0.5)**, used for hyperparameter tuning
and weight optimization, creates a child gene as an affine combination of
the two parent genes with mixing parameter α=0.5, and — critically — the
child value is allowed to land slightly *outside* the interval spanned by
the two parents, which is what gives `cxBlend` its exploratory power
beyond pure interpolation. `cxBlend` works for individuals of any length,
including the single-gene case (Naive Bayes has only `var_smoothing` to
tune), which is why it was chosen over operators that assume multiple
genes. **Two-point crossover (`cxTwoPoint`)** is used instead for binary
feature-selection individuals, where it swaps a contiguous gene segment
between two cut points — a standard, well-behaved choice for binary
representations that blend crossover is not designed for.

**Polynomial bounded mutation (`mutPolynomialBounded`, eta=20.0,
indpb=0.2)** mutates each gene independently with 20% probability,
drawing the new value from a polynomial distribution bounded to the
hyperparameter's declared `[low, high]` range. The `eta=20` spread
parameter concentrates mutations near the original value, favoring local
exploitation around good solutions over wide random jumps — appropriate
once a population has started converging toward a promising region.
**Bit-flip mutation (`mutFlipBit`, indpb=1/n_features)** is the natural
analogue for binary feature-selection individuals, with the per-gene flip
probability set so that, on average, exactly one feature bit flips per
individual per generation. **Gaussian mutation (`mutGaussian`, mu=0,
sigma=0.1, indpb=0.3)** is used for the continuous weight-optimization
genes, perturbing each weight by a draw from `N(0, 0.1)` with 30%
per-gene probability — a higher mutation rate than the hyperparameter
case, appropriate for the simpler, lower-dimensional 7-gene weight space.

**The `checkBounds` decorator.** During hyperparameter and weight
optimization, `cxBlend`'s ability to generate offspring outside the
parent interval is a double-edged sword: left unconstrained, it produced
out-of-range values (e.g. a negative `n_estimators` for Random Forest,
which scikit-learn rejects outright) and, in extreme cases, complex
numbers from the blend arithmetic. `ga_optimizer.py::checkBounds()` and
`ensemble_weights.py`'s equivalent wrap the `mate`/`mutate` operators via
`toolbox.decorate(...)`, clipping every gene back into its declared
bounds (and discarding any imaginary component) immediately after
crossover or mutation runs. This was not part of the original design —
it was added after early optimization runs surfaced `ValueError`s from
scikit-learn constructors receiving invalid hyperparameters, and is now a
standard part of every mixed/continuous-space toolbox in this project.

## Fitness function: F1-score with 5-fold stratified cross-validation

All three targets maximize the same fitness metric: binary **F1-score**
(`sklearn.metrics.f1_score(average='binary')`) averaged over **5-fold
stratified cross-validation** (`cross_val_score(..., cv=5)`), computed
with `n_jobs=1` in the CV call to avoid nested parallelism against
classifiers that themselves use `n_jobs=-1` internally. F1 rather than
raw accuracy is the deliberate choice because the problem is sensitive to
both false negatives (a missed phishing sample) and false positives (a
legitimate message incorrectly flagged); F1's harmonic mean of precision
and recall balances these two costs for the minority phishing class.
Stratified 5-fold CV guards against overfitting to one particular
train/validation split and is the comparison standard used throughout the
GA literature for this class of problem. Any hyperparameter combination
that raises an exception during model construction or fitting (invalid
`solver`/`penalty` pairing, etc.) is caught and scored with fitness
`(0.0,)` rather than propagating the exception and aborting the run — an
invalid individual simply loses the tournament rather than crashing the
evolution loop.

## Population, generations, and the exploitation/exploration trade-off

| Target | Population | Generations | Crossover prob. (`cxpb`) | Mutation prob. (`mutpb`) |
|---|---|---|---|---|
| Hyperparameter tuning | 50 | 30 | 0.7 | 0.2 |
| Feature selection | 30 | 20 | 0.5 | 0.2 |
| Weight optimization | 30 | 20 | 0.6 | 0.3 |

Hyperparameter tuning uses the largest population (50) and the most
generations (30) because its search space is the highest-dimensional and
most heterogeneous (mixed int/float/categorical, up to 9 genes for
XGBoost); a larger, longer-running search is warranted to adequately
cover that space. Feature selection and weight optimization use smaller
populations (30) and fewer generations (20): the binary feature-selection
space, while technically 2³⁰-dimensional, converges faster in practice
because bit-flip mutation with `indpb=1/n_features` makes small,
localized moves; the 7-gene weight-optimization space is simply
low-dimensional enough that a smaller budget suffices. Per classifier,
hyperparameter optimization takes roughly 15-90 seconds end-to-end on
consumer hardware (`.planning/STATE.md` "From 04-02").

## HallOfFame elitism

Every evolution loop (`algorithms.eaSimple` from DEAP) is paired with a
`tools.HallOfFame(maxsize=10)`. The Hall of Fame independently tracks the
top 10 individuals seen across *all* generations so far — not just the
current population — and automatically carries them forward even if a
later generation's selection/crossover/mutation happens to lose the
best-known solution. This is standard elitism: without it, a GA can
regress between generations purely due to selection variance, discarding
a good solution it already found. The function's return value in every
module (`run_ga_optimization`, `run_feature_selection`,
`run_weight_optimization`) is `hof[0]` — the single best individual ever
observed, not merely the best individual in the final generation.

## Fitness-history logging via MLflow

`mlflow_tracker.py` records every optimization run as an MLflow
experiment (`setup_experiment()`, default name
`phase_4_ga_optimization`). `log_generation()` is called once per
generation and logs `avg_fitness`, `max_fitness`, `min_fitness`, and
`std_fitness` as MLflow metrics with the generation index as the `step`
parameter, which lets MLflow's UI render a convergence curve per run — a
falling `std_fitness` indicates the population is converging (and, if it
falls too early, possibly prematurely). `log_best_individual()` logs the
final decoded hyperparameters as MLflow params (so they are searchable
and filterable across runs in the MLflow UI) together with the final
fitness and total optimization duration. `log_convergence_analysis()`
post-processes the DEAP logbook to detect the generation at which further
improvement in `max_fitness` fell below a `0.001` threshold for 5
consecutive generations, giving a quantitative "generations to
convergence" figure rather than relying on visual inspection of the curve
alone. `save_optimized_model()` persists the winning model as
`models/optimized/{classifier}_optimized.joblib` (joblib, `compress=3`)
alongside a human-readable `{classifier}_metadata.json` (hyperparameters,
fitness, timestamp), and logs both as MLflow artifacts — this metadata
file is what `src/optimization/model_registry.py` reads to let the API
select between baseline and GA-optimized model versions without a code
change.

```mermaid
flowchart TD
    SS[search_spaces.py: SEARCH_SPACES] --> TB[setup_toolbox]
    TB --> POP[Initial population]
    POP --> EVAL[fitness.py: evaluate_individual<br/>F1, 5-fold stratified CV]
    EVAL --> SEL[selTournament tournsize=3]
    SEL --> CX[cxBlend / cxTwoPoint]
    CX --> MUT[mutPolynomialBounded / mutFlipBit / mutGaussian]
    MUT --> CB[checkBounds decorator]
    CB --> HOF[HallOfFame maxsize=10]
    CB --> NEXTGEN{More generations?}
    NEXTGEN -- yes --> EVAL
    NEXTGEN -- no --> BEST[hof(0): best individual]
    BEST --> SAVE[save_optimized_model → models/optimized/]
    EVAL -.-> MLF[mlflow_tracker.py: log_generation per step]
    BEST -.-> MLF2[mlflow_tracker.py: log_best_individual + convergence]
```

## Measured gains

| Optimization target | Measured improvement | Source |
|---|---|---|
| Per-classifier hyperparameters | +1.75% average F1 across all 7 classifiers (MLP best, +4.55%); 6 of 7 classifiers improved, 1 unchanged | `.planning/STATE.md` "From 04-05" |
| Feature selection | 30 → 16 features (46.7% reduction), +0.56% F1 | `.planning/STATE.md` "From 04-03" |
| Ensemble weights | +0.53% F1 over equal-weight baseline (0.9654 vs. 0.9602); +1.96% F1 once combined with GA-optimized base classifiers | `.planning/STATE.md` "From 04-04"/"From 04-05" |

These three gains compound rather than overlap: feature selection narrows
the 30-feature input to the 16 most discriminative columns, hyperparameter
tuning then optimizes each of the 7 classifiers' internal configuration
against that (or the full) feature set, and weight optimization finally
tunes how those already-optimized classifiers are combined in the soft
voting ensemble described in [ensemble.md](./ensemble.md). The GA-weighted
ensemble (97.78% accuracy per [ensemble.md](./ensemble.md)'s companion
figures) is the best-performing combination rule measured anywhere in the
project, ahead of unweighted soft voting, hard voting, and stacking.
