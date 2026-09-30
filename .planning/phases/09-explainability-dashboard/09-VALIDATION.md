---
phase: 9
slug: explainability-dashboard
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-30
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 with FastAPI `TestClient`; `conftest.py` sets OpenMP env + `slow` marker |
| **Config file** | none — default `test_*.py` discovery under `tests/` |
| **Quick run command** | `.venv/bin/python -m pytest tests/test_api_explain.py -x -m "not slow"` |
| **Full suite command** | `.venv/bin/python -m pytest` |
| **Estimated runtime** | ~60s full suite; fast explain subset ~2s (SHAP mocked). Real-SHAP `slow` test adds a few seconds. |

**Interpreter note:** run with the project `.venv`. SHAP fast unit tests MOCK the explainer (monkeypatch) for speed; a single `@pytest.mark.slow` test runs the real `TreeExplainer` guarded by `pytest.importorskip("shap")`.

---

## Sampling Rate

- **After every task commit:** `.venv/bin/python -m pytest tests/test_api_explain.py -x -m "not slow"` plus the extended existing files touched
- **After every plan wave:** `.venv/bin/python -m pytest -m "not slow"` (full fast suite)
- **Before `/gsd:verify-work`:** full suite green INCLUDING `-m slow` (real SHAP execution) + human/browser check of the dashboard visuals
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 9-01-01 | 01 | 1 | EXPL-02, EXPL-03, EXPL-05, WEB-06 | — | Wave-0 tests: `/explain` contract, dashboard markup, JS XSS-guard | API/static | `.venv/bin/python -m pytest tests/test_api_explain.py -x -m "not slow"` | ❌ W0 | ⬜ pending |
| 9-02-01 | 02 | 2 | EXPL-02 | T-DoS, T-XSS | `POST /explain` SHAP top-10 (RF, TreeExplainer, correct background sample); URL-only v1; reuses URLRequest validation | unit+slow | `.venv/bin/python -m pytest tests/test_api_explain.py -x` | ❌ W0 | ⬜ pending |
| 9-02-02 | 02 | 2 | EXPL-03, EXPL-04, EXPL-05 | — | `/explain` consolidated payload: 7 ML preds + paradigm contributions + disagreement fuller text + NL explanation | unit | `.venv/bin/python -m pytest tests/test_api_explain.py tests/test_disagreement.py -x` | ❌ W0 | ⬜ pending |
| 9-03-01 | 03 | 3 | EXPL-03, WEB-04 | T-XSS | Hand-rolled SVG bar charts (classifier comparison + SHAP importance); createElementNS/textContent only, no innerHTML | static/JS | `.venv/bin/python -m pytest tests/test_web_ui.py -x` | ❌ W0 | ⬜ pending |
| 9-03-02 | 03 | 3 | EXPL-01, WEB-06 | T-XSS | Dashboard wires Explain button → /explain → render rules/disagreement/NL + charts, XSS-safe | static/JS | `.venv/bin/python -m pytest tests/test_web_ui.py -x` | ❌ W0 | ⬜ pending |
| 9-04-01 | 04 | 4 | all | — | Human browser verification of dashboard rendering | manual | (human-verify checkpoint) | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*Task IDs provisional — the planner finalizes exact numbering.*

---

## Wave 0 Requirements

- [ ] `tests/test_api_explain.py` — NEW: `POST /explain` happy path (mocked SHAP via monkeypatch), 503 when detector not loaded, top-10 ordering/shape, `@pytest.mark.slow` real-`TreeExplainer` test guarded by `pytest.importorskip("shap")`
- [ ] Extend `tests/test_api_multiparadigm.py` — assert the consolidated `/explain` payload contains all 7 classifier predictions + paradigm contributions
- [ ] Extend `tests/test_disagreement.py` — assert the fuller `disagreement_explanation` text round-trips through the API response
- [ ] Extend `tests/test_web_ui.py` — new dashboard markup (Explain button, chart containers) + extend `test_app_js_contract` to cover new chart-render JS (still asserting no `innerHTML`/`insertAdjacentHTML`/`document.write` and no external `<script src>`)
- [ ] Add `shap` to requirements.txt (pulls numba/llvmlite, NOT torch); pin sensibly
- [ ] SHAP background sample: use `cache/url_training_data.joblib` (30-col, schema matches `extract_url_features`) — NEVER the stale 35-col `train_balanced/test/validation.joblib` (Pitfall 1)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dashboard renders correctly in a real browser | EXPL-02/03, WEB-04, WEB-06 | SVG chart rendering + Explain-button flow live in vanilla JS; no JS runtime in CI | `uvicorn src.api.main:app`; analyze a URL, click "Explain": confirm the classifier-comparison bar chart (7 ML + rules + Bayesian), the SHAP top-10 feature-importance chart, fired rules with weights, disagreement text, and NL explanation all render; confirm XSS-safe with adversarial input; check desktop + 375px |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter (after execution)

**Approval:** pending
