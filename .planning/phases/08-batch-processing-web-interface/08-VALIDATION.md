---
phase: 8
slug: batch-processing-web-interface
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-30
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 with FastAPI `TestClient` (httpx 0.28.1) |
| **Config file** | none — `conftest.py` at repo root sets OpenMP env + registers `slow` marker |
| **Quick run command** | `.venv/bin/python -m pytest tests/test_web_ui.py tests/test_batch_api.py -x` |
| **Full suite command** | `.venv/bin/python -m pytest` |
| **Estimated runtime** | ~60s full suite; web/batch subset ~2s (no models needed for page-serving tests) |

**Interpreter note:** always run with the project `.venv` interpreter. Page-serving and static-asset tests need no models; batch tests monkeypatch the per-row inference helper for deterministic speed.

---

## Sampling Rate

- **After every task commit:** `.venv/bin/python -m pytest tests/test_web_ui.py tests/test_batch_api.py -x`
- **After every plan wave:** `.venv/bin/python -m pytest` (full suite)
- **Before `/gsd:verify-work`:** full suite green PLUS a human browser check (desktop + 375px mobile) of rendering and batch polling
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 8-01-01 | 01 | 1 | WEB-01 | — | `GET /` returns HTML paste form; JSON root moved to `/api/info` | API | `.venv/bin/python -m pytest tests/test_web_ui.py::test_index_has_form -x` | ❌ W0 | ⬜ pending |
| 8-01-02 | 01 | 1 | WEB-08 | T-clickjack | viewport meta + `@media` + table-scroll wrapper; security headers | API/static | `.venv/bin/python -m pytest tests/test_web_ui.py::test_responsive_markers -x` | ❌ W0 | ⬜ pending |
| 8-02-01 | 02 | 2 | WEB-02, WEB-03 | T-XSS | file inputs (.eml/.png/.jpg/.csv); severity band; NO innerHTML (XSS guard) | API/static | `.venv/bin/python -m pytest tests/test_web_ui.py::test_app_js_contract -x` | ❌ W0 | ⬜ pending |
| 8-03-01 | 03 | 3 | INPUT-05 | T-V5, T-DoS | `POST /batch` valid CSV → job id; bad ext/header/size/rows → 400; in-memory only | API | `.venv/bin/python -m pytest tests/test_batch_api.py -x` | ❌ W0 | ⬜ pending |
| 8-03-02 | 03 | 3 | WEB-07 | T-DoS, T-info | `GET /batch/{id}` status/total/done/rows; offset slice; 404; per-row error isolation; MAX_JOBS eviction | API/unit | `.venv/bin/python -m pytest tests/test_batch_api.py::test_polling -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*Task IDs are provisional — the planner finalizes exact numbering.*

---

## Wave 0 Requirements

- [ ] `tests/test_web_ui.py` — WEB-01/02/03/08 (form, file inputs, severity-band + XSS-guard contract, responsive markers)
- [ ] `tests/test_batch_api.py` — INPUT-05 + WEB-07 (upload validation, job id, polling, offset slice, per-row error isolation, 404, size/row caps)
- [ ] `tests/fixtures/batch_sample.csv` — sample CSV (also shipped as `static/sample.csv`)
- [ ] Update the existing root-endpoint assertion in `tests/test_api.py` (JSON root moves to `/api/info`)
- [ ] No framework install needed (jinja2/python-multipart/httpx already present)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Rendering + live batch polling in a real browser | WEB-01/02/03/07/08 | Severity logic and DOM rendering live in vanilla JS; no JS runtime in CI (no Node by locked decision) | Run `uvicorn src.api.main:app`; in a browser at desktop width and 375px mobile (devtools device mode): submit a pasted URL/email/SMS, upload an .eml/.png/.csv, confirm verdict + Low/Medium/High/Critical band render, and watch the batch progress bar + results table update via polling |

*The <500ms contract is unaffected here (web phase). The batch endpoint is intentionally async (background job + polling).*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter (after execution)

**Approval:** pending
