"""Web UI contract tests (Phase 8 Plan 01 — Wave 0).

These tests encode the served-HTML, static-asset, XSS-guard, CSP, and
responsive-design contracts for Phase 8 (batch processing & web interface)
BEFORE the implementation lands. They are RED by design until plans
08-02 (index/static mounting + root move) and 08-03 (app.js/style.css)
ship. That is the expected and correct state for this plan — do not
"fix" these tests here; they define the target behavior for later waves.

Module-top imports are limited to `app`, `TestClient`, and stdlib so this
file always collects cleanly even before src/web/ exists.
"""

from fastapi.testclient import TestClient

from src.api.main import app


def test_index_has_form():
    """GET / returns HTML with a textarea, submit control, and a
    content-type selector exposing url/email/sms options. (WEB-01)
    """
    with TestClient(app) as c:
        resp = c.get("/")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/html")
        body = resp.text
        assert "<textarea" in body
        assert 'type="submit"' in body or "<button" in body
        assert "url" in body
        assert "email" in body
        assert "sms" in body


def test_index_has_file_inputs():
    """GET / body contains file inputs accepting .eml, image, and .csv. (WEB-02)"""
    with TestClient(app) as c:
        resp = c.get("/")
        assert resp.status_code == 200
        body = resp.text
        assert ".eml" in body
        assert "image/" in body or ".png" in body
        assert ".csv" in body


def test_app_js_contract():
    """GET /static/app.js defines severityBand and contains no XSS sinks. (WEB-03)"""
    with TestClient(app) as c:
        resp = c.get("/static/app.js")
        assert resp.status_code == 200
        text = resp.text
        assert "severityBand" in text
        assert "innerHTML" not in text
        assert "insertAdjacentHTML" not in text
        assert "document.write" not in text


def test_severity_thresholds_documented():
    """app.js severity thresholds and labels match the 0.25/0.5/0.75 quartile
    bands (Low/Medium/High/Critical). (WEB-03)
    """
    with TestClient(app) as c:
        text = c.get("/static/app.js").text
        assert "0.25" in text
        assert "0.5" in text
        assert "0.75" in text
        for label in ("Low", "Medium", "High", "Critical"):
            assert label in text


def test_responsive_markers():
    """style.css has a media query and a scrollable-table rule; index has
    a viewport meta tag. (WEB-08)
    """
    with TestClient(app) as c:
        css_resp = c.get("/static/style.css")
        assert css_resp.status_code == 200
        css = css_resp.text
        assert "@media" in css
        assert ".table-scroll" in css and "overflow-x" in css

        html = c.get("/").text
        assert 'name="viewport"' in html


def test_security_headers():
    """GET / sets nosniff, DENY framing, and a self-scoped CSP. (T-08-CSP)"""
    with TestClient(app) as c:
        resp = c.get("/")
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert resp.headers.get("x-frame-options") == "DENY"
        csp = resp.headers.get("content-security-policy", "")
        assert "default-src 'self'" in csp


def test_docs_still_served():
    """CSP must not break Swagger UI / OpenAPI schema availability."""
    with TestClient(app) as c:
        assert c.get("/docs").status_code == 200
        assert c.get("/openapi.json").status_code == 200


def test_root_moved_to_api_info():
    """The old JSON root payload now lives at /api/info; GET / is HTML."""
    with TestClient(app) as c:
        info = c.get("/api/info")
        assert info.status_code == 200
        data = info.json()
        assert data["service"] == "PhishGuard API"
        assert "endpoints" in data

        root = c.get("/")
        assert root.headers["content-type"].startswith("text/html")
        assert not root.headers["content-type"].startswith("application/json")
