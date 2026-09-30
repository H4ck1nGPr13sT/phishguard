# Phase 9: Explainability & Dashboard - Research

**Researched:** 2026-09-30
**Domain:** Model explainability (SHAP), multi-paradigm result surfacing, hand-rolled SVG dashboard (no CDN/Node)
**Confidence:** HIGH

## Summary

Phase 9 is 70% *surfacing* and 30% *new build*. Three of the five EXPL requirements (EXPL-01 rules-fired, EXPL-04 disagreement explanation, EXPL-05 natural-language verdict) are **already fully computed** by `MultiParadigmAggregator`/`disagreement.py` and already flow through `/predict/multi-paradigm` into `app.js`'s existing renderer. The genuinely new work is: (1) SHAP feature importance for ML predictions (EXPL-02), delivered via a new on-demand `POST /explain` endpoint (locked decision — SHAP is slow, must not touch the fast `/predict*` path), and (2) a hand-rolled SVG dashboard (EXPL-03, WEB-04, WEB-06) that visualizes the 7-classifier comparison, the SHAP bars, and the disagreement signal, built with zero external JS dependencies to respect the Phase 8 CSP (`default-src 'self'`, no CDN, no Node/bundler).

This research **end-to-end verified** (not just read about) the entire SHAP pipeline against the real, currently-deployed model artifacts in this repo: `shap==0.52.0` installs cleanly into the project's Python 3.13 / macOS arm64 `.venv` with no `torch` dependency (confirmed via PyPI registry metadata and an isolated throwaway venv — `torch` appears only under shap's `test` extra); `shap.TreeExplainer` was run against the actual GA-optimized `rf` Pipeline loaded via `get_active_model("rf")` and produced correct, signed, named top-10 feature contributions in ~3ms (post-import); `LinearExplainer` (lr) ran in <0.1ms; a bounded `KernelExplainer` (svm, with a 5-cluster k-means background) ran in ~23ms. A pre-existing cache file, `cache/url_training_data.joblib`, contains exactly the background/reference sample SHAP needs: 200 rows × 30 columns whose `feature_names` list matches `extract_url_features()`'s live output **exactly** — this is the correct source for SHAP background data. Critically, three *other* cache files (`cache/train_balanced.joblib`, `cache/test.joblib`, `cache/validation.joblib`) use a **stale, incompatible 35-column UCI-encoded schema** (`having_IP_Address`, -1/0/1 encoding) left over from an earlier retraining iteration — using any of them as SHAP background would silently corrupt the explanation. This is documented as a Common Pitfall below.

**Primary recommendation:** Add `shap>=0.52.0` to requirements.txt; warm-import it once at FastAPI lifespan startup (like the EasyOCR reader) to absorb the ~1.9s numba/llvmlite JIT cold-start outside the request path; implement `POST /explain` that runs `TreeExplainer` on `ml_models["phishing_detector"]` (the single GA-optimized RF Pipeline — the natural "representative model" target, since it is already a clean `Pipeline(scaler, classifier)` object, not the `VotingClassifier` ensemble which has no native SHAP tree-structure explainer); reuse `cache/url_training_data.joblib` as the cached background sample; build the dashboard's three visualizations (classifier bar chart, SHAP bars, disagreement gauge) as hand-rolled `document.createElementNS('http://www.w3.org/2000/svg', ...)` SVG in `app.js`, respecting the existing `test_app_js_contract` ban on `innerHTML`/`insertAdjacentHTML`/`document.write`.

## User Constraints

<user_constraints>
No `CONTEXT.md` exists for this phase (not yet run through `/gsd:discuss-phase` — confirmed empty directory). The following are locked by the orchestrator's phase-launch instructions and by upstream project docs (PROJECT.md, ROADMAP.md), and are treated with the same authority as a locked CONTEXT.md decision:

### Locked Decisions
1. **SHAP, not LIME.** Use the fastest applicable explainer per model family: `TreeExplainer` for tree models (rf/dt/xgb), `LinearExplainer` for lr, and either `LinearExplainer`/bounded `KernelExplainer` for svm/mlp/nb **or** focus SHAP on a single primary/representative model to stay tractable. (This research recommends the latter — see Architecture Patterns.)
2. **On-demand only.** SHAP computation happens in a **separate** `POST /explain` endpoint triggered by an "Explain" button — never on the fast `/predict*` path.
3. **No external JS dependency.** CSP is `default-src 'self'` (no CDN, no Node/bundler). All charts (classifier-comparison bars, SHAP feature bars, disagreement indicator) must be hand-rolled inline SVG/DOM in vanilla JS, XSS-safe via `textContent`/`createElement`/SVG DOM only — no `innerHTML`.
4. **Reuse, don't reinvent.** EXPL-01 (rules fired + weights), EXPL-04 (disagreement), and most of EXPL-05 (text explanation) are already produced by `aggregator.py`/`disagreement.py`. Phase 9 surfaces/enriches these; only SHAP (EXPL-02) and the visualizations (EXPL-03, WEB-04, WEB-06) are genuinely new.

### Claude's Discretion
- Exact SHAP explainer choice per non-tree model (LinearExplainer vs. bounded KernelExplainer vs. "representative model only").
- Exact SVG chart layout/styling within the no-CDN constraint.
- Whether to extend `MultiParadigmResponse` with `individual_predictions` (for the 9-way bar chart) vs. having the frontend call `/predict/ensemble` separately.
- Caching strategy for `/explain` results (in-memory LRU, none, or none-needed given expected demo traffic).

