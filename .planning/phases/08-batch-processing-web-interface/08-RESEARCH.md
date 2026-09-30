# Phase 8: Batch Processing & Web Interface - Research

**Researched:** 2026-09-30
**Domain:** Server-served vanilla-JS web UI on FastAPI + in-memory async CSV batch jobs
**Confidence:** HIGH for stack/patterns (verified in the project .venv), MEDIUM for severity cutoffs (design choice, no authoritative standard)

## Summary

Phase 8 adds a thin presentation layer and one new backend capability. Everything the UI needs already exists: `/predict`, `/predict/multi-paradigm`, `/predict/email`, `/predict/email/file`, `/predict/sms`, `/predict/image`. The only genuinely new backend work is the CSV batch job (POST upload -> job id, GET status polling). No new heavy packages are required: Jinja2 3.1.6, python-multipart 0.0.22, FastAPI 0.129.0, Starlette 0.52.1 are all already installed in `.venv`. [VERIFIED: importlib.metadata in .venv] Only `jinja2` is missing from `requirements.txt` and must be added (reproducibility for a thesis reviewer).

Real async batch is achievable with FastAPI `BackgroundTasks` plus an in-memory job dict. Verified locally: under `TestClient`, background tasks run to completion before the POST call returns, so tests can assert on final job state immediately without sleeping. [VERIFIED: local experiment] In a real uvicorn run the task executes after the response is sent, so the frontend genuinely sees `running` -> `done` via polling. Caveat: state lives in process memory, so it is valid for a single uvicorn worker only and is lost on restart; acceptable for the academic demo and must be stated in the thesis.

Two response-contract quirks the UI must absorb: (1) `/predict` returns `phishing_probability`/`prediction`, while multi-paradigm and email/sms/image return `final_probability`/`final_prediction`; (2) only URL has a multi-paradigm endpoint; email/sms/image return `paradigm_contributions` optionally (image populates it, email/sms return `null`). The UI should use `/predict/multi-paradigm` for URLs and normalise all responses in one JS function.

**Primary recommendation:** Add one new router module (`src/api/web.py` for pages, `src/api/batch.py` for batch), mount `StaticFiles` at `/static`, use `Jinja2Templates` for a single `index.html`, and normalise every API response in one vanilla-JS `normalize()` function; render all user-derived content with `textContent` only.

## User Constraints

No CONTEXT.md exists for this phase. Locked decisions come from the orchestrator and upstream docs.

### Locked Decisions
1. Frontend served directly by the existing FastAPI app: Jinja2 templates + static CSS + vanilla JS `fetch()`. No React/Vue/Svelte, no Node build, no bundler. Single `uvicorn src.api.main:app`.
2. Severity bands derived in the frontend from `final_probability`: Low/Medium/High/Critical (suggested <0.25, <0.5, <0.75, >=0.75).
3. CSV batch is real async: POST CSV -> background job -> job id; GET status endpoint polled by the UI for progress bar + incremental results table. In-memory job store acceptable (single worker caveat noted).
4. No auth (open demo).
5. Security: size cap, row cap, safe CSV parsing, no CSV/formula injection, HTML-escape all rendered content; user text always via `textContent`, never `innerHTML`.
6. Root `./CLAUDE.md` content is unrelated and ignored; authoritative spec is PROJECT/ROADMAP/REQUIREMENTS.

### Claude's Discretion
CSS approach, exact thresholds (recommended below), CSV schema details, limits, polling interval, job-registry design, test strategy.

