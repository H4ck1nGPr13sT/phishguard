---
phase: 08-batch-processing-web-interface
plan: 03
subsystem: ui
tags: [vanilla-js, fetch, formdata, xss-safe-dom, csp, severity-bands]

# Dependency graph
requires:
  - phase: 08-batch-processing-web-interface
    provides: "index.html/style.css scaffold, /static mount, CSP security-headers middleware, #input-type/#input-text/#analyze-btn/#result/#upload-area/#batch-area ids (08-02)"
provides:
  - "app.js: normalize(), severityBand(), postJSON()/postForm(), textContent/createElement-only renderResult()/renderError()"
  - "Single-sample paste flow: url -> /predict/multi-paradigm, email -> /predict/email, sms -> /predict/sms"
  - "Single-sample file-upload flow: .eml -> /predict/email/file, image -> /predict/image via FormData"
  - "Severity band UI (Low/Medium/High/Critical, color + text) and confidence percentage rendering"
affects: [08-04, 08-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "normalize() absorbs MultiParadigmResponse vs EmailSMSResponse shape differences behind one view model"
    - "All DOM writes go through textContent/createElement; never a raw-markup DOM sink (innerHTML/insertAdjacentHTML/document.write) — enforced by tests/test_web_ui.py::test_app_js_contract"
    - "postJSON/postForm throw Error with string-only messages; FastAPI 422 array detail is never rendered directly"

key-files:
  created:
    - src/web/static/app.js
  modified:
    - src/web/templates/index.html
    - src/web/static/style.css

key-decisions:
  - "Renamed the pre-existing #upload-eml/#upload-image/#upload-csv ids (from 08-02 scaffold) to #file-eml/#file-image/#file-csv to match the naming the plan's interfaces/task-2 action specify; #file-csv is present but intentionally unwired (08-05 owns its behavior)"
  - "Combined all of app.js (paste flow + file-upload flow) into a single Write/commit under Task 1, since the file was authored as one coherent module; Task 2's commit carries the HTML/CSS changes plus a note pointing back to the Task 1 commit for the upload JS"

requirements-completed: [WEB-02, WEB-03]

# Metrics
duration: ~25min
completed: 2026-09-30
---

# Phase 08 Plan 03: Single-Sample Analysis Flow Summary

**Vanilla-JS app.js implementing paste (url/email/sms) and file-upload (.eml/image) single-sample analysis against the existing FastAPI endpoints, with client-side Low/Medium/High/Critical severity bands and XSS-safe textContent/createElement-only DOM rendering.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-09-30
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- `normalize(d)` unifies `MultiParadigmResponse` and `EmailSMSResponse` response shapes into one view model (prediction, probability, confidence, explanation, rules, contentType)
- `severityBand(p)` implements the exact 0.25/0.5/0.75 quartile cutoffs with Low/Medium/High/Critical labels, rendered as both a CSS color chip (`.sev-low`/`.sev-medium`/`.sev-high`/`.sev-critical`) and a text label
- `postJSON()`/`postForm()` fetch helpers: JSON header for paste flow, FormData with no manual `Content-Type` for uploads; both throw only string error messages (422 `detail` array never rendered)
- `renderResult()`/`renderError()` build the entire result panel via `document.createElement` + `textContent` — zero raw-markup DOM sinks anywhere in the file
- Paste flow routes url/email/sms to `/predict/multi-paradigm`, `/predict/email`, `/predict/sms` respectively
- File-upload flow: `#file-eml` -> `/predict/email/file`, `#file-image` -> `/predict/image`, each with its own "Analyze" button and client-side extension validation (defense-in-depth; server still validates)
- `index.html` `#upload-area` now has labeled `.eml` and image file inputs with dedicated buttons (no inline handlers — CSP `default-src 'self'` compliant); the pre-existing `#batch-area` CSV input was renamed to `#file-csv` for naming consistency, left unwired for 08-05
- `style.css` gained result-panel styling (verdict, severity chip, confidence line, explanation, fired-rules list, error) and upload-area button layout within the existing mobile-first/44px touch-target system

## Task Commits

1. **Task 1: app.js core — normalize, severityBand, safe rendering, paste-text flow** - `ae0449a` (feat)
2. **Task 2: File-upload inputs (.eml, image) + FormData flow + result styling** - `7baaccc` (feat)

_Note: app.js was authored as a single complete file in Task 1's commit (including the `postForm()`/upload-button bindings that Task 2's action describes), since splitting one JS module across two partial-file commits offered no real atomicity benefit. Task 2's commit contains the HTML/CSS additions the split required._

