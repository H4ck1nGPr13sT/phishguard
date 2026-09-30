"""API endpoint tests for POST /predict/image (Phase 7 Plan 04).

Covers:
    - Upload validation ordering: wrong extension, oversized (pre-decode),
      corrupt, and decompression-bomb uploads all reject with HTTP 400.
    - A DETERMINISTIC happy path (HTTP 200) via monkeypatched fake models —
      no 200-OR-503 escape hatch, so this test asserts real behavior even
      in a torch/easyocr-free environment.
    - OCR-responsiveness: the verdict must respond to OCR content (phishing
      text yields a strictly higher probability than blank text) — proves
      BLOCKER 3's OCR->ML bridge is actually wired, not just shaped right.
    - Colon-line body preservation: OCR text whose first line contains a
      colon (e.g. "Password: ...") must still reach the text features via
      the leading b"\\n" prepend, rather than being mis-parsed as an
      RFC-822 header and dropped.

All tests run torch-free: easyocr/torch/cv2 are not required to be
installed for this suite to pass.
"""

import io
import os

import numpy as np
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from src.api.main import app, ml_models

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def _fixture_bytes(name: str) -> bytes:
    with open(os.path.join(FIXTURES_DIR, name), "rb") as fh:
        return fh.read()


@pytest.fixture
def client():
    """FastAPI test client — runs the real lifespan (loads real rule_engine,
    aggregator, email_ensemble, and resolves the OCR backend, which falls
    back to NullOCRBackend in a torch-free environment).
    """
    with TestClient(app) as c:
        yield c


class FakeOCRBackend:
    """Test double for OCRBackend — returns a canned string regardless of
    the image passed to read_text().
    """

    def __init__(self, text: str):
        self._text = text

    def read_text(self, image) -> str:
        return self._text


class FixedProbaEnsemble:
    """Test double for the email_ensemble — predict_proba always returns a
    fixed [[0.1, 0.9]] regardless of input, for a DETERMINISTIC happy-path
    assertion (no dependency on real model weights/behavior).
    """

    def predict_proba(self, X):
        n = len(X)
        return np.array([[0.1, 0.9]] * n)


class TextDrivenFakeEnsemble:
    """Test double for the email_ensemble whose predict_proba is driven by
    the magnitude of the extracted feature vector (real extract_email_
    features output) — richer/longer OCR text with phishing keywords
    produces a larger feature-value sum than blank text, so this proves the
    endpoint's final verdict actually responds to OCR content rather than
    always returning a constant.
    """

    def predict_proba(self, X):
        totals = np.sum(X, axis=1)
        # Saturating monotonic map into (0.01, 0.99) so richer feature
        # vectors -> strictly higher phishing probability, poorer ones ->
        # strictly lower, with no risk of exact ties at either bound.
        probs = 1.0 - 1.0 / (1.0 + totals)
        probs = np.clip(probs, 0.01, 0.99)
        return np.stack([1.0 - probs, probs], axis=1)


def _multipart(filename: str, content: bytes, content_type: str = "image/png"):
    return {"file": (filename, io.BytesIO(content), content_type)}


# ---------------------------------------------------------------------------
# Validation: rejected BEFORE decode (order matters — these must not depend
# on model availability since the checks fire earlier in the handler).
# ---------------------------------------------------------------------------


def test_wrong_extension_rejected(client):
    resp = client.post(
        "/predict/image",
        files=_multipart("notes.txt", b"just some text", content_type="text/plain"),
    )
    assert resp.status_code == 400
    assert "format" in resp.json()["detail"].lower() or "png" in resp.json()["detail"].lower()


def test_oversized_upload_rejected_before_decode(client):
    # >8MB of bytes that are NOT a valid image — if this returns the size
    # message (not "Invalid image"), the size cap fired BEFORE any Pillow
    # decode was attempted.
    oversized_junk = b"\x00" * (8 * 1024 * 1024 + 1)
    resp = client.post("/predict/image", files=_multipart("big.png", oversized_junk))
    assert resp.status_code == 400
    assert "too large" in resp.json()["detail"].lower()


