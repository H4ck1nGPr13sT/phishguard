"""Web UI contract tests (Phase 8 Plan 01 — Wave 0; extended Phase 9 Plan 01).

These tests encode the served-HTML, static-asset, XSS-guard, CSP, and
responsive-design contracts for Phase 8 (batch processing & web interface)
BEFORE the implementation lands. They are RED by design until plans
08-02 (index/static mounting + root move) and 08-03 (app.js/style.css)
ship. That is the expected and correct state for this plan — do not
"fix" these tests here; they define the target behavior for later waves.

Phase 9 Plan 01 adds the Explain-dashboard markup/JS-contract tests at the
bottom of this file — also RED by design until 09-03 ships the dashboard.

Module-top imports are limited to `app`, `TestClient`, `re`, and stdlib so
this file always collects cleanly even before src/web/ or the dashboard
exists.
"""

import re

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


# ---------------------------------------------------------------------------
# Phase 9 Plan 01 (Wave 0) — Explain dashboard contract, RED by design until
# 09-03 ships src/web/templates/index.html's dashboard section and the new
# app.js chart renderers.
# ---------------------------------------------------------------------------


def test_index_has_explain_dashboard():
    """GET / body contains an Explain trigger and dashboard containers.
    (WEB-04, WEB-06)
    """
    with TestClient(app) as c:
        resp = c.get("/")
        assert resp.status_code == 200
        body = resp.text
        assert 'id="explain-btn"' in body
        assert 'id="dashboard"' in body
        assert 'id="classifier-chart"' in body
        assert 'id="shap-chart"' in body


def test_app_js_defines_chart_renderers():
    """GET /static/app.js defines the new chart-render functions and uses
    the SVG DOM API (no CDN charting library). (WEB-04)
    """
    with TestClient(app) as c:
        text = c.get("/static/app.js").text
        assert "renderDashboard" in text
        assert "renderClassifierChart" in text
        assert "renderShapChart" in text
        assert "createElementNS" in text


def test_app_js_contract_dashboard():
    """app.js served text still has NO innerHTML/insertAdjacentHTML/
    document.write sinks after the Phase 9 dashboard chart code lands.
    (WEB-04, XSS contract)
    """
    with TestClient(app) as c:
        text = c.get("/static/app.js").text
        assert "innerHTML" not in text
        assert "insertAdjacentHTML" not in text
        assert "document.write" not in text


def test_index_no_external_scripts():
    """GET / body — every <script src="..."> tag must point at /static/,
    never an external/CDN or protocol-relative source. (WEB-04, no-CDN CSP)

    A bare 'script src="http' substring check would miss protocol-relative
    `//cdn...` sources; a naive '//' check would false-positive on the
    legitimate `/static/app.js`. Regex-extract every script src and assert
    each one starts with "/static/".
    """
    with TestClient(app) as c:
        body = c.get("/").text
        srcs = re.findall(r'<script[^>]*\bsrc="([^"]*)"', body)
        assert len(srcs) > 0
        for src in srcs:
            assert src.startswith("/static/"), f"Non-local script source: {src}"
