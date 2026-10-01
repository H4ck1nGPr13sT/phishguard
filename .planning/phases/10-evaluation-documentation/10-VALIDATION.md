---
phase: 10
slug: evaluation-documentation
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-10-01
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 (`.venv/bin/python -m pytest`); `conftest.py` sets OpenMP env + `slow` marker |
| **Config file** | none — default `test_*.py` discovery under `tests/` |
| **Quick run command** | `.venv/bin/python -m pytest tests/test_eval_report.py tests/test_docs.py -x -q` |
| **Full suite command** | `.venv/bin/python -m pytest -q` (452 passed, 1 skipped as of Phase 9) |
| **Estimated runtime** | ~60s full suite; eval/docs subset a few seconds |

**matplotlib note:** force the non-interactive `Agg` backend inside `tests/test_eval_report.py` and in `scripts/generate_eval_report.py` (`matplotlib.use("Agg")` before importing pyplot) — Pitfall 2, so collection/runs never trigger an interactive backend.

---

## Sampling Rate

- **After every task commit:** `.venv/bin/python -m pytest tests/test_eval_report.py tests/test_docs.py -x -q`
- **After every plan wave:** `.venv/bin/python -m pytest -q` (full suite — confirm no regression)
- **Before `/gsd:verify-work`:** full suite green + human-verify checkpoint reviewing `docs/algorithms/*.md` prose for thesis-grade accuracy
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | EVAL-05/06, DOC-03/04/05 | Wave-0 tests RED-by-design | unit | `.venv/bin/python -m pytest tests/test_eval_report.py tests/test_docs.py --collect-only -q` | ❌ W0 | ⬜ pending |
| 10-02-01 | 02 | 2 | EVAL-05 | Ablation by zeroing on `cache/url_training_data.joblib` (30-col, NOT stale 35-col); `visual` group marked N/A (no trained classifier) | unit | `.venv/bin/python -m pytest tests/test_eval_report.py -k ablat -x` | ❌ W0 | ⬜ pending |
| 10-02-02 | 02 | 2 | EVAL-06 | Exportable PDF (confusion matrix + ROC via matplotlib Agg) + CSV (metrics in [0,1]) | unit+smoke | `.venv/bin/python -m pytest tests/test_eval_report.py -x` | ❌ W0 | ⬜ pending |
| 10-03-01 | 03 | 3 | DOC-03 | OpenAPI routes carry summary/description; openapi.json exportable | unit | `.venv/bin/python -m pytest tests/test_api.py -k openapi -x` | ❌ W0 | ⬜ pending |
| 10-03-02 | 03 | 3 | DOC-04, DOC-05 | Mermaid architecture + data-flow diagrams; valid diagram types; links resolve | unit | `.venv/bin/python -m pytest tests/test_docs.py -x` | ❌ W0 | ⬜ pending |
| 10-04-01 | 04 | 4 | DOC-06, DOC-07 | Theory docs for all algorithms (docs/algorithms/*.md, module-structured); internal links resolve; README refreshed (Pitfall 4) | unit+manual | `.venv/bin/python -m pytest tests/test_docs.py -x` + human-verify | ❌ W0 | ⬜ pending |
| 10-05-01 | 05 | 5 | all | Human review of thesis-grade prose accuracy | manual | (human-verify checkpoint) | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red. Task IDs provisional — the planner finalizes numbering/plan count.*

---

## Wave 0 Requirements

- [ ] `tests/test_eval_report.py` — EVAL-05 (ablation correctness + cache-schema regression guard: must use the 30-col `cache/url_training_data.joblib`, never the stale/empty 35-col caches) + EVAL-06 (PDF/CSV creation + schema, matplotlib Agg)
- [ ] `tests/test_docs.py` — DOC-04/05 (Mermaid block diagram-type sanity) + internal Markdown link resolution (stdlib `re`/`pathlib`, no new dep)
- [ ] Extend `tests/test_api.py` — OpenAPI route `summary` populated (DOC-03 regression guard)
- [ ] No framework install; NO new runtime deps (matplotlib/pandas/jinja2 already present; Mermaid renders on GitHub natively)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Thesis-grade accuracy of algorithm theory prose | DOC-06, DOC-07 | Correctness/academic quality of descriptions (ML classifiers, GA, Bayesian, rules, aggregation, OCR, SHAP) cannot be auto-verified | Read `docs/algorithms/*.md`; confirm each algorithm is described correctly, at thesis standard, and consistent with `praca-inzynierska.pdf` terminology; confirm architecture/data-flow Mermaid diagrams render and are accurate |
| Rendered evaluation report | EVAL-06 | PDF visual quality (readable confusion matrices, ROC curves, metric tables) | Open the generated PDF; confirm plots render and are legible |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter (after execution)

**Approval:** pending