### Deferred Ideas (OUT OF SCOPE)
- None explicitly deferred in ROADMAP.md for Phase 9; email/SMS/image SHAP explanations are **not** required by EXPL-02's wording ("ML predictions" generically) but this research recommends scoping the `/explain` endpoint to the URL content type for v1 given background-data availability (see Open Questions).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXPL-01 | System wyświetla które reguły eksperckie zadziałały z wagami | **Already exists.** `aggregator.py` → `active_rules` (from `RuleEngine.evaluate()`'s `fired_rules`), `FiredRule` Pydantic model (name/description/weight/matched_values), already rendered in `app.js` ("Fired rules" `<ul>`). Phase 9 only needs to place this in the new dashboard layout — no backend change required. |
| EXPL-02 | System wyświetla SHAP/LIME feature importance dla decyzji ML | **New.** `POST /explain` endpoint; `shap.TreeExplainer` on `ml_models["phishing_detector"]` (GA-optimized RF Pipeline), feature names from `extract_url_features().keys()`, background from `cache/url_training_data.joblib`. Verified end-to-end in this research session (~3ms warm). |
| EXPL-03 | System wyświetla porównanie predykcji wszystkich klasyfikatorów | **Mostly exists, needs wiring.** `get_individual_predictions(voting_soft, X)` (Phase 3) already extracts all 7 base-estimator predictions cheaply; used today by `/predict/ensemble`. New: expose this alongside rules+Bayesian in the multi-paradigm response (or a second fast call), and render as a hand-rolled SVG bar chart (new). |
| EXPL-04 | System wyjaśnia rozbieżności między metodami gdy występują | **Already exists** as structured data (`disagreement.py` → `calculate_paradigm_disagreement()`, `get_disagreement_explanation()`) but `get_disagreement_explanation()`'s richer per-paradigm text is currently **unused** by the API (only a short inline warning appears in `aggregator._generate_explanation()`). New: expose the fuller explanation text and the dropped `paradigm_probabilities` field; render as a disagreement visualization. |
| EXPL-05 | System generuje raport wyjaśniający decyzję w formie tekstowej | **Already exists.** `aggregator._generate_explanation()` → `explanation` field, already rendered. New: enrich the `/explain` (slow-path) response with top-SHAP-feature sentence, since the fast path's explanation cannot include SHAP by definition (locked decision 2). |
| WEB-04 | Aplikacja wyświetla dashboard z wizualizacjami (wykresy, porównania) | **New.** Hand-rolled SVG dashboard: classifier-comparison bar chart, SHAP feature-importance bars, disagreement indicator — all vanilla-JS SVG/DOM, no CDN (see Architecture Patterns). |
| WEB-06 | Aplikacja wyświetla szczegółowe wyjaśnienie decyzji | **New UI, reuses existing data** — combines EXPL-01/04/05 (already-available fields) with EXPL-02 (new `/explain` data) into one detail view triggered by the "Explain" button. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SHAP computation (EXPL-02) | API / Backend | — | CPU-bound ML explainability; must run server-side where the fitted Pipeline objects live. Never in-browser. |
| Classifier comparison data (EXPL-03) | API / Backend | — | Requires access to fitted `VotingClassifier` base estimators (`get_individual_predictions`); server-side only. |
| Disagreement explanation (EXPL-04) | API / Backend | — | Already computed server-side by `disagreement.py`; only exposure/text enrichment is new, still backend. |
| Natural-language verdict (EXPL-05) | API / Backend | — | Text generation from paradigm scores; backend, as today. |
| Dashboard rendering (WEB-04, WEB-06) | Browser / Client | — | Hand-rolled SVG/DOM chart construction from JSON API responses; no server templating needed beyond the existing Jinja2 shell (`index.html`). |
| "Explain" button trigger / on-demand fetch | Browser / Client | API / Backend | Client fires `POST /explain`; backend computes and returns JSON; client renders. |
| CSP / no-CDN enforcement | Browser / Client | — | Enforced by the existing `security_headers_middleware` (`default-src 'self'`) in `src/api/main.py`; dashboard JS must not violate it. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `shap` | 0.52.0 (latest on PyPI, confirmed via registry JSON) | SHAP value computation (TreeExplainer/LinearExplainer/KernelExplainer) | Industry-standard unified explainability library; only ecosystem-standard choice named in the locked decision. `[VERIFIED: PyPI registry + local install test]` |

No other new Python packages are required. Vanilla JS (`document.createElementNS` for SVG) needs zero new frontend dependencies — confirmed feasible for all three needed chart types (see Architecture Patterns).

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `numba` | 0.68.0 (transitive via shap) | JIT compilation backend for SHAP's internal C-speed loops | Installed automatically as a shap core dependency on this platform (darwin/arm64) — not installed directly. `[VERIFIED: pip install + PyPI requires_dist]` |
| `llvmlite` | 0.50.0 (transitive via shap) | LLVM bindings numba depends on | Same as above — transitive, not installed directly. `[VERIFIED]` |

**`shap` does NOT pull in `torch`.** Confirmed by (a) PyPI `requires_dist` metadata for shap 0.52.0 — `torch` appears only under `extra == "test"`, never as a core/runtime dependency; and (b) installing `shap` into a fresh, isolated throwaway venv and confirming `pip list` shows only `llvmlite`, `numba`, `shap` — no `torch`. `torch` is already present in this project's `.venv` for an unrelated reason (Phase 7's `easyocr` dependency), not because of shap. `[VERIFIED: PyPI registry + isolated venv install test]`

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `shap.TreeExplainer` per-model | `shap.Explainer(pipeline.predict_proba, background)` (model-agnostic, auto-selects algorithm) | Simpler call site but loses the tree-structure speed advantage (falls back to Permutation/Kernel explainer even for tree models) — much slower, defeats the "fastest applicable explainer" locked decision. Rejected. |
| `shap.KernelExplainer` for ALL 7 models | `shap.TreeExplainer`/`LinearExplainer` for tree/linear models, `KernelExplainer` only for svm/mlp/nb, **or** SHAP only the single representative model | KernelExplainer-for-all is uniform code but ~10-50x slower per call than TreeExplainer and requires careful background-sample sizing for every model; the locked decision explicitly permits narrowing SHAP to "the primary/representative model." Recommended: **scope EXPL-02 to explaining `ml_models["phishing_detector"]` (RF) only** — it is the single model already used for the plain `/predict` endpoint, is a clean Pipeline (not a VotingClassifier), and TreeExplainer on it is the fastest, most defensible choice. Per-classifier SHAP across all 7 is explicitly NOT required by EXPL-02's wording ("feature importance dla decyzji ML", singular decision) and adds ~7x the endpoint complexity for no requirement-driven benefit. |
| Server-computed SVG (matplotlib → PNG) | Hand-rolled client-side SVG/DOM (locked decision 3) | Server-side chart images would need a `<img>` tag pointing at a data: URI or a static file — CSP `default-src 'self'` actually *permits* this (no CDN involved), but it duplicates rendering logic across languages, produces non-interactive/non-accessible raster output, and isn't what the locked decision specifies. Rejected in favor of the locked client-side SVG approach. |

