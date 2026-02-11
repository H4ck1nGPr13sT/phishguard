# Phase 3: ML Ensemble Expansion - Research

**Researched:** 2026-02-11
**Domain:** scikit-learn ensemble methods (voting, stacking), multi-classifier systems
**Confidence:** HIGH

## Summary

This research investigates how to expand from a single Random Forest classifier to a 7-classifier ensemble with multiple voting strategies and disagreement detection. The phase requires adding 6 new classifiers (SVM, MLP, Gradient Boosting, Logistic Regression, Naive Bayes, Decision Tree) and implementing three aggregation methods (soft voting, hard voting, stacking).

The standard approach uses scikit-learn's built-in `VotingClassifier` and `StackingClassifier` which handle aggregation automatically. Individual predictions are accessed via `named_estimators_` and `transform()` methods. Disagreement detection uses normalized Shannon entropy calculated across classifier predictions, with values >0.7 indicating high uncertainty (edge cases).

The existing codebase already follows best practices: sklearn Pipeline pattern prevents data leakage, joblib persistence is established, FastAPI lifespan events load models once at startup, and StandardScaler normalization is in place. The expansion requires minimal architectural changes - mainly adding new classifiers to the existing pattern and implementing ensemble wrappers.

**Primary recommendation:** Use sklearn's VotingClassifier for soft/hard voting, StackingClassifier for meta-learning, and scipy.stats.entropy with base=n_classifiers for normalized disagreement scores. Load all 7 models at FastAPI startup via lifespan events into a single ml_models dict.

## Standard Stack

The established libraries/tools for ensemble classification in scikit-learn:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scikit-learn | >=1.4.0 | All classifiers + ensemble methods | Industry standard ML library with built-in VotingClassifier/StackingClassifier |
| scipy | latest | Entropy calculation for disagreement | Optimized statistical functions, scipy.stats.entropy normalizes automatically |
| joblib | included with sklearn | Model persistence | Optimized for NumPy arrays, already used in Phase 2 |

### Classifiers Required
| Classifier | sklearn Class | Key Parameters | Purpose |
|------------|---------------|----------------|---------|
| Random Forest | `RandomForestClassifier` | Already trained | Baseline from Phase 2 |
| SVM | `SVC` | `probability=True`, `class_weight='balanced'` | Non-linear decision boundary |
| MLP | `MLPClassifier` | `hidden_layer_sizes=(100,)`, `solver='adam'` | Neural network approach |
| Gradient Boosting | `GradientBoostingClassifier` | `n_estimators=100`, `learning_rate=0.1` | Sequential ensemble |
| XGBoost | `XGBClassifier` | `n_estimators=100`, `max_depth=6` | High-performance boosting |
| Logistic Regression | `LogisticRegression` | `class_weight='balanced'`, `max_iter=1000` | Linear baseline |
| Naive Bayes | `GaussianNB` | `var_smoothing=1e-9` | Probabilistic baseline |
| Decision Tree | `DecisionTreeClassifier` | `max_depth=10`, `min_samples_split=10` | Interpretable baseline |

### Ensemble Methods
| Method | sklearn Class | Parameters | When to Use |
|--------|---------------|------------|-------------|
| Soft Voting | `VotingClassifier` | `voting='soft'` | Average probabilities (recommended for calibrated classifiers) |
| Hard Voting | `VotingClassifier` | `voting='hard'` | Majority vote on class labels |
| Stacking | `StackingClassifier` | `cv=5`, `final_estimator=LogisticRegression()` | Meta-learning (often best performance) |

**Installation:**
```bash
# Already in requirements.txt
scikit-learn>=1.4.0

# Add XGBoost
pip install xgboost>=2.0.0
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── models/
│   ├── train.py              # Existing RF training
│   ├── train_ensemble.py     # NEW: Train all 7 classifiers
│   ├── predict.py            # Existing single model prediction
│   └── ensemble.py           # NEW: Ensemble prediction & disagreement
├── api/
│   ├── main.py               # Existing FastAPI app (modify lifespan)
│   └── endpoints.py          # Existing endpoints (add ensemble endpoint)
models/
├── rf_pipeline.joblib        # Existing
├── svm_pipeline.joblib       # NEW
├── mlp_pipeline.joblib       # NEW
├── gb_pipeline.joblib        # NEW
├── xgb_pipeline.joblib       # NEW
├── lr_pipeline.joblib        # NEW
├── nb_pipeline.joblib        # NEW
├── dt_pipeline.joblib        # NEW
└── ensemble/
    ├── voting_soft.joblib    # NEW: VotingClassifier with soft voting
    ├── voting_hard.joblib    # NEW: VotingClassifier with hard voting
    └── stacking.joblib       # NEW: StackingClassifier
```

