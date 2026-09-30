"""Integration tests for Phase 7: OCR & Visual Analysis (real EasyOCR backend).

Requirements coverage:
- INPUT-04: System accepts image uploads (PNG/JPG) via POST /predict/image
- INPUT-06: System extracts text from images via OCR (real EasyOCR backend)

These tests exercise the REAL EasyOCR backend end-to-end. They are guarded by
``pytest.importorskip`` so the whole module is collected-but-skipped (never
errored) in environments where the heavy Phase 7 dependencies are absent — this
keeps the fast unit suite torch-free per 07-VALIDATION.md.

NETWORK PREREQUISITE: the first construction of an ``easyocr.Reader`` downloads
~64MB of recognition/detection weights to ``~/.EasyOCR/model``. Running these
tests therefore needs network access once (RESEARCH.md Pitfall 3). After the
first download the weights are cached locally.
"""

import io

import pytest

# Skip the entire module unless the heavy deps are importable. Collected-but-
# skipped (not errored) when absent — see 07-VALIDATION.md sampling design.
pytest.importorskip("easyocr")
pytest.importorskip("imagehash")
pytest.importorskip("cv2")

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from src.api.main import app  # noqa: E402
from src.features.ocr.backend import EasyOCRBackend  # noqa: E402
from tests.fixtures.make_fixtures import generate_all  # noqa: E402


@pytest.fixture(scope="module")
def fixtures_dir(tmp_path_factory):
    """Generate the deterministic fixture PNGs once for the module."""
    d = tmp_path_factory.mktemp("phase7_fixtures")
    generate_all(str(d))
    return d


def _png_bytes(path) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


@pytest.mark.slow
def test_real_ocr_extracts_text_from_login_image(fixtures_dir):
    """A real EasyOCRBackend extracts recognizable tokens from text_login.png.

    Proves INPUT-06 with the real neural OCR backend (not a fake/Null stub).
    The fixture draws "Verify your PayPal account" and "Password", so the
    extracted text should contain at least one of those tokens.
    """
    backend = EasyOCRBackend()
    backend.warm_up()

    image = Image.open(fixtures_dir / "text_login.png").convert("RGB")
    text = backend.read_text(image)

    assert isinstance(text, str)
    assert text.strip() != "", "real OCR returned empty text for a text image"
    lowered = text.lower()
    assert any(tok in lowered for tok in ("paypal", "password", "verify", "account")), (
        f"expected a recognizable login token in OCR output, got: {text!r}"
    )


@pytest.mark.slow
def test_predict_image_end_to_end_login(fixtures_dir):
    """POST text_login.png to /predict/image and get a combined verdict.

    Exercises the full path: upload validation -> single real OCR pass ->
    email_ensemble ML signal + rules + visual signal -> MultiParadigmAggregator.
    """
    with TestClient(app) as client:
        resp = client.post(
            "/predict/image",
            files={"file": ("text_login.png", _png_bytes(fixtures_dir / "text_login.png"), "image/png")},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["content_type"] == "image"
    assert 0.0 <= body["final_probability"] <= 1.0
    # The combined verdict must reflect the multi-paradigm aggregation.
    assert body.get("paradigm_contributions") is not None
    assert isinstance(body.get("explanation", ""), str) and body["explanation"] != ""


@pytest.mark.slow
def test_predict_image_blank_is_stable(fixtures_dir):
    """A blank image yields a stable structured verdict (empty OCR text).

    Empty OCR text must still produce a fixed-length feature vector and a
    well-formed 200 response — no crash on the zero-text path.
    """
    with TestClient(app) as client:
        resp = client.post(
            "/predict/image",
            files={"file": ("blank.png", _png_bytes(fixtures_dir / "blank.png"), "image/png")},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["content_type"] == "image"
    assert 0.0 <= body["final_probability"] <= 1.0
