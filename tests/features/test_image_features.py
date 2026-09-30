"""Unit tests for the OCR-text feature path of image_features.py.

These tests MUST NOT import easyocr/torch/cv2/imagehash — they inject a
`FakeOCRBackend` test double so the fast suite stays fully torch-free
(mandatory dependency-isolation constraint for Phase 7).
"""

import os

import pytest
from PIL import Image

from src.features.image_features import extract_image_features, load_and_ocr

FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures"
)


class FakeOCRBackend:
    """Test double for OCRBackend — returns a canned string set at
    construction, regardless of the image passed to read_text().
    """

    def __init__(self, text: str):
        self._text = text
        self.calls = 0

    def read_text(self, image) -> str:
        self.calls += 1
        return self._text


def _fixture_bytes(name: str) -> bytes:
    with open(os.path.join(FIXTURES_DIR, name), "rb") as fh:
        return fh.read()


@pytest.fixture
def text_png_bytes() -> bytes:
    return _fixture_bytes("text_login.png")


@pytest.fixture
def blank_png_bytes() -> bytes:
    return _fixture_bytes("blank.png")


@pytest.fixture
def truncated_png_bytes() -> bytes:
    return _fixture_bytes("truncated.png")


def test_load_and_ocr_returns_image_and_text_exactly_once(text_png_bytes):
    """load_and_ocr returns (PIL.Image, str), calling read_text exactly once."""
    fake_backend = FakeOCRBackend("URGENT verify your account")
    image, ocr_text = load_and_ocr(text_png_bytes, fake_backend)

    assert isinstance(image, Image.Image)
    assert ocr_text == "URGENT verify your account"
    assert fake_backend.calls == 1


def test_extract_image_features_ocr_text_path(text_png_bytes):
    """OCR text with content produces ocr_text_* keys with signal and the
    correct char count.
    """
    fake_backend = FakeOCRBackend("URGENT verify your account")
    features = extract_image_features(text_png_bytes, fake_backend)

    ocr_text_keys = [k for k in features if k.startswith("ocr_text_")]
    assert len(ocr_text_keys) > 0
    # At least one text feature should carry non-zero linguistic signal for
    # a clearly urgent phishing-style string.
    assert any(v != 0 for k, v in features.items() if k.startswith("ocr_text_"))
    assert features["ocr_char_count"] == 24


def test_extract_image_features_blank_image_same_keys(
    text_png_bytes, blank_png_bytes
):
    """Blank image (empty OCR text) yields the SAME key set as a
    text-bearing image — guards against feature-vector length drift
    (Pitfall 6).
    """
    text_backend = FakeOCRBackend("URGENT verify your account")
    blank_backend = FakeOCRBackend("")

    text_features = extract_image_features(text_png_bytes, text_backend)
    blank_features = extract_image_features(blank_png_bytes, blank_backend)

    assert set(text_features.keys()) == set(blank_features.keys())
    assert len(text_features) == len(blank_features)
    assert blank_features["ocr_char_count"] == 0


def test_extract_image_features_invalid_bytes_raises_value_error(
    truncated_png_bytes,
):
    """Non-image / corrupt bytes raise ValueError from
    _load_and_validate_image (via load_and_ocr).
    """
    fake_backend = FakeOCRBackend("")
    with pytest.raises(ValueError):
        extract_image_features(truncated_png_bytes, fake_backend)


def test_extract_image_features_decompression_bomb_raises_value_error(
    monkeypatch,
):
    """A crafted decompression-bomb image (pixel count above the configured
    limit) raises ValueError instead of merely warning.
    """
    # Shrink the pixel-count ceiling so a small, cheaply-generated image
    # counts as a "bomb" without needing to allocate a huge real image.
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)

    bomb_image = Image.new("RGB", (50, 50), color="white")  # 2500 px > 100
    import io

    buffer = io.BytesIO()
    bomb_image.save(buffer, format="PNG")
    bomb_bytes = buffer.getvalue()

    fake_backend = FakeOCRBackend("")
    with pytest.raises(ValueError):
        extract_image_features(bomb_bytes, fake_backend)