### Deferred Ideas (OUT OF SCOPE)
Dashboards/charts/model comparison and SHAP/LIME (Phase 9, WEB-04/05/06), auth, Celery/Redis queues, image batch via CSV, Docker.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INPUT-05 | CSV upload for batch analysis | `POST /batch` (multipart) with schema `type,content`; size/row caps; per-row dispatch to existing extractors |
| WEB-01 | Form to paste text/URL | `index.html` form: type selector (url/email/sms) + textarea + submit; JS picks endpoint |
| WEB-02 | File upload (eml, images, CSV) | Three upload inputs posting `FormData` to `/predict/email/file`, `/predict/image`, `/batch` |
| WEB-03 | Result with confidence level | `severityBand(final_probability)` in JS; verdict + band + explanation + fired rules |
| WEB-07 | Batch processing of many samples | BackgroundTasks job + polling endpoint + incremental results table |
| WEB-08 | Responsive / mobile | Viewport meta, mobile-first CSS with fluid grid, `@media (min-width: 640px)`, table horizontal scroll wrapper |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| HTML page delivery | Frontend Server (FastAPI+Jinja2) | - | Single-service locked decision |
| Static CSS/JS delivery | CDN/Static (Starlette StaticFiles) | - | Mounted `/static`, no build |
| Form handling, result rendering, severity band | Browser | - | Band is derived client-side per locked decision |
| Response normalisation across endpoints | Browser | - | One JS function hides field-name differences |
| Inference per input type | API/Backend | - | Existing endpoints unchanged |
| CSV parsing, validation, caps | API/Backend | - | Untrusted input validated server-side |
| Job registry + background execution | API/Backend | - | In-process dict + BackgroundTasks |
| Progress polling | Browser (timer) | API/Backend (status GET) | Stateless GET returns job snapshot |
| Output escaping | Browser (textContent) | API (CSV export guarded) | Defence in depth |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.129.0 installed; req `>=0.109.0` | App, routes, BackgroundTasks, UploadFile | Already the project backbone [VERIFIED: .venv] |
| starlette | 0.52.1 (transitive) | `StaticFiles`, `Jinja2Templates` | Bundled with FastAPI; `StaticFiles` uses anyio, so no `aiofiles` needed [VERIFIED: source inspection] |
| jinja2 | 3.1.6 installed, NOT in requirements.txt | Templates | Required by `Jinja2Templates`; latest on PyPI is 3.1.6 [VERIFIED: pip index, slopcheck OK] |
| python-multipart | 0.0.22 installed; req `>=0.9.0` | Multipart upload parsing | Already used by eml/image endpoints [VERIFIED: .venv] |
| Python stdlib `csv`, `io`, `uuid`, `threading` | - | CSV parsing, job ids, lock | No dependency; `csv` over pandas to keep parsing strict and bounded |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | 0.28.1 | Backs `TestClient` | Tests [VERIFIED: .venv] |
| pytest | 9.0.2 | Tests | Existing suite |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| BackgroundTasks | `asyncio.create_task` / ThreadPoolExecutor | BackgroundTasks runs sync `def` tasks in threadpool automatically and is test-friendly; executor adds complexity with no gain |
| Hand-written CSS | Pico.css / Bootstrap via CDN | CDN breaks offline reproducibility; if a framework is wanted, vendor the single file into `static/`. Recommendation: ~150 lines of own mobile-first CSS |
| Polling | SSE/WebSocket | Polling is simpler, stateless, testable with TestClient |
| stdlib csv | pandas.read_csv | pandas infers types and loads everything; stdlib streams with hard caps |