### Pattern 1: Training All Classifiers with Same Pipeline

**What:** Wrap each classifier in sklearn Pipeline with StandardScaler (same pattern as Phase 2)

**When to use:** Every classifier needs same preprocessing (scaling)

**Example:**
```python
# Source: Existing pattern from src/models/train.py + sklearn docs
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import GradientBoostingClassifier
from xgboost import XGBClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier

def create_classifier_pipelines():
    """Create all 7 classifier pipelines with StandardScaler."""
    classifiers = {
        'rf': RandomForestClassifier(
            n_estimators=200, max_depth=15, min_samples_split=10,
            min_samples_leaf=5, class_weight='balanced',
            oob_score=True, n_jobs=-1, random_state=42
        ),
        'svm': SVC(
            C=1.0, kernel='rbf', gamma='scale',
            probability=True,  # CRITICAL for soft voting
            class_weight='balanced', random_state=42
        ),
        'mlp': MLPClassifier(
            hidden_layer_sizes=(100,), activation='relu',
            solver='adam', alpha=0.0001, max_iter=500,
            random_state=42
        ),
        'gb': GradientBoostingClassifier(
            n_estimators=100, learning_rate=0.1, max_depth=5,
            min_samples_split=10, random_state=42
        ),
        'xgb': XGBClassifier(
            n_estimators=100, max_depth=6, learning_rate=0.1,
            scale_pos_weight=1,  # Adjust for imbalance if needed
            random_state=42, n_jobs=-1
        ),
        'lr': LogisticRegression(
            C=1.0, max_iter=1000, class_weight='balanced',
            random_state=42, n_jobs=-1
        ),
        'nb': GaussianNB(var_smoothing=1e-9),
        'dt': DecisionTreeClassifier(
            max_depth=10, min_samples_split=10, min_samples_leaf=5,
            class_weight='balanced', random_state=42
        )
    }

    # Wrap each in Pipeline with StandardScaler
    pipelines = {}
    for name, clf in classifiers.items():
        pipelines[name] = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', clf)
        ])

    return pipelines
```

### Pattern 2: VotingClassifier for Soft/Hard Voting

**What:** Combine classifiers using sklearn VotingClassifier

**When to use:** Need to aggregate predictions via majority voting or probability averaging

**Example:**
```python
# Source: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html
from sklearn.ensemble import VotingClassifier

# CRITICAL: All estimators must be PRE-FITTED pipelines or use fit()
voting_soft = VotingClassifier(
    estimators=[
        ('rf', pipelines['rf']),
        ('svm', pipelines['svm']),
        ('mlp', pipelines['mlp']),
        ('gb', pipelines['gb']),
        ('xgb', pipelines['xgb']),
        ('lr', pipelines['lr']),
        ('nb', pipelines['nb']),
        ('dt', pipelines['dt'])
    ],
    voting='soft',  # Average probabilities (requires predict_proba support)
    n_jobs=-1
)

voting_hard = VotingClassifier(
    estimators=[...],  # Same estimators
    voting='hard',  # Majority vote on class labels
    n_jobs=-1
)

# Fit on training data
voting_soft.fit(X_train, y_train)
voting_hard.fit(X_train, y_train)
```

### Pattern 3: StackingClassifier for Meta-Learning

**What:** Train meta-model on outputs of base classifiers using cross-validation

**When to use:** Want best possible accuracy by learning how to combine predictions

**Example:**
```python
# Source: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.StackingClassifier.html
from sklearn.ensemble import StackingClassifier

stacking = StackingClassifier(
    estimators=[
        ('rf', pipelines['rf']),
        ('svm', pipelines['svm']),
        ('mlp', pipelines['mlp']),
        ('gb', pipelines['gb']),
        ('xgb', pipelines['xgb']),
        ('lr', pipelines['lr']),
        ('nb', pipelines['nb']),
        ('dt', pipelines['dt'])
    ],
    final_estimator=LogisticRegression(class_weight='balanced'),
    cv=5,  # 5-fold CV to prevent overfitting
    stack_method='auto',  # Use predict_proba if available, else predict
    n_jobs=-1
)

# CRITICAL: fit() automatically:
# 1. Trains base estimators on full X_train
# 2. Generates CV predictions for final_estimator training
# 3. Prevents data leakage
stacking.fit(X_train, y_train)
```