## Files Created/Modified
- `src/web/static/app.js` - `normalize()`, `severityBand()`, `postJSON()`, `postForm()`, `setText()`, `renderResult()`, `renderError()`, paste-flow (`analyzePastedInput`) and upload-flow (`analyzeEmlFile`, `analyzeImageFile`) handlers, `initSingleSampleFlow()` binding on `DOMContentLoaded`
- `src/web/templates/index.html` - `#upload-area` file inputs renamed/extended: `#file-eml` + `#analyze-eml-btn`, `#file-image` + `#analyze-image-btn`; `#batch-area` CSV input renamed `#upload-csv` -> `#file-csv` (unwired, for 08-05)
- `src/web/static/style.css` - `.result-verdict`, `.result-severity`, `.result-confidence`, `.result-explanation`, `.result-rules`, `.result-rule-matched`, `.result-error`, `#upload-area .field`/`button` layout rules

## Decisions Made
- Combined the paste-flow and file-upload-flow JS into one `app.js` write (Task 1 commit) rather than splitting across two partial edits — the plan's file is a single cohesive module and there was no meaningful intermediate state to preserve separately.
- Renamed 08-02's `#upload-eml`/`#upload-image`/`#upload-csv` ids to `#file-eml`/`#file-image`/`#file-csv` to match this plan's interfaces contract (`Template ids created in 08-02` section lists the analyze/result ids but the plan's Task 2 action explicitly names `#file-eml`/`#file-image`, and instructs adding `#file-csv` for 08-05) — kept all three consistent under one naming scheme.
- Client-side extension validation on uploads is defense-in-depth only; the server endpoints (`predict_email_file`, `predict_image`) remain the authoritative validators (400 on bad extension/size), matching T-08-09's disposition (no file preview, only JSON verdict rendered).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Doc-comment text tripped the app.js XSS-sink contract test**
- **Found during:** Task 1 verification (`test_app_js_contract`)
- **Issue:** The top-of-file CSP/XSS-rule comment and two inline doc comments literally contained the substrings `innerHTML`, `insertAdjacentHTML` (describing what NOT to use), which the contract test greps for across the entire served file text — causing a false-positive failure even though no actual sink call existed in the code.
- **Fix:** Reworded the three comments to describe the forbidden APIs without using their literal names (e.g. "raw-HTML-injection DOM sinks", "the 'set markup from a string' property") so the served asset text contains zero occurrences of the banned substrings while still documenting the constraint for future maintainers.
- **Files modified:** `src/web/static/app.js`
- **Verification:** `grep -n "innerHTML\|insertAdjacentHTML\|document.write" src/web/static/app.js` returns nothing; `test_app_js_contract` passes.
- **Committed in:** `ae0449a` (part of Task 1 commit — comment was fixed before the commit was made)

---

**Total deviations:** 1 auto-fixed (Rule 1 — comment wording only, no logic change)
**Impact on plan:** None on scope; purely a documentation-text fix required to satisfy the plan's own contract test. No scope creep.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `normalize()`, `severityBand()`, `postJSON()`, `postForm()`, and the rendering helpers in `app.js` are available for 08-04 (batch backend) and 08-05 (batch frontend) to reuse/extend.
- `#file-csv` input exists in `#batch-area` but has no event binding — 08-05 must wire its upload + polling logic (per this plan's explicit scope boundary).
- `tests/test_batch_api.py` (10 tests) remain RED as expected — they exercise `/batch` endpoints that ship in 08-04; not in scope for 08-03.
- Full suite: 424 passed, 10 failed (all `test_batch_api.py`, pre-existing RED for 08-04/08-05), 1 skipped.

---
*Phase: 08-batch-processing-web-interface*
*Completed: 2026-09-30*

## Self-Check: PASSED

- FOUND: src/web/static/app.js
- FOUND: src/web/templates/index.html
- FOUND: src/web/static/style.css
- FOUND: .planning/phases/08-batch-processing-web-interface/08-03-SUMMARY.md
- FOUND: ae0449a (Task 1 commit)
- FOUND: 7baaccc (Task 2 commit)
