"""Server-rendered web UI pages for PhishGuard.

Serves the Jinja2 HTML index page at GET / (the JSON API info payload
lives at GET /api/info, see src/api/endpoints.py). Static assets
(CSS/JS) are mounted separately at /static in src/api/main.py.
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Anchored at this module's file so uvicorn works regardless of CWD.
WEB_DIR = Path(__file__).resolve().parent.parent / "web"

templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))

web_router = APIRouter()


@web_router.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request):
    """Serve the responsive single-page HTML UI."""
    return templates.TemplateResponse(request, "index.html", {"max_csv_rows": 500})