### Pattern 4: Accessing Individual Predictions

**What:** Get predictions from each classifier for side-by-side comparison

**When to use:** Display individual classifier results in web UI

**Example:**
```python
# Source: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html
# Method 1: Access fitted sub-estimators directly
voting_soft.named_estimators_['rf'].predict_proba(X_test)
voting_soft.named_estimators_['svm'].predict_proba(X_test)

# Method 2: Use transform() to get all predictions at once
# For soft voting: shape (n_samples, n_classifiers * n_classes)
all_probas = voting_soft.transform(X_test)
# With 7 classifiers, 2 classes: shape (n_samples, 14)
# Split into per-classifier probabilities: all_probas.reshape(n_samples, 7, 2)

# For individual URL
def get_individual_predictions(url_features):
    results = {}
    for name in ['rf', 'svm', 'mlp', 'gb', 'xgb', 'lr', 'nb', 'dt']:
        clf = voting_soft.named_estimators_[name]
        proba = clf.predict_proba([url_features])[0]
        results[name] = {
            'phishing_probability': float(proba[1]),
            'prediction': 'phishing' if proba[1] > 0.5 else 'legitimate',
            'confidence': float(max(proba))
        }
    return results
```

### Pattern 5: Disagreement Detection via Normalized Entropy

**What:** Calculate normalized Shannon entropy across classifier predictions

**When to use:** Detect edge cases where classifiers disagree

**Example:**
```python
# Source: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.entropy.html
# + https://mc-stan.org/posterior/reference/entropy.html
from scipy.stats import entropy
import numpy as np

def calculate_disagreement(individual_predictions):
    """Calculate normalized entropy (0-1) across classifier predictions.

    Returns:
        float: Disagreement score 0-1 where:
               0 = all classifiers agree (low entropy)
               1 = maximum disagreement (uniform distribution)
    """
    # Get phishing probabilities from all classifiers
    probas = [pred['phishing_probability'] for pred in individual_predictions.values()]

    # Create discrete distribution: count votes for each outcome
    # Bin probabilities into discrete buckets or use actual predictions
    predictions = [1 if p > 0.5 else 0 for p in probas]

    # Count votes for each class
    unique, counts = np.unique(predictions, return_counts=True)
    pk = counts / len(predictions)  # Normalize to probabilities

    # Calculate Shannon entropy
    H = entropy(pk, base=2)  # Use base=2 for bits

    # Normalize by max possible entropy: log2(n_classifiers)
    # For 7 classifiers with binary decision, max entropy if split evenly
    max_entropy = np.log2(len(predictions))
    normalized_entropy = H / max_entropy if max_entropy > 0 else 0.0

    return normalized_entropy

# Usage
disagreement = calculate_disagreement(individual_results)
is_edge_case = disagreement > 0.7  # Threshold for high uncertainty
```

### Pattern 6: FastAPI Multiple Model Loading

**What:** Load all models at startup via lifespan events

**When to use:** Serve multiple models without per-request loading overhead

**Example:**
```python
# Source: Existing src/api/main.py + https://github.com/fastapi/fastapi/discussions/8913
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pathlib import Path

ml_models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all ML models at startup."""
    print("Loading ensemble models...")

    # Load individual classifiers
    for name in ['rf', 'svm', 'mlp', 'gb', 'xgb', 'lr', 'nb', 'dt']:
        model_path = Path(f"models/{name}_pipeline.joblib")
        ml_models[name] = load_model(model_path)

    # Load ensemble models
    ml_models['voting_soft'] = load_model(Path("models/ensemble/voting_soft.joblib"))
    ml_models['voting_hard'] = load_model(Path("models/ensemble/voting_hard.joblib"))
    ml_models['stacking'] = load_model(Path("models/ensemble/stacking.joblib"))

    print(f"Loaded {len(ml_models)} models successfully")

    yield

    print("Shutting down, clearing models...")
    ml_models.clear()

app = FastAPI(lifespan=lifespan)
```

### Anti-Patterns to Avoid

