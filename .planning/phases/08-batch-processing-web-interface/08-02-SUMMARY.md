---
phase: 08-batch-processing-web-interface
plan: 02
subsystem: ui
tags: [fastapi, jinja2, starlette-staticfiles, csp, security-headers, responsive-css]

# Dependency graph
requires:
  - phase: 08-batch-processing-web-interface
    provides: "Wave 0 test contracts (tests/test_web_ui.py) defining the served-HTML/static/CSP/root-move behavior this plan implements"
provides:
  - "GET / serving a responsive Jinja2 HTML index (src/api/web.py + src/web/templates/index.html)"
  - "GET /api/info as the relocated JSON service-info payload (src/api/endpoints.py)"
  - "StaticFiles mounted at /static, anchored at WEB_DIR (CWD-independent)"
  - "src/web/static/style.css: mobile-first responsive CSS scaffold with severity band classes and .table-scroll"
  - "Scoped security-headers middleware (nosniff, X-Frame-Options DENY, CSP default-src 'self' exempting /docs,/redoc,/openapi.json)"
affects: [08-03-single-sample-js, 08-05-batch-ui, 08-06]

# Tech tracking
tech-stack:
  added: [jinja2>=3.1.0]
  patterns:
    - "WEB_DIR = Path(__file__).resolve().parent.parent / 'web' anchors templates/static at module location, not CWD"
    - "Jinja2Templates request-first TemplateResponse(request, 'name.html', ctx) signature (Starlette >=0.29)"
    - "@app.middleware('http') with a path-prefix exemption list for CSP, applied after call_next"
    - "No inline <script>/<style>; all JS external (/static/app.js, 08-03) and all CSS external (/static/style.css) to satisfy CSP default-src 'self'"

key-files:
  created:
    - src/api/web.py
    - src/web/templates/index.html
    - src/web/static/style.css
  modified:
    - requirements.txt
    - src/api/main.py
    - src/api/endpoints.py
    - tests/test_api.py
    - tests/test_api_multiparadigm.py

key-decisions:
  - "JSON root moved to GET /api/info (not content-negotiated); all existing tests asserting on GET / JSON were updated in lockstep, including one (test_api_multiparadigm.py) not listed in the plan's files_modified but broken by the same route move"
  - "CSP exemption scoped by path prefix (/docs, /redoc) and exact match (/openapi.json) rather than a blanket docs-mode flag, keeping the middleware dependency-free and easy to audit"
  - "index.html ships only scaffold containers (#result, #upload-area, #batch-area) for 08-03/08-05 to populate — no JS wiring in this plan, per plan scope"

requirements-completed: [WEB-01, WEB-08]

# Metrics
duration: 18min
completed: 2026-09-30
---

# Phase 08 Plan 02: FastAPI Web UI Wiring Summary

**FastAPI now serves a responsive Jinja2 HTML index at `/` (previously JSON), with JSON service info relocated to `/api/info`, static assets mounted at `/static`, and a scoped CSP/nosniff/frame-deny security-headers middleware that keeps Swagger UI working.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-09-30T20:12:00+02:00 (approx)
- **Completed:** 2026-09-30T20:19:26+02:00
- **Tasks:** 3 (plan) + 1 (deviation fix)
- **Files modified:** 8 (3 created, 5 modified)

