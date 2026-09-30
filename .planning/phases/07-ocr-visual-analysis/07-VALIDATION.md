---
phase: 7
slug: ocr-visual-analysis
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-30
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 (389 tests currently collect cleanly via the project `.venv`) |
| **Config file** | none — tests discovered by default `test_*.py` convention under `tests/` |
| **Quick run command** | `.venv/bin/python -m pytest tests/features/test_image_features.py -x` |
| **Full suite command** | `.venv/bin/python -m pytest` |
| **Estimated runtime** | ~60 seconds (full suite); quick image-feature run ~2s (no torch, uses fake/Null OCR backend) |

**Interpreter note:** always run with the project `.venv` interpreter. A bare `python3 -m pytest` fails with ~20 collection errors due to missing project-scoped packages.

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/features/test_image_features.py -x` (fast, no torch — uses `NullOCRBackend`/fake injected backend)
- **After every plan wave:** Run `.venv/bin/python -m pytest` (full suite; OCR integration tests use `pytest.importorskip("easyocr")` so they skip cleanly when heavy deps are absent)
- **Before `/gsd:verify-work`:** Full suite must be green (OCR integration test either passing or cleanly skipped)
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 7-01-01 | 01 | 1 | INPUT-06 | — | OCR text extraction via mockable backend; no torch required for unit path | unit | `.venv/bin/python -m pytest tests/features/test_image_features.py -k ocr -x` | ❌ W0 | ⬜ pending |
| 7-01-02 | 01 | 1 | INPUT-07 | — | Perceptual-hash brand similarity + layout/color heuristics are deterministic | unit | `.venv/bin/python -m pytest tests/features/test_image_features.py -k visual -x` | ❌ W0 | ⬜ pending |
| 7-02-01 | 02 | 2 | INPUT-04 | T-V5 / T-V12 | Upload validation: type allowlist, size cap, `Image.verify()`, in-memory only | unit + API | `.venv/bin/python -m pytest tests/test_api_image.py -x` | ❌ W0 | ⬜ pending |
| 7-02-02 | 02 | 2 | INPUT-06 | — | OCR'd text feeds existing text/email pipeline; end-to-end verdict | integration | `.venv/bin/python -m pytest tests/integration/test_image_integration.py -m slow` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*Task IDs are provisional — the planner finalizes exact numbering.*

---

## Wave 0 Requirements

- [ ] `tests/features/test_image_features.py` — covers INPUT-06 (OCR-text-to-features path via fake backend) and INPUT-07 (perceptual hash + layout/color heuristics)
- [ ] `tests/test_api_image.py` — covers INPUT-04 (upload validation: wrong type, oversized, corrupt image → 400; happy path → 200 with `content_type="image"`)
- [ ] `tests/integration/test_image_integration.py` — end-to-end with real EasyOCR backend; uses `pytest.importorskip("easyocr")` to degrade gracefully
- [ ] Fixture images under `tests/fixtures/` — a handful of small PNG/JPG (clear text, blank, corrupt/truncated, login-form-like); none exist yet
- [ ] Framework install — `easyocr imagehash opencv-python-headless pytesseract` added to `requirements.txt` (needed for integration test and runtime, not the fast unit path)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real OCR latency vs the <500ms contract | INPUT-06 | Requires real EasyOCR inference on representative images; timing is environment-dependent and not captured by unit tests | Warm reader at startup, then time `/predict/image` on 5 sample screenshots; record p50/p95; confirm documented sync-with-exception decision holds |

*The <500ms hard contract remains binding for url/email/sms endpoints. `/predict/image` is an explicit documented exception (OCR is inherently slower); reader is warmed at lifespan startup.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