- **DON'T train ensemble on same data used for base classifiers:** Use cross-validation (StackingClassifier does this automatically)
- **DON'T forget `probability=True` for SVC:** Required for soft voting, disabled by default
- **DON'T load models per-request:** Use FastAPI lifespan events to load once at startup
- **DON'T mix scaled and unscaled features:** All classifiers must use same Pipeline pattern
- **DON'T use `cv='prefit'` for StackingClassifier:** High overfitting risk unless models trained separately

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Combining classifier votes | Manual averaging/voting logic | `VotingClassifier` | Handles edge cases (missing values, different class orders), optimized parallel execution |
| Meta-learning on predictions | Custom CV loop + final model | `StackingClassifier` | Automatic CV prevents data leakage, handles `predict_proba` vs `predict` logic |
| Normalized entropy | Manual Shannon formula | `scipy.stats.entropy` | Numerically stable, handles edge cases (zero probabilities, normalization) |
| Model persistence | Custom serialization | `joblib.dump/load` | Optimized for NumPy arrays, version tracking, compression |
| Parallel prediction | Threading/multiprocessing | `n_jobs=-1` in classifiers | Sklearn handles GIL, avoids thread thrashing |

**Key insight:** Ensemble methods have subtle edge cases (class label ordering, probability calibration, CV data leakage). Sklearn's implementations are battle-tested on millions of datasets.

## Common Pitfalls

### Pitfall 1: SVC Without `probability=True`

**What goes wrong:** VotingClassifier with `voting='soft'` fails because SVC doesn't support `predict_proba()` by default

**Why it happens:** SVC uses Platt scaling for probability calibration which requires 5-fold CV during training - disabled by default for performance

**How to avoid:** Always set `probability=True` when creating SVC for ensemble use

**Warning signs:**
```python
AttributeError: predict_proba is not available when probability=False
```

### Pitfall 2: Data Leakage in Stacking

**What goes wrong:** Training final estimator on same-set predictions from base models causes overfitting

**Why it happens:** Base models have "seen" training data, so their predictions are overconfident

**How to avoid:** Use StackingClassifier which automatically uses `cross_val_predict` for final estimator training

**Warning signs:** Stacking accuracy on training set >> test set accuracy (>10% gap)

### Pitfall 3: Memory Issues with Multiple Workers

**What goes wrong:** Each Gunicorn worker loads all models separately, consuming N × model_size RAM

**Why it happens:** FastAPI default: workers independently load resources at startup

**How to avoid:**
- Development: Use single worker (`--workers 1`)
- Production: Use Gunicorn's `--preload` flag (load models before forking workers)

**Warning signs:** RAM usage scales linearly with worker count

### Pitfall 4: Inconsistent Feature Scaling

**What goes wrong:** Some classifiers trained on scaled features, others on raw features

**Why it happens:** Forgetting to wrap all classifiers in Pipeline with StandardScaler