**Installation:**
```bash
pip install shap>=0.52.0
```
Add to `requirements.txt` under a new `# Phase 9 - Explainability` section (after the Phase 8 block):
```
# Phase 9 - Explainability
# shap pulls in numba+llvmlite (JIT compiler, NOT torch) as core deps on this
# platform. torch already present in .venv is from Phase 7's easyocr, unrelated
# to shap. See 09-RESEARCH.md Package Legitimacy Audit + Standard Stack.
shap>=0.52.0
```

**Version verification:** `pip index versions shap` and the PyPI JSON API both confirm `0.52.0` as latest (2026-09-30), with a `cp312-abi3` wheel that installs cleanly on this project's Python 3.13 / macOS arm64 `.venv` (forward-compatible abi3 wheel). Actually installed and smoke-tested in the real project `.venv` during this research session — `shap.__version__ == '0.52.0'`.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|--------------|-----------|-------------|
| `shap` | PyPI | First released 2018 (version 0.1), 50+ releases through 0.52.0 — long-established | Not independently queried this session (well-established project; see note) `[ASSUMED: download figure]` | `github.com/shap/shap` (official org, confirmed via PyPI `project_urls.Repository`) | `[OK]` (verified via `slopcheck install shap`) | Approved |
| `numba` (transitive) | PyPI | Long-established (NumFOCUS-adjacent project, widely used in scientific Python) | Not queried | `github.com/numba/numba` | Not independently run (transitive dep, pulled automatically by shap) | Approved (transitive, standard scientific-Python tooling) |
| `llvmlite` (transitive) | PyPI | Long-established (paired release cadence with numba) | Not queried | `github.com/numba/llvmlite` | Not independently run (transitive) | Approved (transitive) |

**Packages removed due to slopcheck `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** none.

`shap` is tagged `[VERIFIED: PyPI registry]` for its existence/version claims (confirmed via `pip index versions`, the PyPI JSON API, and an actual successful install+import+TreeExplainer run in this session) — this satisfies the stricter "authoritative source AND slopcheck" bar, not just registry presence. The exact weekly-download figure was not queried via a separate download-stats API in this session; that single cell is marked `[ASSUMED]` in the Assumptions Log below out of caution, though the package's legitimacy is otherwise fully verified through three independent signals (official docs/readthedocs, GitHub org `shap/shap`, and a clean `slopcheck` pass).

## Architecture Patterns

### System Architecture Diagram

```
Browser (app.js — existing analyze flow, unchanged)
   |
   |  POST /predict/multi-paradigm  (fast path, UNCHANGED)
   v
FastAPI endpoint --> predict_url_multi() --> MultiParadigmAggregator.aggregate()
   |                                              |
   |                                              +--> active_rules (EXPL-01, reuse)
   |                                              +--> disagreement (EXPL-04, reuse)
   |                                              +--> explanation (EXPL-05, reuse)
   |                                              +--> [NEW] individual_predictions
   |                                                    (get_individual_predictions on
   |                                                     voting_soft — cheap, no SHAP)
   v
JSON response --> renderResult() (existing) + [NEW] renderDashboard()
   |                                              |
   |                                              +--> SVG bar chart: 7 ML + rules + bayesian (EXPL-03)
   |                                              +--> disagreement gauge (EXPL-04 visual)
   |
   |  user clicks "Explain" button (NEW, on-demand)
   v
POST /explain { url }  (NEW endpoint, SLOW PATH — separate from /predict*)
   |
   v
FastAPI /explain --> extract_url_features(url) --> scaler.transform()
   |                          |
   |                          v
   |                 shap.TreeExplainer(ml_models["phishing_detector"]
   |                                       .named_steps["classifier"])
   |                          |
   |                          v
   |                 top-10 signed (feature_name, shap_value, raw_value) triples
   |                          |
   v                          v
JSON /explain response <-- combine with existing explanation text (EXPL-05 enrichment)
   |
   v
renderShapChart() --> SVG diverging horizontal bar chart (WEB-04)
```

A reader can trace the primary use case (paste a URL -> see verdict -> click Explain -> see SHAP bars) entirely along this diagram: fast path (top) never touches SHAP; slow path (bottom) is isolated behind the `/explain` button and endpoint, exactly per locked decision 2.

### Recommended Project Structure
```
src/
├── explainability/                  # NEW module (mirrors src/paradigms/ layout)
│   ├── __init__.py
│   └── shap_explain.py              # explain_prediction(url) -> dict; owns the
│                                     # TreeExplainer instance + background cache
├── api/
│   ├── endpoints.py                 # + POST /explain (new), MultiParadigmResponse
│   │                                 #   gains individual_predictions (new, cheap)
│   ├── inference.py                 # + explain_url() shared helper (mirrors
│   │                                 #   predict_url_multi() pattern)
│   ├── main.py                      # lifespan: warm-import shap once at startup
│   │                                 #   (absorbs ~1.9s numba/llvmlite JIT cost)
│   └── models.py                    # + ExplainRequest, ExplainResponse,
│                                     #   FeatureContribution Pydantic models
├── web/
│   ├── static/
│   │   ├── app.js                   # + renderDashboard(), renderShapChart(),
│   │   │                            #   renderDisagreementGauge() — all SVG/DOM,
│   │   │                            #   no innerHTML (test_app_js_contract applies)
│   │   └── style.css                # + .dashboard, .shap-bar, .disagreement-gauge
│   └── templates/
│       └── index.html               # + "Explain" button, dashboard <section>
cache/
└── (reuse existing) url_training_data.joblib   # SHAP background source — DO NOT
                                                  # create a new background cache
```

### Pattern 1: Explainer selection by model family (locked decision 1)
**What:** Dispatch to the fastest applicable SHAP explainer based on the estimator's class, extracted from `pipeline.named_steps["classifier"]`. Always transform features through `pipeline.named_steps["scaler"]` first, and pass the **raw estimator** (not the whole Pipeline) to the explainer.
**When to use:** Any time a new sklearn Pipeline needs a SHAP explanation.
**Example (verified against the real `rf_optimized` Pipeline in this repo):**
```python
# Source: verified locally against shap 0.52.0 + this project's models/
import shap
import numpy as np