**Installation:** add one line to `requirements.txt`:
```
jinja2>=3.1.0   # Phase 8 - server-rendered templates (Jinja2Templates)
```
Pin decision: `jinja2>=3.1.0` (lower bound only, consistent with the file's style; scikit-learn is the only exact pin and only because of pickled artifacts). No other requirement changes needed. `python-multipart>=0.0.9` and `fastapi>=0.109.0` remain adequate; the TemplateResponse form used below (`request` first argument) needs Starlette >= 0.29, satisfied by FastAPI >= 0.109 (Starlette 0.35+). [ASSUMED: minimum Starlette per FastAPI 0.109 pin; installed version verified]

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| jinja2 | PyPI | >10 yrs | very high | github.com/pallets/jinja | [OK] | Approved (already installed, add to requirements) |

**Packages removed ([SLOP]):** none. **Flagged ([SUS]):** none. No other new packages are introduced in this phase.

## Architecture Patterns

### System Architecture Diagram

```
Browser (index.html + app.js + style.css)
  |
  |-- GET /            --> web router --> Jinja2 index.html (text/html)
  |-- GET /static/*    --> StaticFiles (css, js)
  |
  |-- Single analysis
  |     form(url)     --> POST /predict/multi-paradigm (JSON)
  |     form(email)   --> POST /predict/email (JSON)
  |     form(sms)     --> POST /predict/sms (JSON)
  |     file(.eml)    --> POST /predict/email/file (multipart)
  |     file(image)   --> POST /predict/image (multipart)
  |          \--> normalize() --> severityBand() --> render via textContent
  |
  |-- Batch
        file(.csv) --> POST /batch (multipart)
                         |- validate: ext, size cap, header, row cap
                         |- create job {id,status=queued,total,done,rows[]}
                         |- BackgroundTasks.add_task(run_batch, job_id, rows)
                         \- return 202/200 {job_id, total}
        timer 1s   --> GET /batch/{job_id}?offset=N
                         \- {status, total, done, rows[offset:], error?}
        run_batch: for each row -> dispatch(type, content) -> append result row
                   (uses same ml_models + extractors as the endpoints)
```

### Recommended Project Structure
```
src/api/
  main.py            # + app.mount("/static", ...), include web + batch routers
  web.py             # GET / (HTMLResponse via Jinja2Templates)
  batch.py           # POST /batch, GET /batch/{id}, job registry, run_batch
  inference.py       # (recommended) shared per-type predict helpers extracted from endpoints
src/web/
  templates/index.html
  static/style.css
  static/app.js
tests/
  test_web_ui.py
  test_batch_api.py
```
Use an absolute path anchored at the module file (`Path(__file__).resolve().parent.parent / "web" / "static"`) so `uvicorn` works from any CWD. Note `main.py` uses CWD-relative `models/` paths already; the UI directories should not inherit that fragility. Pitfall: `StaticFiles` with a nonexistent directory raises at import time.

### Pattern 1: Mount static + templates + index route
```python
# Source: Starlette/FastAPI docs (https://fastapi.tiangolo.com/advanced/templates/, /tutorial/static-files/)
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))
web_router = APIRouter()

@web_router.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"max_csv_rows": 500})

# in main.py:
# app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
# app.include_router(web_router)
```
**Route conflict (critical):** `endpoints.py` already defines `GET /` returning JSON API info. The HTML index must take that path for WEB-01, so either (a) include `web_router` BEFORE the existing router (first registered route wins), or (b) remove/move the JSON root to `/api`. Recommended: move the JSON info to `GET /api/info` and update any test asserting on `GET /` (check `tests/test_api.py` root test before editing), or keep JSON via content negotiation. The planner must make this an explicit task with a test update.

### Pattern 2: Vanilla JS calling endpoints with safe rendering
```javascript
// Normalise the two response shapes into one view model.
function normalize(d) {
  const p = d.final_probability ?? d.phishing_probability ?? d.ensemble_probability;
  return {
    prediction: d.final_prediction ?? d.prediction ?? d.ensemble_prediction,
    probability: p,
    confidence: d.confidence ?? d.ensemble_confidence,
    explanation: d.explanation ?? "",
    rules: d.active_rules ?? [],
    contentType: d.content_type ?? "url",
  };
}
function severityBand(p) {            // Low/Medium/High/Critical
  return p < 0.25 ? "Low" : p < 0.5 ? "Medium" : p < 0.75 ? "High" : "Critical";
}
async function postJSON(url, body) {
  const r = await fetch(url, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Request failed (" + r.status + ")");
  return data;
}
// ALWAYS textContent; never innerHTML with server/user data.
function setText(el, s) { el.textContent = String(s); }
```
Note FastAPI 422 responses return `detail` as an array of objects; the `typeof` check above prevents rendering `[object Object]`. For multipart uploads do NOT set the `Content-Type` header manually (the browser must add the boundary).

### Pattern 3: Batch job with BackgroundTasks + polling
```python
# Source: https://fastapi.tiangolo.com/tutorial/background-tasks/ ; behaviour verified locally
import csv, io, threading, uuid
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

MAX_CSV_BYTES = 1 * 1024 * 1024
MAX_CSV_ROWS = 500
MAX_CELL_CHARS = 5000                      # matches SMSRequest max_length
ALLOWED_TYPES = {"url", "email", "sms"}
JOBS: dict[str, dict] = {}                 # single-worker demo store
_LOCK = threading.Lock()
MAX_JOBS = 50                              # evict oldest to bound memory

@router.post("/batch")
async def start_batch(background: BackgroundTasks, file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(400, "File must be .csv")
    raw = await file.read(MAX_CSV_BYTES + 1)
    if len(raw) > MAX_CSV_BYTES:
        raise HTTPException(400, "File too large (max 1MB)")
    try:
        text = raw.decode("utf-8-sig")     # tolerate Excel BOM
    except UnicodeDecodeError:
        raise HTTPException(400, "CSV must be UTF-8")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or {"type", "content"} - {h.strip().lower() for h in reader.fieldnames}:
        raise HTTPException(400, "CSV header must contain: type,content")
    rows = []
    for i, row in enumerate(reader, start=1):
        if i > MAX_CSV_ROWS:
            raise HTTPException(400, f"Too many rows (max {MAX_CSV_ROWS})")
        rows.append(row)
    job_id = uuid.uuid4().hex
    with _LOCK:
        JOBS[job_id] = {"status": "queued", "total": len(rows), "done": 0, "rows": []}
    background.add_task(run_batch, job_id, rows)   # sync def -> threadpool
    return {"job_id": job_id, "total": len(rows)}

@router.get("/batch/{job_id}")
def batch_status(job_id: str, offset: int = 0):
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(404, "Unknown job")
    with _LOCK:
        return {"status": job["status"], "total": job["total"], "done": job["done"],
                "rows": job["rows"][max(offset, 0):]}
```
`run_batch` iterates rows, per row: validate `type` in allowlist and content length, call the shared per-type inference helper inside `try/except`, append `{row, type, content_preview, prediction, probability, error}`, increment `done`, finally set `status="done"` (or `"failed"` with a generic error on unexpected exceptions). One bad row must not abort the job.

Design notes:
- **Schema:** header `type,content` (case-insensitive, extra columns ignored); `type` in {url,email,sms}; `content` is URL / raw email text (must contain header-like lines, matching `EmailTextRequest`) / SMS text. Per-row validation should reuse the same rules as the Pydantic request models (instantiate `URLRequest`, `EmailTextRequest`, `SMSRequest` and catch `ValidationError` -> row error) so behaviour is identical to the single endpoints.
- **Per-row dispatch:** do not call `predict_batch` in `src/models/predict.py` (assumes one homogeneous feature schema). Extract the prediction bodies of the existing endpoints into plain functions (e.g. `predict_url_multi(url)`, `predict_email_text(raw)`, `predict_sms_text(msg)`) in `inference.py` and have both endpoints and `run_batch` call them. Minimal-risk alternative: call the endpoint functions directly with constructed request models (they are plain sync functions; `HTTPException` must be caught per row).
- **Models dict:** `run_batch` reads `ml_models` from `src.api.main`; same import pattern as `endpoints.py`.
- **Incremental table:** `offset` parameter lets the client fetch only new rows; progress = `done/total`.
- **Image rows in CSV:** out of scope (deferred); `type=image` is rejected as an invalid type.

### Anti-Patterns to Avoid
- **`innerHTML` with server/user data:** XSS via pasted URL, CSV cell, OCR text, rule `matched_values`, explanation. Use `textContent` / `createElement`.
- **Manually setting `Content-Type` on `FormData` fetch:** breaks the multipart boundary.
- **Holding the job lock during inference:** only lock for state mutation.
- **`async def` batch runner calling CPU-bound models:** blocks the event loop; use sync `def` for `run_batch`.
- **Multiple uvicorn workers (`--workers N`):** job lookups would 404 across processes; document single-worker.
- **Unbounded job store:** evict oldest beyond `MAX_JOBS`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV parsing | Manual `split(",")` | stdlib `csv.DictReader` | Quoted fields, embedded commas/newlines |
| Job ids | Counters / timestamps | `uuid.uuid4().hex` | Unguessable ids, no collisions |
| HTML templating | String concatenation | `Jinja2Templates` (autoescape on for `.html`) | Escaping by default |
| Static serving | Custom file route | `StaticFiles` | Path traversal safe, caching headers |
| Request validation per row | New validators | Existing Pydantic request models | Identical rules to single endpoints |
| Async queue | Celery/Redis | `BackgroundTasks` + dict | Out of scope for demo scale |
| Severity logic server-side | New API field | Pure JS function (locked) | Keeps API contract unchanged |

**Key insight:** this phase should add almost no new logic; its value is correct wiring, consistent normalisation, and safe rendering.

## Severity Bands (WEB-03)

Recommended (adopting the orchestrator's suggestion): `p < 0.25 Low`, `p < 0.5 Medium`, `p < 0.75 High`, `p >= 0.75 Critical`, applied to `final_probability` (for `/predict` fallbacks, `phishing_probability`). [ASSUMED: equal-width quartiles are a presentation convention, not derived from a published standard or from calibration on this project's data.] Consistency check against the code: the verdict flips at 0.5 (`> 0.5` => phishing), so Low/Medium both correspond to a "legitimate" verdict and High/Critical to "phishing"; this aligns the colour/label with the verdict. The `confidence` field (0.5 + distance from 0.5) is a different quantity (certainty of the verdict, not threat level) and should be shown as a percentage next to the band rather than used for the band. Thesis note: the model is trained on small, partly synthetic datasets (Phases 3/6), so probabilities are not calibrated; the band labels are a UI convenience, not a calibrated risk score. The planner should surface this in the UI footer text and the confirmation goes to Assumptions Log A1.

## Responsive Design (WEB-08)

- `<meta name="viewport" content="width=device-width, initial-scale=1">` (mandatory, otherwise mobile browsers render at desktop width).
- Mobile-first CSS: single column by default; `@media (min-width: 640px)` for a two-column form/result layout; `max-width: 960px` centred container; `rem`-based type; inputs/buttons `min-height: 44px` (touch target).
- Wrap the results table in `<div class="table-scroll" style="overflow-x:auto">`.
- Severity band as colour AND text (accessibility; not colour only).
- `prefers-color-scheme` optional; not required.
- Verification: no real-device test in CI; assert viewport meta + `@media` presence in served assets via TestClient, plus a documented manual check in browser devtools device mode at 375px.

## Common Pitfalls

### Pitfall 1: `GET /` collision
**What goes wrong:** Existing JSON root route shadows or is shadowed by the HTML index; existing test may assert JSON.
**How to avoid:** Explicit task: move JSON info, update test, add test that `/` returns `text/html`.
**Warning signs:** Browser shows JSON.

### Pitfall 2: Lifespan models not loaded in tests
**What goes wrong:** `TestClient(app)` without the context manager does not run lifespan, so `ml_models` may be empty (503s).
**How to avoid:** Follow `tests/test_api_image.py`: `with TestClient(app) as c:` for real models, or inject mocks into `ml_models` as `tests/test_api.py` does. Page-serving tests need no models.

### Pitfall 3: Background task timing in tests vs production
**What goes wrong:** Under `TestClient` the job is already finished when POST returns, hiding progress states.
**How to avoid:** Test final state and row contents via polling; test "running" behaviour by unit-testing `run_batch` with a stubbed slow per-row function, or by directly inserting a job in `JOBS` with partial `rows`/`done` and asserting `GET` returns the offset slice. [VERIFIED: local experiment for completion-before-return]

### Pitfall 4: Email rows need header-like lines
**What goes wrong:** `EmailTextRequest` rejects content without `From:/Subject:/To:/Date:`; in CSV, newlines inside quoted cells are legal but users may flatten them.
**How to avoid:** Reuse the model validator and report the row error text; document in the UI with a sample CSV and provide a downloadable `sample.csv` in `static/`.

### Pitfall 5: CSV/formula injection on export
**What goes wrong:** Cells starting with `=`, `+`, `-`, `@`, tab, CR could execute in Excel if the UI offers "Download results CSV".
**How to avoid:** Display-only needs no mitigation beyond `textContent`. If export is added, prefix such cells with `'` (OWASP CSV Injection guidance). [CITED: owasp.org/www-community/attacks/CSV_Injection] Recommend skipping export in this phase, or including the prefix with a test.

### Pitfall 6: Job store growth and thread safety
**How to avoid:** `MAX_JOBS` eviction, lock around mutations, return copies/slices.

### Pitfall 7: Loading `app.js` with relative paths
**How to avoid:** Use absolute `/static/app.js` and `fetch("/batch")` (leading slash) so behaviour does not depend on the page URL.

### Pitfall 8: OMP segfault on macOS
**What goes wrong:** Phase 7 found torch + XGBoost crash; `conftest.py` sets `KMP_DUPLICATE_LIB_OK`. Real (non-pytest) `uvicorn` runs on a machine with easyocr installed may hit it. **How to avoid:** note the env var in the README run instructions (existing guard is pytest-only). [VERIFIED: conftest.py]

## Code Examples

### Testing served HTML and static assets
```python
# Source: Starlette TestClient (httpx-based); pattern from tests/test_api_image.py
from fastapi.testclient import TestClient
from src.api.main import app

def test_index_html():
    with TestClient(app) as c:
        r = c.get("/")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/html")
        assert 'name="viewport"' in r.text

def test_static_assets():
    with TestClient(app) as c:
        assert c.get("/static/style.css").status_code == 200
        js = c.get("/static/app.js")
        assert js.status_code == 200 and "innerHTML" not in js.text   # XSS guard
```

### Testing batch upload + polling
```python
def test_batch_happy_path():
    csv_bytes = b"type,content\nurl,https://example.com/login\nsms,URGENT verify your account now\n"
    with TestClient(app) as c:
        r = c.post("/batch", files={"file": ("b.csv", csv_bytes, "text/csv")})
        assert r.status_code == 200
        job_id = r.json()["job_id"]
        s = c.get(f"/batch/{job_id}").json()     # task already finished under TestClient
        assert s["status"] == "done" and s["done"] == s["total"] == 2

def test_batch_rejects_bad_input():
    with TestClient(app) as c:
        assert c.post("/batch", files={"file": ("x.txt", b"a", "text/plain")}).status_code == 400
        assert c.post("/batch", files={"file": ("x.csv", b"a,b\n1,2\n", "text/csv")}).status_code == 400
        big = b"type,content\n" + b"sms,hi\n" * 501
        assert c.post("/batch", files={"file": ("x.csv", big, "text/csv")}).status_code == 400
        assert c.get("/batch/nonexistent").status_code == 404
```
Tests that need fast deterministic results should monkeypatch the per-row inference helper (as `test_api_image.py` does with fake models) so they do not depend on trained artifacts.

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `templates.TemplateResponse("x.html", {"request": request})` | `TemplateResponse(request, "x.html", ctx)` | Old form deprecated in Starlette; use new signature [CITED: fastapi.tiangolo.com/advanced/templates] |
| `aiofiles` required for StaticFiles | anyio-based, no extra dep | Nothing to install [VERIFIED: starlette source in .venv] |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Quartile cutoffs 0.25/0.5/0.75 are acceptable severity bands | Severity Bands | Labels may look arbitrary to reviewer; easy to change (single JS function) |
| A2 | Starlette >= 0.29 needed for request-first `TemplateResponse`; satisfied by FastAPI >= 0.109 pin | Standard Stack | Old env would fail; mitigated by installed 0.52.1 |
| A3 | Limits (1MB, 500 rows, 5000 chars/cell, 50 jobs, 1s polling) are sensible demo defaults | Pattern 3 | Tunable constants; user may prefer other values |
| A4 | Moving JSON root to `/api/info` is acceptable (vs. keeping JSON at `/`) | Pattern 1 | Existing consumers/tests of `GET /` need updating |

## Open Questions

1. **Where should the JSON root go?** Recommendation: `/api/info`; update the one existing root test.
2. **Refactor endpoints into shared helpers vs. call endpoint functions?** Recommendation: extract helpers (cleaner, testable); fallback is direct calls with request models.
3. **Should the UI call `/predict/ensemble` too?** No; Phase 9 covers model comparison (WEB-05 is mapped to Phase 3/9).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python venv | everything | yes | 3.13.13 | - |
| fastapi / starlette | app | yes | 0.129.0 / 0.52.1 | - |
| jinja2 | templates | yes (unpinned in requirements) | 3.1.6 | add to requirements.txt |
| python-multipart | uploads | yes | 0.0.22 | - |
| httpx | TestClient | yes | 0.28.1 | - |
| Node/npm | - | not needed | - | none (locked: no build step) |
| Trained models (`models/`) | real-model tests | present in repo | - | monkeypatch helpers |

No blocking missing dependencies.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 with FastAPI `TestClient` (httpx 0.28.1) |
| Config file | none (`conftest.py` at repo root sets OpenMP env, registers `slow` marker) |
| Quick run command | `.venv/bin/python -m pytest tests/test_web_ui.py tests/test_batch_api.py -x` |
| Full suite command | `.venv/bin/python -m pytest` (~60s) |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WEB-01 | `GET /` returns HTML containing paste form (textarea, submit, type select) | API | `pytest tests/test_web_ui.py::test_index_has_form -x` | Wave 0 |
| WEB-02 | Page contains file inputs accepting `.eml`, `.png/.jpg`, `.csv`; upload endpoints reachable | API | `pytest tests/test_web_ui.py::test_index_has_file_inputs -x` | Wave 0 |
| WEB-03 | `app.js` defines `severityBand` with 4 labels; XSS guard (no `innerHTML`) | static check | `pytest tests/test_web_ui.py::test_app_js_contract -x` | Wave 0 |
| WEB-03 | Band thresholds correct (boundary values) | unit (pure Python mirror or Node-free regex check) | `pytest tests/test_web_ui.py::test_severity_thresholds_documented -x` | Wave 0 |
| INPUT-05 | `POST /batch` valid CSV -> job id; bad ext/header/size/rows -> 400 | API | `pytest tests/test_batch_api.py -x` | Wave 0 |
| WEB-07 | `GET /batch/{id}` returns status/total/done/rows; offset slice; 404 unknown; per-row error isolation; completes | API/unit | `pytest tests/test_batch_api.py::test_polling -x` | Wave 0 |
| WEB-08 | Viewport meta present; CSS contains `@media` and table scroll wrapper | static | `pytest tests/test_web_ui.py::test_responsive_markers -x` | Wave 0 |
| Regression | Existing endpoints unchanged (root JSON moved) | API | `pytest tests/test_api.py -x` | exists (update root test) |

Severity logic lives in JS, which cannot be executed without a JS runtime. Options for the planner: keep thresholds defined in a single documented constant and assert its presence via regex in tests, AND do one human-verify checkpoint in a browser (desktop and 375px mobile) for rendering/polling behaviour. Do not add Node/Jest (violates no-Node decision).

### Sampling Rate
- **Per task commit:** quick run command above
- **Per wave merge:** full suite
- **Phase gate:** full suite green plus human browser check before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_web_ui.py` - WEB-01/02/03/08
- [ ] `tests/test_batch_api.py` - INPUT-05, WEB-07
- [ ] Sample CSV fixture (`tests/fixtures/batch_sample.csv`, also shipped as `static/sample.csv`)
- [ ] Update existing root-endpoint assertion in `tests/test_api.py` if `/` moves
- [ ] No framework install needed

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (locked: open demo) | - |
| V3 Session Management | no (no sessions/cookies) | - |
| V4 Access Control | partial | Job ids are unguessable uuid4; no listing endpoint; accepted risk for open demo |
| V5 Input Validation | yes | Extension allowlist, size cap, UTF-8 decode, row cap, cell length cap, `type` allowlist, reuse Pydantic models per row |
| V6 Cryptography | no (use `uuid4`, i.e. `os.urandom`-backed, for ids; no custom crypto) | - |
| V12 Files/Resources | yes | CSV processed in memory only, never written to disk; bounded read (`read(MAX+1)`) |
| V13/V14 API & Config | yes | Generic error messages for unexpected failures; `StaticFiles` mount limited to `static/` |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Stored/reflected XSS via URL/email/SMS text, CSV cells, OCR text, rule `matched_values`, explanation | Tampering / Info disclosure | `textContent`/`createElement` only; Jinja autoescape; test that `app.js` has no `innerHTML`/`insertAdjacentHTML`/`document.write`; add `Content-Security-Policy: default-src 'self'` header via small middleware or per-response (no inline scripts, so feasible) |
| CSV/formula injection | Tampering | Display via `textContent`; if export added, prefix `=+-@\t\r` cells with `'` |
| Oversized/zip-bomb-like CSV, huge cells | DoS | 1MB read cap, 500-row cap, 5000-char cell cap, `csv.field_size_limit` set explicitly |
| Job flooding / memory exhaustion | DoS | `MAX_JOBS` eviction; per-job row cap; accepted: no rate limiting (open demo) |
| CPU exhaustion via long batch | DoS | Row cap; sync threadpool execution; document single-worker limitation |
| Job-id enumeration | Info disclosure | uuid4 (122 bits); no list endpoint |
| Path traversal via static mount | Tampering | Starlette `StaticFiles` normalises paths; serve only `static/` |
| Error detail leakage | Info disclosure | Existing endpoints embed `str(e)` in 500 detail; in batch rows, store a short generic message plus exception class name, not stack traces |
| Clickjacking / MIME sniffing | Tampering | `X-Frame-Options: DENY` and `X-Content-Type-Options: nosniff` via middleware (optional hardening, cheap) |
| Malicious content in uploaded image/eml | Tampering | Already handled by Phase 6/7 validation; UI must not preview uploaded files via `innerHTML` (if a thumbnail is shown use `URL.createObjectURL` on an `<img>`, revoke after load) |

## Sources

### Primary (HIGH confidence)
- Project files read: `src/api/main.py`, `endpoints.py`, `models.py`, `requirements.txt`, `conftest.py`, `tests/test_api_image.py`, `tests/test_api.py`, Phase 7 RESEARCH/VALIDATION (format reference).
- Local verification in `.venv`: installed versions (jinja2 3.1.6, python-multipart 0.0.22, fastapi 0.129.0, starlette 0.52.1, httpx 0.28.1); StaticFiles does not use aiofiles; TestClient runs BackgroundTasks to completion before returning.
- `pip index versions jinja2` (3.1.6 latest) and slopcheck 0.6.1 (`[OK]`).

### Secondary (MEDIUM confidence)
- FastAPI docs (templates, static files, background tasks) and OWASP CSV Injection page, cited from knowledge of the official docs; not re-fetched in this session [CITED, unfetched].

### Tertiary (LOW confidence)
- Severity cutoffs: design convention only (A1).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all packages verified installed; one requirements line to add.
- Architecture: HIGH - patterns are standard FastAPI and locally exercised (BackgroundTasks).
- Pitfalls: HIGH for route collision/TestClient behaviour (verified in code), MEDIUM for others.
- Severity bands: MEDIUM - assumption pending confirmation.

**Research date:** 2026-09-30
**Valid until:** 30 days (stable stack)

## RESEARCH COMPLETE