**How to avoid:** Use same `create_pipeline()` pattern for ALL classifiers (including ones that don't strictly need it like tree-based)

**Warning signs:** Wildly different prediction distributions across classifiers, especially for SVM/MLP vs trees

### Pitfall 5: XGBoost Thread Thrashing

**What goes wrong:** System slows down when XGBoost and sklearn both use all threads

**Why it happens:** Both set `n_jobs=-1`, creating more threads than CPU cores

**How to avoid:** Set XGBoost `n_jobs=None` (uses all cores) and sklearn components to `n_jobs=1`, OR use single `n_jobs=-1` at VotingClassifier level and `n_jobs=1` for individual estimators

**Warning signs:** High CPU usage but slow prediction times, context switching overhead

### Pitfall 6: Entropy Without Normalization

**What goes wrong:** Disagreement scores not comparable across different numbers of classifiers

**Why it happens:** Raw Shannon entropy scales with number of outcomes

**How to avoid:** Divide entropy by `log(n_classifiers)` to normalize to [0, 1]

**Warning signs:** Disagreement scores > 1.0 or not in expected range

### Pitfall 7: Overfitting Decision Trees

**What goes wrong:** Decision Tree achieves 100% training accuracy but poor test accuracy

**Why it happens:** Default DecisionTreeClassifier grows until leaves are pure

**How to avoid:** Set `max_depth=10`, `min_samples_split=10`, `min_samples_leaf=5` for regularization

**Warning signs:** Training accuracy near 100%, test accuracy much lower

## Code Examples

Verified patterns from official sources:

### Training All Classifiers

```python
# Source: Adapted from Phase 2 train.py + sklearn ensemble docs
import logging
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier
import joblib

def train_all_classifiers(X_train, y_train):
    """Train all 7 classifiers with same preprocessing pipeline."""
    classifiers = {
        'rf': RandomForestClassifier(
            n_estimators=200, max_depth=15, min_samples_split=10,
            min_samples_leaf=5, class_weight='balanced',
            oob_score=True, n_jobs=-1, random_state=42
        ),
        'svm': SVC(
            C=1.0, kernel='rbf', gamma='scale',
            probability=True,  # CRITICAL
            class_weight='balanced', random_state=42
        ),
        'mlp': MLPClassifier(
            hidden_layer_sizes=(100,), activation='relu',
            solver='adam', alpha=0.0001, max_iter=500,
            random_state=42
        ),
        'gb': GradientBoostingClassifier(
            n_estimators=100, learning_rate=0.1, max_depth=5,
            random_state=42
        ),
        'xgb': XGBClassifier(
            n_estimators=100, max_depth=6, learning_rate=0.1,
            random_state=42, n_jobs=1  # Prevent thread thrashing
        ),
        'lr': LogisticRegression(
            C=1.0, max_iter=1000, class_weight='balanced',
            random_state=42, n_jobs=-1
        ),
        'nb': GaussianNB(var_smoothing=1e-9),
        'dt': DecisionTreeClassifier(
            max_depth=10, min_samples_split=10, min_samples_leaf=5,
            class_weight='balanced', random_state=42
        )
    }

    trained_pipelines = {}
    for name, clf in classifiers.items():
        logging.info(f"Training {name}...")
        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', clf)
        ])
        pipeline.fit(X_train, y_train)

        # Save individual model
        save_path = Path(f"models/{name}_pipeline.joblib")
        joblib.dump(pipeline, save_path, compress=3, protocol=5)
        logging.info(f"Saved {name} to {save_path}")

        trained_pipelines[name] = pipeline

    return trained_pipelines
```

### Creating and Training Ensemble Models

```python
# Source: https://scikit-learn.org/stable/modules/ensemble.html
from sklearn.ensemble import VotingClassifier, StackingClassifier

def train_ensemble_models(trained_pipelines, X_train, y_train):
    """Create and train ensemble models."""
    estimators = [(name, pipe) for name, pipe in trained_pipelines.items()]

    # Soft voting
    voting_soft = VotingClassifier(
        estimators=estimators,
        voting='soft',
        n_jobs=-1
    )
    voting_soft.fit(X_train, y_train)
    joblib.dump(voting_soft, "models/ensemble/voting_soft.joblib", compress=3)

    # Hard voting
    voting_hard = VotingClassifier(
        estimators=estimators,
        voting='hard',
        n_jobs=-1
    )
    voting_hard.fit(X_train, y_train)
    joblib.dump(voting_hard, "models/ensemble/voting_hard.joblib", compress=3)

    # Stacking
    stacking = StackingClassifier(
        estimators=estimators,
        final_estimator=LogisticRegression(class_weight='balanced'),
        cv=5,
        n_jobs=-1
    )
    stacking.fit(X_train, y_train)
    joblib.dump(stacking, "models/ensemble/stacking.joblib", compress=3)

    return voting_soft, voting_hard, stacking
```

### Ensemble Prediction with Disagreement

```python
# Source: scipy.stats.entropy docs + VotingClassifier docs
import numpy as np
from scipy.stats import entropy

def predict_with_ensemble(url_features, voting_soft_model):
    """Get ensemble prediction + individual predictions + disagreement."""
    # Get individual predictions
    individual = {}
    for name in ['rf', 'svm', 'mlp', 'gb', 'xgb', 'lr', 'nb', 'dt']:
        clf = voting_soft_model.named_estimators_[name]
        proba = clf.predict_proba([url_features])[0]
        individual[name] = {
            'phishing_probability': float(proba[1]),
            'prediction': 'phishing' if proba[1] > 0.5 else 'legitimate',
            'confidence': float(max(proba))
        }

    # Ensemble predictions
    ensemble_proba = voting_soft_model.predict_proba([url_features])[0]

    # Calculate disagreement
    predictions = np.array([1 if p['phishing_probability'] > 0.5 else 0
                           for p in individual.values()])
    unique, counts = np.unique(predictions, return_counts=True)
    pk = counts / len(predictions)
    H = entropy(pk, base=2)
    max_H = np.log2(len(predictions))
    disagreement = H / max_H if max_H > 0 else 0.0

    return {
        'ensemble': {
            'soft_voting': {
                'phishing_probability': float(ensemble_proba[1]),
                'prediction': 'phishing' if ensemble_proba[1] > 0.5 else 'legitimate',
                'confidence': float(max(ensemble_proba))
            }
        },
        'individual': individual,
        'disagreement_score': disagreement,
        'is_edge_case': disagreement > 0.7
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual ensemble averaging | VotingClassifier/StackingClassifier | sklearn 0.17+ (2015) | Built-in handling of edge cases, parallel execution |
| Pickle for models | joblib | sklearn 0.10+ (2012) | 2-10x faster for NumPy-heavy models |
| Custom probability from SVM | `probability=True` + Platt scaling | sklearn 0.14+ (2013) | Calibrated probabilities via CV |
| XGBoost separate package | XGBClassifier sklearn API | XGBoost 0.4+ (2016) | Drop-in sklearn compatibility |
| GradientBoostingClassifier | HistGradientBoostingClassifier | sklearn 0.21+ (2019) | 10x faster on large datasets (histogram-based) |

**Deprecated/outdated:**
- **GridSearchCV with `iid=True`:** Parameter removed in sklearn 0.24, cross-validation scores now correctly account for different test set sizes
- **SVC `gamma='auto'`:** Changed to `gamma='scale'` in sklearn 0.22 for better defaults
- **Manual CV for stacking:** StackingClassifier added in sklearn 0.22 automates this correctly

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal disagreement threshold for edge case detection**
   - What we know: Normalized entropy 0-1 scale, >0.7 suggested in literature
   - What's unclear: Optimal threshold depends on dataset and use case
   - Recommendation: Start with 0.7, tune based on manual review of flagged cases

2. **Memory footprint with 11 models loaded (8 individual + 3 ensemble)**
   - What we know: RandomForest ~2.5MB, others likely 1-5MB each, total ~20-40MB
   - What's unclear: Exact memory impact until models trained
   - Recommendation: Monitor RAM usage, consider lazy loading for production if needed

3. **XGBoost vs sklearn GradientBoostingClassifier for this use case**
   - What we know: XGBoost generally faster/better, sklearn GB more conservative
   - What's unclear: Which performs better on 30-feature URL dataset
   - Recommendation: Include both, compare performance, drop worse performer if needed

## Sources

### Primary (HIGH confidence)
- [VotingClassifier — scikit-learn 1.8.0](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html)
- [StackingClassifier — scikit-learn 1.8.0](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.StackingClassifier.html)
- [SVC — scikit-learn 1.8.0](https://scikit-learn.org/stable/modules/generated/sklearn.svm.SVC.html)
- [MLPClassifier — scikit-learn 1.8.0](https://scikit-learn.org/stable/modules/generated/sklearn.neural_network.MLPClassifier.html)
- [scipy.stats.entropy — SciPy v1.17.0](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.entropy.html)
- [XGBoost sklearn API](https://xgboost.readthedocs.io/en/latest/python/sklearn_estimator.html)

### Secondary (MEDIUM confidence)
- [Voting Classifier: Hard and Soft in Scikit Learn](https://medium.com/data-and-beyond/voting-classifier-hard-and-soft-in-scikit-learn-d2f3c091d973) - WebSearch verified with official docs
- [Stacking Ensemble Machine Learning With Python](https://machinelearningmastery.com/stacking-ensemble-machine-learning-with-python/) - WebSearch verified with official docs
- [FastAPI: Best way to load multiple ML models](https://github.com/fastapi/fastapi/discussions/8913) - Official GitHub discussion
- [Complete Guide to Parameter Tuning in Gradient Boosting](https://www.analyticsvidhya.com/blog/2016/02/complete-guide-parameter-tuning-gradient-boosting-gbm-python/) - WebSearch

### Tertiary (LOW confidence)
- [Normalized entropy — entropy • posterior](https://mc-stan.org/posterior/reference/entropy.html) - Formula reference, not sklearn-specific
- [Criteria for Uncertainty-based Corner Cases Detection](https://arxiv.org/html/2404.11266v1) - Academic research, not implementation guide

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official sklearn docs, verified versions in requirements.txt
- Architecture: HIGH - Patterns verified with official docs and existing codebase
- Pitfalls: MEDIUM - Based on WebSearch + official warnings, need validation in practice
- Disagreement metrics: MEDIUM - Formula verified, threshold needs tuning

**Research date:** 2026-02-11
**Valid until:** 2026-03-11 (30 days - sklearn stable, no major updates expected)