def get_explainer(pipeline):
    clf = pipeline.named_steps["classifier"]
    cls_name = type(clf).__name__
    if cls_name in ("RandomForestClassifier", "DecisionTreeClassifier",
                     "XGBClassifier", "GradientBoostingClassifier"):
        return shap.TreeExplainer(clf)
    if cls_name == "LogisticRegression":
        # LinearExplainer needs a background sample for the masker
        return shap.LinearExplainer(clf, background_scaled)
    # svm / mlp / nb: bounded KernelExplainer with a small k-means summary
    bg_summary = shap.kmeans(background_scaled, 5)
    return shap.KernelExplainer(clf.predict_proba, bg_summary)

def explain_one(pipeline, feature_dict):
    names = list(feature_dict.keys())
    X = np.array([list(feature_dict.values())])
    Xs = pipeline.named_steps["scaler"].transform(X)
    explainer = get_explainer(pipeline)
    sv = explainer.shap_values(Xs)
    sv_arr = np.array(sv)
    # RF/DT (sklearn native trees): shape (1, n_features, n_classes) -> take class 1
    # XGBoost: shape (1, n_features) directly (already class-1/margin contribution)
    contrib = sv_arr[0, :, 1] if sv_arr.ndim == 3 else sv_arr[0]
    top_idx = np.argsort(np.abs(contrib))[::-1][:10]
    return [
        {"feature": names[i], "shap_value": float(contrib[i]), "raw_value": float(X[0, i])}
        for i in top_idx
    ]
```
**Recommendation (per the "representative model" escape hatch in locked decision 1):** Implement `get_explainer`/`explain_one` for `ml_models["phishing_detector"]` (RF, TreeExplainer) only for v1. This fully satisfies EXPL-02 ("SHAP/LIME feature importance dla decyzji ML" — singular "decision", not "all 7 decisions") without needing to solve KernelExplainer background-tuning for svm/mlp/nb under a real latency budget. Document the dispatch table above so the planner/future work can extend to other classifiers if desired — but do not require it for phase completion.

### Pattern 2: Startup-time warm import (avoids the 1.9s cold-import tax)
**What:** `import shap` inside the FastAPI `lifespan` context manager (`src/api/main.py`), not lazily inside the endpoint handler.
**When to use:** Always, for this phase. Measured: cold `import shap` takes ~1.9s (numba JIT warmup + llvmlite loading) in this environment; after the module is imported once, subsequent `TreeExplainer` construction + `shap_values()` calls are single-digit milliseconds.
**Example:**
```python
# Source: pattern mirrors the existing OCR-reader warm-load in src/api/main.py lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    ...
    import shap  # warm the numba/llvmlite JIT once, off the request path
    ml_models["shap_module"] = shap
    ml_models["shap_background"] = joblib.load(
        "cache/url_training_data.joblib"
    )["X_train"]  # verified: 200x30, matches extract_url_features() schema exactly
    ...
```

### Pattern 3: Hand-rolled SVG bar chart (WEB-04, no CDN)
**What:** Build an SVG element tree with `document.createElementNS(SVG_NS, tag)`, set numeric attributes (`x`, `y`, `width`, `height`, `fill`) via `setAttribute`, and set any label text via `textContent` on a `<text>` node — never a markup-injection sink.
**When to use:** Classifier-comparison bars (EXPL-03), SHAP feature bars (EXPL-02/WEB-04), disagreement gauge (EXPL-04 visual).
**Example:**
```javascript
// Source: pattern consistent with existing app.js createElement/textContent-only style
const SVG_NS = "http://www.w3.org/2000/svg";