## Accomplishments
- `GET /` now serves a responsive, semantic HTML5 page (viewport meta, url/email/sms selector, textarea, empty result/upload/batch containers, uncalibrated-severity-bands disclaimer footer) via `src/api/web.py`'s `web_router` + `Jinja2Templates`.
- The old JSON info payload moved cleanly to `GET /api/info`, with every existing test asserting on the old location updated (including one file outside the plan's declared scope, `tests/test_api_multiparadigm.py`, caught by running the full suite).
- `StaticFiles` mounted at `/static`, anchored at `WEB_DIR` so it works regardless of the process's CWD; `style.css` is a hand-written ~185-line mobile-first stylesheet with `@media (min-width: 640px)`, 44px touch targets, `.table-scroll{overflow-x:auto}`, and four severity-band classes (color + text, never color-only).
- Security-headers middleware sets `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY` on every response, and `Content-Security-Policy: default-src 'self'` on every response except `/docs`, `/redoc`, `/openapi.json` — verified Swagger UI and the OpenAPI schema still return 200.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add jinja2, create web_router, mount StaticFiles, move JSON root to /api/info** - `a51bd44` (feat)
2. **Task 2: Build responsive base template + mobile-first CSS** - `d973005` (feat)
3. **Task 3: Security-headers middleware (CSP scoped, nosniff, frame options)** - `8c378b5` (feat)
4. **Deviation fix: update test_api_multiparadigm root assertion** - `2a426e9` (fix, Rule 1)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `src/api/web.py` - `WEB_DIR`, `templates` (Jinja2Templates), `web_router` with `GET /` → `index.html`
- `src/web/templates/index.html` - responsive single-page UI: content-type selector, textarea/submit, `#result`, `#upload-area` (.eml + image inputs), `#batch-area` (.csv input + `{{ max_csv_rows }}`, `.table-scroll`-wrapped results table), footer disclaimer, external-only `/static/style.css` + `/static/app.js`
- `src/web/static/style.css` - mobile-first CSS: `@media (min-width:640px)` two-column layout, `max-width:960px` container, `rem` type, 44px inputs/buttons, `.table-scroll`, `.sev-low/.sev-medium/.sev-high/.sev-critical`
- `src/api/main.py` - `StaticFiles` mount at `/static`; `web_router` included before `endpoints.router`; `security_headers_middleware` (nosniff, X-Frame-Options, scoped CSP)
- `src/api/endpoints.py` - `GET /` → `GET /api/info` (`root()` renamed `api_info()`), payload unchanged; module docstring updated
- `requirements.txt` - `jinja2>=3.1.0` added under new `# Phase 8 - Web Interface` section
- `tests/test_api.py` - `TestRootEndpoint` JSON assertions retargeted to `/api/info`; new `test_root_serves_html` asserting `GET /` is `text/html`
- `tests/test_api_multiparadigm.py` - `TestRootEndpoint.test_root_lists_multiparadigm_endpoint` retargeted to `/api/info` (deviation fix, not in plan's declared `files_modified`)

## Decisions Made
- Kept the JSON root move as a hard relocation to `/api/info` (locked decision from 08-RESEARCH, A4) rather than content negotiation — simpler, matches the plan's explicit acceptance criteria and test contracts.
- CSP exemption implemented as two small module-level constants (`_CSP_EXEMPT_PREFIXES`, `_CSP_EXEMPT_EXACT`) checked in the middleware, keeping the security logic in one place and trivially auditable against the threat register (T-08-05).
- `index.html`'s batch/upload areas are deliberately inert placeholders (stable ids only) — no JS behavior added here; that is explicitly 08-03/08-05 scope per the plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pre-existing test broken by the GET / → GET /api/info move**
- **Found during:** Wave-gate full-suite run after Task 3
- **Issue:** `tests/test_api_multiparadigm.py::TestRootEndpoint::test_root_lists_multiparadigm_endpoint` asserted on `GET /` returning the JSON `endpoints` list. This file is not in the plan's `files_modified` list, so it wasn't touched in Task 1, but the root-move in Task 1 broke it (route now returns HTML, `.json()` call would fail the assertion).
- **Fix:** Retargeted the test to `GET /api/info`, same pattern as `tests/test_api.py::TestRootEndpoint`.
- **Files modified:** `tests/test_api_multiparadigm.py`
- **Verification:** `pytest tests/test_api_multiparadigm.py::TestRootEndpoint -q` → 1 passed
- **Committed in:** `2a426e9`

---

**Total deviations:** 1 auto-fixed (1 bug fix, Rule 1)
**Impact on plan:** Necessary correctness fix directly caused by this plan's Task 1 route move; no scope creep — same pattern as the plan's own `tests/test_api.py` update.

## Issues Encountered
None beyond the deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness

Full suite: **422 passed, 12 failed (expected RED), 1 skipped**.

The 12 remaining failures are entirely out of this plan's scope and RED by design:
- `tests/test_batch_api.py` (10 tests) — `POST /batch` / `GET /batch/{id}` don't exist yet; ships in **08-04**.
- `tests/test_web_ui.py::test_app_js_contract` and `::test_severity_thresholds_documented` (2 tests) — `/static/app.js` doesn't exist yet; ships in **08-03**.

All 08-02-scoped `tests/test_web_ui.py` contracts are green: `test_index_has_form`, `test_index_has_file_inputs`, `test_responsive_markers`, `test_security_headers`, `test_docs_still_served`, `test_root_moved_to_api_info`. `tests/test_api.py` (including the new HTML-root test) is fully green. Ready for 08-03 (app.js single-sample behavior) to bind to the ids/containers this plan shipped in `index.html`.

---
*Phase: 08-batch-processing-web-interface*
*Completed: 2026-09-30*

## Self-Check: PASSED

All created/modified files verified present on disk; all 4 task/deviation commit hashes (`a51bd44`, `d973005`, `8c378b5`, `2a426e9`) verified present in `git log`.
