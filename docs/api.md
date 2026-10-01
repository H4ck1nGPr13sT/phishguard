# API Documentation (DOC-03)

PhishGuard's REST API is self-documenting via FastAPI's auto-generated
OpenAPI 3.x schema. Every `/predict*` route and `/explain` carries an
explicit `summary`, `description`, and `response_description` (see
`src/api/endpoints.py`), so the interactive docs below are accurate without
any hand-maintained API reference duplicating the code.

## Interactive documentation

With the API server running (`uvicorn src.api.main:app --reload` or the
project's standard run command):

| Interface | URL | Description |
|-----------|-----|--------------|
| Swagger UI | `/docs` | Interactive — try requests directly from the browser, see request/response schemas and examples |
| ReDoc | `/redoc` | Read-only, single-page reference rendering of the same schema |
| Raw OpenAPI schema | `/openapi.json` | The machine-readable OpenAPI 3.x document FastAPI generates in-process from the route decorators and Pydantic models |

Both `/docs` and `/redoc` are exempted from the app's Content-Security-Policy
(they need inline scripts / CDN assets to render) — see the
`_CSP_EXEMPT_PREFIXES` guard in `src/api/main.py`.

## Route summary

| Method | Path | Tag | Purpose |
|--------|------|-----|---------|
| GET | `/api/info` | root | Service metadata and endpoint list |
| GET | `/health` | health | Service + per-model loaded status |
| POST | `/predict` | prediction | Fast single-model (RF) URL verdict |
| POST | `/predict/ensemble` | prediction | All 7 classifiers + disagreement |
| POST | `/predict/multi-paradigm` | prediction | ML + rules + Bayesian aggregated verdict (thesis core-value endpoint) |
| POST | `/explain` | explainability | SHAP + consolidated explainability report |
| POST | `/predict/email` | prediction | Raw email text verdict |
| POST | `/predict/email/file` | prediction | `.eml` file upload verdict |
| POST | `/predict/sms` | prediction | SMS/chat text verdict |
| POST | `/predict/image` | prediction | Screenshot/photo verdict (OCR + visual) |

See [architecture.md](./architecture.md) for how these routes compose with
the feature-extraction and paradigm layers, and
[data-flow.md](./data-flow.md) for the request lifecycle of the
multi-paradigm endpoint specifically.

## Regenerating `docs/openapi.json`

`docs/openapi.json` is a committed snapshot of the schema, generated
in-process (no running server required) for thesis-appendix inclusion.
Regenerate it after changing any route decorator or response model:

```bash
.venv/bin/python -c "
import json
from src.api.main import app
with open('docs/openapi.json', 'w') as f:
    json.dump(app.openapi(), f, indent=2)
"
```

`app.openapi()` builds the schema dict purely from the route metadata and
Pydantic models already defined in `src/api/endpoints.py` / `src/api/models.py`
— it does not start the server or run the `lifespan` model-loading step.