function renderBarChart(container, items, { width = 400, barHeight = 24 } = {}) {
  // items: [{ label, value }] where value is a probability 0..1
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(items.length * (barHeight + 8)));
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Classifier comparison chart");

  items.forEach((item, i) => {
    const y = i * (barHeight + 8);
    const rect = document.createElementNS(SVG_NS, "rect");
    rect.setAttribute("x", "120");
    rect.setAttribute("y", String(y));
    rect.setAttribute("width", String(Math.max(0, item.value) * (width - 130)));
    rect.setAttribute("height", String(barHeight));
    rect.setAttribute("class", item.value > 0.5 ? "bar-phishing" : "bar-legit");
    svg.appendChild(rect);

    const label = document.createElementNS(SVG_NS, "text");
    label.setAttribute("x", "0");
    label.setAttribute("y", String(y + barHeight - 6));
    label.textContent = item.label;  // safe: SVG <text> textContent, no markup parsing
    svg.appendChild(label);

    const valueLabel = document.createElementNS(SVG_NS, "text");
    valueLabel.setAttribute("x", String(125 + Math.max(0, item.value) * (width - 130)));
    valueLabel.setAttribute("y", String(y + barHeight - 6));
    valueLabel.textContent = (item.value * 100).toFixed(1) + "%";
    svg.appendChild(valueLabel);
  });

  container.replaceChildren(svg);
}
```
This satisfies `test_app_js_contract`'s ban on `innerHTML`/`insertAdjacentHTML`/`document.write` by construction (SVG DOM nodes built purely via `createElementNS` + `setAttribute` + `textContent`).

### Anti-Patterns to Avoid
- **Passing the whole `Pipeline` to `TreeExplainer`:** `shap.TreeExplainer` expects a raw tree estimator with `.tree_`/booster internals, not a `Pipeline` wrapper. Always unwrap via `pipeline.named_steps["classifier"]` and pre-transform features via `pipeline.named_steps["scaler"].transform(X)`.
- **Using `cache/train_balanced.joblib`, `cache/test.joblib`, or `cache/validation.joblib` as SHAP background:** these use the stale 35-column UCI-encoded schema (`having_IP_Address`, -1/0/1 values), incompatible with the deployed 30-feature pipelines. Use `cache/url_training_data.joblib['X_train']` instead (verified schema match).
- **Computing SHAP inside `/predict` or `/predict/multi-paradigm`:** violates locked decision 2 and will blow the sub-500ms latency budget those endpoints are held to elsewhere in the project.
- **Assuming SHAP output shape is uniform across model families:** sklearn-native tree models (RF, DT) return shape `(1, n_features, n_classes)`; XGBoost's `TreeExplainer` returns `(1, n_features)` directly (already the class-1/margin contribution). Code must branch on `sv_arr.ndim`, verified in this session.
- **Using `innerHTML`/template-string HTML for chart labels:** breaks the existing `test_app_js_contract` test and reintroduces an XSS sink for feature names / rule descriptions that ultimately originate from model/rule config (still attacker-adjacent if rule YAML or feature extraction ever handles less-trusted input).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Feature attribution for tree/linear models | A custom permutation-importance or gain-based heuristic | `shap.TreeExplainer` / `shap.LinearExplainer` | SHAP values have a game-theoretic (Shapley) consistency guarantee that ad-hoc "gain" or single-feature-perturbation heuristics lack; this is precisely why the project locked SHAP over a custom approach. |
| Cross-paradigm disagreement detection | A new disagreement scorer for the dashboard | `disagreement.py`'s existing `calculate_paradigm_disagreement()` / `get_disagreement_explanation()` | Already implemented, tested (20-test suite per STATE.md), and consistent with the Phase 3 classifier-disagreement convention (normalized Shannon entropy). Reinventing risks a second, inconsistent disagreement metric appearing in the same UI. |
| Rule-fired justification text | A new rules-summary formatter | `FiredRule` (existing Pydantic model) + `active_rules` (existing aggregator output) | Already renders correctly in `app.js`'s "Fired rules" section; Phase 9 only needs a new dashboard-section placement, not new formatting logic. |
| Chart rendering | A minimal bundled charting library ("just one small dependency") | Hand-rolled SVG per Pattern 3 above | Locked decision 3 explicitly forbids CDN/Node dependencies; the CSP (`default-src 'self'`) would block any CDN-hosted script anyway, and no build/bundler step exists in this project. |

**Key insight:** Nearly everything needed for EXPL-01/04/05 already exists as tested, working code from Phases 3 and 5 — the risk in this phase is not "can we compute X" but "are we accidentally recomputing X with different logic than the aggregator already uses," which would produce visibly inconsistent numbers between the verdict text and the new dashboard.

## Common Pitfalls

### Pitfall 1: Stale/incompatible cache files masquerading as valid SHAP background data
**What goes wrong:** `cache/train_balanced.joblib`, `cache/test.joblib`, and `cache/validation.joblib` all contain 35-column data using the old UCI ML pre-encoded feature schema (`having_IP_Address`, `URL_Length`, ... with -1/0/1 encoding) from before the Phase 3 retraining (STATE.md 03-04: "UCI ML pre-encoded features (-1/0/1) incompatible with our custom 30-feature extraction pipeline"). If used as SHAP background data, the array shape (35 cols) would not even match the live model's `n_features_in_` (30), causing either a hard crash or, worse, silent misalignment if code coerces shapes.
**Why it happens:** These cache files were never deleted after the schema migration; only `cache/url_training_data.joblib` was regenerated to match the live 30-feature schema.
**How to avoid:** Use `cache/url_training_data.joblib['X_train']` (200×30, verified `feature_names` match `extract_url_features().keys()` exactly) as the one and only SHAP background source for URL-paradigm explanations.
**Warning signs:** A SHAP call raising a feature-count mismatch exception, or `TreeExplainer`/`LinearExplainer` silently producing 35 or 34 features' worth of output instead of 30.

### Pitfall 2: Explaining the `VotingClassifier` ensemble directly
**What goes wrong:** `ml_models["voting_soft"]` is a `sklearn.ensemble.VotingClassifier` over 7 heterogeneous base estimators (RF, SVM, MLP, XGB, LR, NB, DT). SHAP has no dedicated fast explainer for a heterogeneous voting ensemble as a single unit — the only correct path would be `KernelExplainer(voting_clf.predict_proba, background)`, which is model-agnostic and comparatively slow, or an ad-hoc weighted sum of each base estimator's own SHAP values (mathematically defensible since Shapley values are additive across a linear combination of models, but adds real implementation complexity not required by EXPL-02).
**Why it happens:** It's tempting to explain "the ensemble" since that's what the primary verdict is based on.
**How to avoid:** Explain `ml_models["phishing_detector"]` (the single GA-optimized RF `Pipeline`, already used for the plain `/predict` endpoint) instead — it is the natural "representative model" the locked decision's escape hatch anticipates, and `TreeExplainer` on it is both fast and exact.
**Warning signs:** An `/explain` implementation that imports `KernelExplainer` and takes >1s per request in testing — a sign the wrong (ensemble) target was chosen.

### Pitfall 3: SHAP cold-import tax hitting the first user request
**What goes wrong:** `import shap` triggers numba/llvmlite JIT compilation of its internal kernels, measured at ~1.9s in this environment. If `shap` is imported lazily inside the `/explain` handler (matching the OCR module's lazy-import-inside-function convention used for *optional* Phase 7 deps), the very first `/explain` call from a demo audience member will appear to hang for ~2 seconds with no feedback.
**Why it happens:** Python only pays the numba JIT-warmup cost once per process, on first import — but "once per process" means "once per server restart," and if that import is deferred to first request, that request eats the cost.
**How to avoid:** Import `shap` in the FastAPI `lifespan` startup (unconditionally, since `shap` — unlike `easyocr`/`torch` — is a Phase 9 hard requirement, not an optional heavy dependency requiring graceful degradation).
**Warning signs:** Swagger UI / manual test showing the first `/explain` call taking noticeably longer than subsequent calls.

### Pitfall 4: `sv_arr.ndim` branching missed for XGBoost
**What goes wrong:** `TreeExplainer(rf_or_dt_classifier).shap_values(X)` returns shape `(1, n_features, 2)` (per-class), but `TreeExplainer(xgb_classifier).shap_values(X)` returns shape `(1, n_features)` directly (no class axis) — confirmed by direct testing in this session. Code written against one shape and applied uniformly to the other either crashes (`IndexError`) or silently extracts the wrong axis.
**Why it happens:** XGBoost's `TreeExplainer` backend computes binary-classification SHAP values as a single margin/log-odds contribution toward the positive class by default, differing from sklearn-native trees' per-class breakdown.
**How to avoid:** Branch on `np.array(shap_values).ndim` (3 → take `[..., 1]`; 2 → use directly) as shown in Pattern 1's `explain_one()`.
**Warning signs:** Since this phase's v1 recommendation scopes SHAP to the RF model only (Alternatives Considered, Pattern 1), this specific pitfall is avoided by construction for v1 — document it anyway for any future extension to XGBoost explanations.

### Pitfall 5: Confusing scaled-space SHAP values with raw feature values in the UI
**What goes wrong:** SHAP values are computed on the **scaler-transformed** feature array (since the `StandardScaler` step precedes the classifier in every Pipeline). If the UI displays the SHAP value next to the *raw* (unscaled) feature value without labeling which is which, technically literate reviewers (this is an academic thesis defense context) may reasonably ask why a SHAP magnitude doesn't match an intuitive raw-unit interpretation.
**Why it happens:** It's natural to want to show "path_length = 7" (human-readable, raw) next to its SHAP contribution — but the contribution was computed in standardized-units space.
**How to avoid:** Display the raw feature value for human readability (as this research's verified example does) but label the bar-chart axis/legend as "relative contribution" rather than implying a literal probability-point unit; this is a presentation nuance, not a bug, and does not require unscaling the SHAP values themselves (a common, accepted practice for StandardScaler'd Pipelines).
**Warning signs:** A thesis reviewer asking "why does a small raw value get a large bar" — mitigated by clear axis/legend labeling, not by algorithm changes.

## Code Examples

Verified patterns from direct execution against this repo's real artifacts in this research session:

### Full explain flow against the live GA-optimized RF model
```python
# Source: executed and verified in this research session against
# models/optimized/rf_optimized.joblib (via get_active_model("rf"))
import numpy as np
import shap
from src.optimization.model_registry import get_active_model
from src.features.extractors import extract_url_features

