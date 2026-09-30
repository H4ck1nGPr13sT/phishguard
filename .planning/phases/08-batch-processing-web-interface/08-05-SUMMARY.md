---
phase: 08-batch-processing-web-interface
plan: 05
subsystem: ui
tags: [fastapi, jinja2, vanilla-js, csv, polling, xss-safe-dom]

# Dependency graph
requires:
  - phase: 08-batch-processing-web-interface
    provides: "POST /batch + GET /batch/{id}?offset=N endpoints (08-04), app.js safe-render helpers + #batch-area scaffold (08-03)"
provides:
  - "Batch CSV upload UI wired to POST /batch"
  - "Incremental polling loop (GET /batch/{id}?offset=N) with progress bar"
  - "Results table built via createElement, appended via textContent only"
  - "Downloadable static/sample.csv documenting the type,content schema"
affects: [08-batch-processing-web-interface]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Offset-based incremental polling: client tracks rowsRendered and passes it as ?offset=N so each tick only returns new rows"
    - "Overlap-guarded setTimeout polling loop (not setInterval) to avoid concurrent in-flight ticks"
    - "Table skeleton built once via createElement, rows appended incrementally — never re-rendered"

key-files:
  created:
    - src/web/static/sample.csv
  modified:
    - src/web/templates/index.html
    - src/web/static/style.css
    - src/web/static/app.js

key-decisions:
  - "Polling uses setTimeout recursion (not setInterval) with a batchPollInFlight guard, so a slow response never causes overlapping ticks"
  - "#batch-results container is emptied and rebuilt with a fresh table skeleton per batch run; rows within a run are only ever appended, never replaced"
  - "Error rows get a 'n/a' probability cell and a .batch-row-error highlight instead of a severity chip, keeping the per-row error human-visible without a raw-HTML sink"

patterns-established:
  - "Batch polling pattern: POST upload -> capture job_id/total -> build table skeleton -> poll offset -> append -> stop on done/failed"

requirements-completed: [INPUT-05, WEB-07, WEB-02]

# Metrics
duration: 25min
completed: 2026-09-30
---

# Phase 08 Plan 05: Batch CSV Frontend Summary

**CSV batch upload UI with offset-based polling, a live progress bar, and an incrementally-built XSS-safe results table, plus a downloadable sample.csv.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-09-30T00:00:00Z (approx, not recorded precisely)
- **Completed:** 2026-09-30
- **Tasks:** 2
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- `#batch-area` now has a working "Analyze CSV batch" button wired to `POST /batch`, a sample-CSV download link, and a live progress bar (`<progress>` + numeric text)
- `pollBatchJob()` polls `GET /batch/{id}?offset=N` on a ~1s timer, appends only newly-returned rows, advances the offset by the number of rows appended, and stops on `status == "done" | "failed"`, with an overlap guard against concurrent ticks
- Results table is built once via `createElement` inside a `.table-scroll` wrapper; every cell (row, type, content_preview, verdict, probability/severity chip, error) is set via `textContent` only — no `innerHTML`/`insertAdjacentHTML`/`document.write` anywhere in `app.js`
- Shipped `src/web/static/sample.csv` mirroring `tests/fixtures/batch_sample.csv`'s `type,content` schema (url/sms/email rows, including a properly quoted multi-line email cell), linked from the batch help text

## Task Commits

Each task was committed atomically:

1. **Task 1: Batch UI markup + sample.csv + progress/table styling** - `a48eed8` (feat)
2. **Task 2: Batch polling logic in app.js (upload, progress, incremental table)** - `e5956d9` (feat)

**Plan metadata:** (this commit, docs)

## Files Created/Modified
- `src/web/static/sample.csv` - downloadable example CSV (type,content schema)
- `src/web/templates/index.html` - `#batch-btn`, sample-CSV link, `#batch-error`, `#batch-progress` (bar + text), `#batch-results` container (table built dynamically by app.js)
- `src/web/static/style.css` - `.batch-progress`, `#batch-progress-text`, `.batch-row-error` styling within the existing mobile-first / `.table-scroll` system
- `src/web/static/app.js` - `analyzeCsvBatch()`, `pollBatchJob()`, `buildBatchResultsTable()`, `appendBatchRow()`, `updateBatchProgress()`, `renderBatchError()`/`clearBatchError()`, `stopBatchPolling()`, plus the `#batch-btn` click binding

## Decisions Made
- Used `setTimeout` recursion instead of `setInterval` for polling, guarded by an in-flight flag, so a slow `/batch/{id}` response cannot cause overlapping requests (mitigates T-08-20 DoS-via-runaway-polling).
- Replaced the static (08-03) `#batch-results` `<table>` markup with an empty container that `app.js` populates via `createElement`, since the plan requires the skeleton to be built in JS and appended into `.table-scroll` — keeping HTML and JS ownership of the table in one place.
- Error rows render probability as `n/a` (no severity chip, since `probability` is fixed at `0.0` for failed rows server-side) and get a `.batch-row-error` background so failures are visually distinct without relying on color alone (row still carries the literal error text via textContent).

## Deviations from Plan

None - plan executed exactly as written. The only structural choice beyond the plan's literal text was removing the previously-static results `<table>` (added in 08-03 as scaffold) in favor of a JS-built skeleton per the plan's explicit instruction ("Build the results table skeleton ONCE via createElement... appended into #batch-results (clear it first with replaceChildren)") — this is compliance with the plan's own task action, not a deviation.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Batch feature (INPUT-05, WEB-07, WEB-02 CSV path) is now end-to-end from the browser: upload -> job -> polling -> incremental results, all XSS-safe and DoS-guarded per the 08-05 threat model (T-08-18, T-08-19 accepted, T-08-20 mitigated).
- Full suite: 434 passed, 1 skipped (baseline preserved; no regressions).
- This is the last autonomous wave per the plan; live browser polling behavior (visual progress advance, real network timing) is intentionally left for the 08-06 human-verify checkpoint, since it cannot be meaningfully asserted via `TestClient`.

---
*Phase: 08-batch-processing-web-interface*
*Completed: 2026-09-30*