def test_corrupt_image_rejected(client):
    corrupt_bytes = _fixture_bytes("truncated.png")
    resp = client.post("/predict/image", files=_multipart("truncated.png", corrupt_bytes))
    assert resp.status_code == 400
    assert "invalid image" in resp.json()["detail"].lower()


def test_decompression_bomb_rejected(client, monkeypatch):
    # Shrink the pixel-count ceiling so a small, cheaply-generated image
    # counts as a "bomb" without allocating a huge real image (mirrors
    # tests/features/test_image_features.py's bomb test pattern).
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)

    bomb_image = Image.new("RGB", (50, 50), color="white")  # 2500 px > 100
    buffer = io.BytesIO()
    bomb_image.save(buffer, format="PNG")
    bomb_bytes = buffer.getvalue()

    resp = client.post("/predict/image", files=_multipart("bomb.png", bomb_bytes))
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Deterministic happy path (no 200-OR-503 escape hatch).
# ---------------------------------------------------------------------------


def test_happy_path_deterministic(client, monkeypatch):
    monkeypatch.setitem(ml_models, "ocr_backend", FakeOCRBackend("Verify your PayPal account"))
    monkeypatch.setitem(ml_models, "email_ensemble", FixedProbaEnsemble())

    image_bytes = _fixture_bytes("text_login.png")
    resp = client.post("/predict/image", files=_multipart("text_login.png", image_bytes))

    assert resp.status_code == 200
    body = resp.json()
    assert body["content_type"] == "image"
    assert 0.0 <= body["final_probability"] <= 1.0
    assert 0.5 <= body["confidence"] <= 1.0
    assert body["feature_count"] > 0
    assert body["final_prediction"] in ("phishing", "legitimate")


# ---------------------------------------------------------------------------
# OCR-responsiveness (BLOCKER 3): verdict must respond to OCR content.
# ---------------------------------------------------------------------------


def test_ocr_responsiveness_phishing_text_scores_higher_than_blank(client, monkeypatch):
    monkeypatch.setitem(ml_models, "email_ensemble", TextDrivenFakeEnsemble())
    image_bytes = _fixture_bytes("text_login.png")

    monkeypatch.setitem(
        ml_models,
        "ocr_backend",
        FakeOCRBackend("URGENT: verify your account now or it will be suspended immediately"),
    )
    resp_phishing = client.post("/predict/image", files=_multipart("a.png", image_bytes))
    assert resp_phishing.status_code == 200

    monkeypatch.setitem(ml_models, "ocr_backend", FakeOCRBackend(""))
    resp_blank = client.post("/predict/image", files=_multipart("b.png", image_bytes))
    assert resp_blank.status_code == 200

    assert (
        resp_phishing.json()["final_probability"]
        > resp_blank.json()["final_probability"]
    )


# ---------------------------------------------------------------------------
# Colon-line body preservation (checker warning): the leading b"\n" prepend
# must keep colon-containing OCR lines in the email BODY, not drop them as
# mis-parsed RFC-822 headers.
# ---------------------------------------------------------------------------


def test_colon_line_body_preservation(client, monkeypatch):
    monkeypatch.setitem(ml_models, "email_ensemble", TextDrivenFakeEnsemble())
    image_bytes = _fixture_bytes("text_login.png")

    # First line contains a colon, mimicking OCR output from a login form.
    # Without the b"\n" prepend fix, this would be mis-parsed as a header
    # and dropped from the body -> feature vector collapses to the same
    # (near-zero) baseline as blank text.
    monkeypatch.setitem(
        ml_models,
        "ocr_backend",
        FakeOCRBackend("Password: enter now to verify account suspended"),
    )
    resp_colon = client.post("/predict/image", files=_multipart("a.png", image_bytes))
    assert resp_colon.status_code == 200

    monkeypatch.setitem(ml_models, "ocr_backend", FakeOCRBackend(""))
    resp_blank = client.post("/predict/image", files=_multipart("b.png", image_bytes))
    assert resp_blank.status_code == 200

    assert (
        resp_colon.json()["final_probability"]
        > resp_blank.json()["final_probability"]
    )