pipe = get_active_model("rf")  # auto-unwraps dict-wrapped GA artifact -> clean Pipeline
features = extract_url_features("https://paypal-login-security.tk/verify?acct=1")
names = list(features.keys())
X = np.array([list(features.values())])
Xs = pipe.named_steps["scaler"].transform(X)
clf = pipe.named_steps["classifier"]

explainer = shap.TreeExplainer(clf)   # ~3ms after shap is warm-imported
sv = explainer.shap_values(Xs)
contrib = np.array(sv)[0, :, 1]       # class 1 = phishing
top_idx = np.argsort(np.abs(contrib))[::-1][:10]
top_features = [
    {"feature": names[i], "shap_value": float(contrib[i]), "raw_value": float(X[0, i])}
    for i in top_idx
]
# Verified real output (order and signs will vary by input URL):
#   path_length            +0.1102  (value=7.0)
#   slash_count             +0.0874 (value=3.0)
#   special_char_count      +0.0610 (value=9.0)
#   url_length               +0.0453 (value=46.0)
#   hostname_length          +0.0418 (value=24.0)
```

### Loading the correct (schema-matching) background sample
```python
# Source: verified in this session — feature_names list matches
# extract_url_features().keys() exactly (30/30 match)
import joblib
bg = joblib.load("cache/url_training_data.joblib")
assert bg["feature_names"] == list(extract_url_features("https://example.com").keys())
X_background = bg["X_train"]  # shape (200, 30), balanced 100 phishing / 100 legitimate
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| SHAP required `numba`+`llvmlite` AND historically had a heavier C-extension build | SHAP 0.5x series still requires `numba`/`llvmlite` as core deps on most platforms (confirmed for 0.52.0 via PyPI `requires_dist`), but ships a `cp312-abi3` forward-compatible wheel so no local compilation is needed even on Python 3.13 | Wheel availability confirmed current (2026-09-30) | Zero-friction `pip install shap` on this project's Python 3.13/macOS-arm64 `.venv` — verified by actually installing it. |

**Deprecated/outdated:**
- An earlier training-data cache schema (UCI ML pre-encoded, -1/0/1 features) was superseded by the real-URL-feature retraining in Phase 3 (STATE.md "From 03-04"); the old cache files were never cleaned up and remain a trap for any phase that scans `cache/*.joblib` generically (see Pitfall 1).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | `shap`'s exact current weekly-download count / project age beyond "first released 2018, 50+ PyPI releases" was not independently queried via a download-stats API this session | Package Legitimacy Audit | Low — legitimacy is otherwise independently confirmed via PyPI registry metadata, official GitHub org (`shap/shap`), successful local install/import/TreeExplainer execution, and a clean `slopcheck` verdict. This is a belt-and-suspenders gap, not a load-bearing unknown. |
| A2 | `numba`/`llvmlite`'s own package legitimacy was not independently run through `slopcheck` (only inferred as "standard scientific-Python tooling") | Package Legitimacy Audit | Low — these are extremely well-known, decade-old PyData-ecosystem packages pulled in transitively by shap itself (not independently chosen); if `shap` is legitimate, its declared transitive deps are vetted by the shap maintainers' own release process. |
| A3 | EXPL-02's "ML predictions" (plural, generic) is interpreted as satisfied by explaining the single representative RF model rather than all 7 classifiers individually | Standard Stack (Alternatives Considered), Pattern 1 | Medium — if a stricter reading of EXPL-02 is intended (SHAP per-classifier for all 7), the phase scope and `/explain` endpoint complexity grow substantially (KernelExplainer tuning for svm/mlp/nb under a real latency budget). Recommend the planner confirm this scoping decision explicitly (flagged in Open Questions below) since no CONTEXT.md exists to have already locked it. |

**If this table is empty:** N/A — see rows above. All load-bearing technical claims (package existence/version, dependency graph, timing, SHAP output shapes, cache-file schema compatibility) were independently verified via tool execution in this session, not merely asserted from training knowledge.

## Open Questions (RESOLVED)

> RESOLVED by orchestrator locked decisions (2026-09-30), applied across plans 09-01..09-04:
> - **Q1 → RESOLVED: URL-only for v1.** SHAP feature importance is scoped to the URL paradigm (RF model, 30-col `cache/url_training_data.joblib` background). Email/SMS/image SHAP is out of v1 scope (no schema-matching background data). The UI labels SHAP importance as URL-only. (locked decision 1)
> - **Q2 → RESOLVED: NEW `ExplainResponse` model, single `/explain` call.** Do NOT extend `MultiParadigmResponse` — the recommendation to extend it is OVERRIDDEN. The consolidated `/explain` endpoint returns the 7 individual classifier predictions (reusing `get_individual_predictions`) inside a new dedicated response model, so existing tested models are untouched. (locked decision 2)
> - **Q3 → RESOLVED: expose `disagreement_explanation` as a new field** in the `/explain` payload (from `get_disagreement_explanation()`), satisfying WEB-06's "detailed explanation". (locked decision 2/4)

1. **Should `/explain` support email/SMS/image content types, or only URL?**
   - What we know: A schema-matching SHAP background sample (`cache/url_training_data.joblib`) exists only for the URL paradigm (30 features). No equivalent cached, schema-matching background sample exists for the email (65-feature) or SMS (70-feature) ensembles — `cache/email_sms/` was empty when checked.
   - What's unclear: Whether EXPL-02 is expected to cover all four content types (url/email/sms/image) or just the primary URL demo path, given ROADMAP.md Phase 9 doesn't specify content type and CONTEXT.md doesn't exist to clarify.
   - Recommendation: Scope `/explain` to URL content type for v1 (richest existing paradigm integration, verified background data available). If the planner wants email/SMS coverage too, a new background sample would need to be generated from the existing synthetic email/SMS training data (STATE.md "06-06": "Synthetic training datasets: 200 email samples... 200 SMS samples") — feasible but adds a data-prep task not yet scoped here.

2. **Should `MultiParadigmResponse` gain a permanent `individual_predictions` field, or should the dashboard fetch it via a second call to `/predict/ensemble`?**
   - What we know: `get_individual_predictions(voting_soft, X)` is cheap (a few ms, no retraining) and already used by `/predict/ensemble`. `/predict/multi-paradigm` currently omits it.
   - What's unclear: Whether adding a field to `MultiParadigmResponse` is preferred (single round-trip, but changes an existing, tested response schema) vs. a second parallel fetch from the frontend (no backend schema change, one extra HTTP round-trip, ~sub-50ms given both are local calls).
   - Recommendation: Extend the response (single round-trip is simpler for the dashboard and the field is purely additive/optional, won't break existing consumers of `MultiParadigmResponse`) — but this is a design choice the planner should make explicitly since it touches an existing, tested Pydantic model.

3. **Should `get_disagreement_explanation()`'s fuller text be exposed as a new field, or is the existing inline warning in `explanation` sufficient for EXPL-04?**
   - What we know: `disagreement.py`'s `get_disagreement_explanation()` produces a more detailed, per-paradigm-probability breakdown than the one-line warning currently embedded in `aggregator._generate_explanation()`.
   - What's unclear: Whether WEB-06 ("szczegółowe wyjaśnienie decyzji" / detailed explanation) is satisfied by the existing short warning or requires this fuller text.
   - Recommendation: Add it as a new optional `disagreement_explanation` field (cheap, already-computed function, just not currently called) — low-risk, directly addresses "detailed explanation" framing of WEB-06.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|----------|
| `shap` | EXPL-02 `/explain` endpoint | ✓ (installed during this research session) | 0.52.0 | — |
| `numba`/`llvmlite` | shap's internal JIT | ✓ (transitive, installed with shap) | 0.68.0 / 0.50.0 | — |
| `cache/url_training_data.joblib` | SHAP background sample | ✓ (pre-existing file, schema-verified) | — | If ever deleted, regenerate via `scripts/retrain_with_urls.py` (per STATE.md 03-04) or fall back to `shap.sample(X, k)` from any freshly-extracted batch of legitimate/phishing URLs. |
| Vanilla JS `document.createElementNS` (SVG DOM API) | WEB-04 dashboard charts | ✓ (native browser API, no install needed) | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none — everything required for this phase is already available or was installed and verified during this research session.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x (`.venv/bin/python -m pytest`), `fastapi.testclient.TestClient` for API tests |
| Config file | none dedicated — `conftest.py` at repo root sets `KMP_DUPLICATE_LIB_OK`/`OMP_NUM_THREADS` env vars before any OpenMP-linked library (xgboost, torch) is imported, and registers the `slow` marker |
| Quick run command | `.venv/bin/python -m pytest tests/test_api_explain.py -x` (new file, see Wave 0 gaps) |
| Full suite command | `.venv/bin/python -m pytest` (currently 388+ tests per STATE.md; must stay green) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|-------------|
| EXPL-01 | Fired rules with weights appear in dashboard-facing response | unit (existing endpoint, new dashboard-section assertion) | `pytest tests/test_api_multiparadigm.py -x` | ✅ (extend existing) |
| EXPL-02 | `POST /explain` returns top-10 SHAP features with names+signed values for a known phishing/legit URL | unit (mocked SHAP for speed) + `@pytest.mark.slow` integration (real SHAP, `pytest.importorskip("shap")`) | `pytest tests/test_api_explain.py -x` / `pytest tests/test_api_explain.py -m slow` | ❌ Wave 0 |
| EXPL-03 | Response includes all 7 individual classifier predictions + rules + Bayesian | unit | `pytest tests/test_api_multiparadigm.py -x` (extend) | ❌ Wave 0 (extend existing file) |
| EXPL-04 | Disagreement explanation text present and non-generic when `is_edge_case=True` | unit | `pytest tests/test_disagreement.py -x` (extend) | ❌ Wave 0 (extend existing file) |
| EXPL-05 | `/explain` response's enriched explanation mentions a top SHAP feature by name | unit | `pytest tests/test_api_explain.py -x` | ❌ Wave 0 |
| WEB-04 | `/static/app.js` defines the new chart-render functions and contains no XSS sinks (extends existing `test_app_js_contract`) | static asset contract test | `pytest tests/test_web_ui.py -x` | ✅ (extend existing `test_app_js_contract`) |
| WEB-06 | `GET /` HTML includes an "Explain" button / dashboard section markup | static asset contract test | `pytest tests/test_web_ui.py -x` | ❌ Wave 0 (extend existing file) |

### Sampling Rate
- **Per task commit:** fast/mocked subset — `pytest tests/test_api_explain.py -x -m "not slow"` plus the relevant extended existing files.
- **Per wave merge:** full suite minus slow markers — `pytest -m "not slow"`.
- **Phase gate:** full suite green including `-m slow` (real SHAP execution) before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_api_explain.py` — new file covering `POST /explain`: happy path (mocked SHAP via monkeypatch), 503 when `phishing_detector` not loaded, top-10 ordering/shape assertions, and a `pytest.mark.slow` test guarded by `pytest.importorskip("shap")` that runs the real `TreeExplainer` end-to-end against a known URL (mirrors this research session's manual verification).
- [ ] Extend `tests/test_api_multiparadigm.py` — assert `individual_predictions` (if added per Open Question 2) is present and contains all 7 classifier names.
- [ ] Extend `tests/test_disagreement.py` — assert the new `disagreement_explanation`/`paradigm_probabilities` fields (if added per Open Question 3) round-trip correctly through the API response model.
- [ ] Extend `tests/test_web_ui.py` — add assertions for the new dashboard markup (Explain button, chart container elements) and extend `test_app_js_contract`-style checks to cover any new JS functions (still asserting absence of `innerHTML`/`insertAdjacentHTML`/`document.write`).
- [ ] Framework install: none — pytest/httpx/TestClient already present; only the `shap` runtime dependency itself is new (see Package Legitimacy Audit).

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|-------------------|
| V2 Authentication | No | Project is an explicit "open demo, no auth" per PROJECT.md Out of Scope. |
| V3 Session Management | No | No sessions in this project. |
| V4 Access Control | No | Open demo, no roles. |
| V5 Input Validation | Yes | `/explain` request body reuses the existing `URLRequest` Pydantic model (http/https prefix check, 10-2048 char length bounds) — no new input surface, no new validation logic needed. |
| V6 Cryptography | No | Not applicable to this phase. |
| V12 Output Encoding / XSS Prevention | Yes | Dashboard rendering (feature names, rule descriptions, matched values, SHAP values) MUST use `textContent`/`createElement`/`createElementNS` only — never `innerHTML`, per the existing (and to-be-extended) `test_app_js_contract`. |
| V13 API and Web Service Security | Yes | `Content-Security-Policy: default-src 'self'` (existing `security_headers_middleware`) must continue to apply to `/explain` and to `GET /` (the new dashboard markup lives in the already-covered `index.html`) — no new CSP exemption needed since no CDN asset is introduced. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| SHAP compute Denial-of-Service: an attacker submits many/rapid `POST /explain` requests, each costing several ms-to-tens-of-ms of CPU (and, for any future non-RF explainer, potentially much more via `KernelExplainer`) | Denial of Service | Scope v1 to `TreeExplainer` on RF only (fast, ~3ms per call — verified) rather than `KernelExplainer` on slower models; no new rate-limiting infrastructure exists in this project (open demo, consistent with PROJECT.md scope) so this is a residual risk to flag, not fully mitigate, in an academic-demo context. If deployed beyond the thesis defense, recommend adding a simple per-IP rate limit on `/explain` specifically (it is the one CPU-heavier endpoint introduced by this phase). |
| Reflected/stored XSS via rendered feature names or rule `matched_values` in the new dashboard charts | Tampering / Information Disclosure (XSS) | `textContent`/`createElementNS` + `setAttribute` only for all new SVG/DOM chart code (Pattern 3); `matched_values` already flows through the existing rules-list renderer safely today — the same discipline must extend to any new dashboard code touching the same or newly-added fields (feature names from SHAP are drawn from a fixed, code-defined `feature_names` list — not attacker-controlled — but rule `matched_values`/`description` strings originate from rule YAML config + substring matches against attacker-supplied URL/email/SMS text, so the existing textContent-only discipline remains load-bearing). |
| CSP bypass via an accidentally-added CDN `<script src="https://...">` tag in the new dashboard template markup | Tampering | Locked decision 3 forbids CDN dependencies entirely; the existing `security_headers_middleware` CSP (`default-src 'self'`) would block any such script from executing even if accidentally added, but Wave 0 tests should still assert no external script tags exist in `index.html`'s new dashboard section, consistent with the spirit of `test_index_has_form`/`test_app_js_contract`. |

## Sources

### Primary (HIGH confidence)
- PyPI JSON API (`https://pypi.org/pypi/shap/json`) — shap 0.52.0 `requires_dist`, confirming `numba`/`llvmlite` as core deps and `torch` as test-extra-only. Queried directly in this session.
- PyPI JSON API (`https://pypi.org/pypi/numba/json`, `.../llvmlite/json`) — version/Python-compatibility confirmation for numba 0.68.0, llvmlite 0.50.0.
- Direct local execution: `pip install shap` into both the project's real `.venv` (Python 3.13, macOS arm64) and an isolated throwaway venv; `shap.TreeExplainer`/`LinearExplainer`/`KernelExplainer` run against this repo's actual `models/*.joblib` Pipeline artifacts; `cache/url_training_data.joblib` schema compared directly against `extract_url_features()` live output.
- This repo's own source: `src/paradigms/aggregation/aggregator.py`, `disagreement.py`, `src/api/endpoints.py`, `src/api/models.py`, `src/api/inference.py`, `src/api/main.py`, `src/api/web.py`, `src/web/static/app.js`, `tests/test_web_ui.py`, `src/optimization/model_registry.py`.
- `slopcheck install shap` — local execution, `[OK]` verdict.

### Secondary (MEDIUM confidence)
- WebSearch on "shap python package dependencies numba does it require torch" — partially superseded/corrected by the direct PyPI registry query above (the search suggested numba/llvmlite had become fully optional in recent SHAP releases; direct registry inspection of 0.52.0's `requires_dist` shows numba/llvmlite remain required on this platform (darwin/arm64), so the registry data was treated as authoritative over the search summary).

### Tertiary (LOW confidence)
- None used as load-bearing claims — all package/dependency/timing claims in this document were independently tool-verified rather than taken from single unverified sources.

## Metadata

**Confidence breakdown:**
- Standard stack (shap + its dependency graph): HIGH — directly installed, imported, and exercised against this repo's real model artifacts in-session; version/dependency claims cross-checked against PyPI registry metadata.
- Architecture (explainer dispatch, endpoint placement, SVG rendering feasibility): HIGH — TreeExplainer/LinearExplainer/KernelExplainer timings measured directly; SVG/DOM approach is a direct extension of the already-shipped, tested `app.js` pattern (`createElement`+`textContent`), not a novel technique.
- Pitfalls (stale cache schema, SHAP output-shape variance, cold-import cost): HIGH — each pitfall was independently reproduced/measured in this session (schema mismatch confirmed by diffing column lists; XGBoost's differing output shape confirmed by direct execution; cold-import timing measured directly).

**Research date:** 2026-09-30
**Valid until:** 2026-10-30 (30 days — stable ecosystem, but re-verify `shap` version/wheel availability if the phase is implemented significantly later, since shap ships frequent minor releases)

## RESEARCH COMPLETE
