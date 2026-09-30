"""Unit tests for the OCR-text and visual feature paths of image_features.py.

The OCR-text tests MUST NOT import easyocr/torch/cv2/imagehash — they inject
a `FakeOCRBackend` test double so the fast suite stays fully torch-free
(mandatory dependency-isolation constraint for Phase 7).

The visual-feature tests below are split into two groups:
    - Installed-path tests (guarded by `pytest.importorskip`) — only run
      when cv2/imagehash happen to be installed in the current venv.
    - Absent-deps fallback tests (run ALWAYS, no importorskip) — simulate
      cv2/imagehash being unavailable via a monkeypatched `builtins.__import__`
      and assert graceful degradation (Plan 07-02 BLOCKER 1).
"""

import builtins
import io
import os

import pytest
from PIL import Image

from src.features.image_features import (
    BRAND_MATCH_THRESHOLD,
    _VISUAL_FEATURE_KEYS,
    _default_visual_features,
    extract_image_features,
    extract_visual_features,
    load_and_ocr,
    perceptual_hash_similarity,
)

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
    # len("URGENT verify your account") == 26
    assert features["ocr_char_count"] == 26


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


# ---------------------------------------------------------------------------
# Visual features (Plan 07-02): perceptual-hash brand similarity + OpenCV
# layout/color heuristics.
# ---------------------------------------------------------------------------


def _open_rgb(image_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


class _ImportBlocker:
    """Context manager that makes `import <name>` raise ImportError for any
    module name in `blocked_names`, while delegating every other import to
    the real `builtins.__import__`. Used to simulate cv2/imagehash being
    absent even when they ARE installed in the current venv, so the
    graceful-degradation path is exercised deterministically regardless of
    what's actually installed.
    """

    def __init__(self, blocked_names):
        self._blocked_names = set(blocked_names)
        self._real_import = builtins.__import__

    def __enter__(self):
        real_import = self._real_import
        blocked_names = self._blocked_names

        def fake_import(name, *args, **kwargs):
            if name in blocked_names:
                raise ImportError(f"simulated absent dependency: {name}")
            return real_import(name, *args, **kwargs)

        builtins.__import__ = fake_import
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        builtins.__import__ = self._real_import
        return False


# --- Installed-path tests (skip cleanly if cv2/imagehash are absent) -------


@pytest.mark.parametrize("_dep", ["imagehash"])
def test_perceptual_hash_self_match_distance_zero(_dep):
    """Hashing a brand's own reference tile matches that brand at
    Hamming distance 0 (guards the must_haves truth for this plan).
    """
    pytest.importorskip("imagehash")
    from assets.brand_logos.build_reference_hashes import BRAND_COLORS, _placeholder_tile
    from src.features.ocr.reference_hashes import load_reference_hashes

    reference_hashes = load_reference_hashes()
    brand = "paypal"
    assert brand in reference_hashes

    tile = _placeholder_tile(brand, BRAND_COLORS[brand])
    numeric, closest_brand = perceptual_hash_similarity(tile, reference_hashes)

    assert closest_brand == brand
    assert numeric["visual_hash_distance"] == 0.0
    assert numeric["visual_brand_similarity_flag"] == 1.0


def test_layout_color_heuristics_ranges(text_png_bytes):
    """OpenCV layout/color heuristics return finite floats in documented
    ranges when cv2 is installed.
    """
    pytest.importorskip("cv2")
    from src.features.image_features import _extract_layout_color_features

    image = _open_rgb(text_png_bytes)
    features = _extract_layout_color_features(image)

    assert set(features.keys()) == {
        "visual_edge_density",
        "visual_color_concentration",
        "visual_rect_element_count",
    }
    assert 0.0 <= features["visual_edge_density"] <= 1.0
    assert 0.0 <= features["visual_color_concentration"] <= 1.0
    assert features["visual_rect_element_count"] >= 0.0


# --- Absent-deps fallback tests (ALWAYS run — no importorskip) -------------


def test_extract_visual_features_fallback_full_key_set_no_exception(
    text_png_bytes,
):
    """With cv2 AND imagehash simulated absent, extract_visual_features
    still returns the FULL _VISUAL_FEATURE_KEYS set with zero/default
    values and raises no exception (BLOCKER 1).
    """
    image = _open_rgb(text_png_bytes)

    with _ImportBlocker(["cv2", "imagehash"]):
        visual_dict, closest_brand = extract_visual_features(image)

    assert set(visual_dict.keys()) == set(_VISUAL_FEATURE_KEYS)
    assert visual_dict == _default_visual_features()
    assert closest_brand is None


def test_extract_image_features_fallback_identical_keys_text_vs_blank(
    text_png_bytes, blank_png_bytes
):
    """On the absent-deps fallback path, extract_image_features's full key
    set (OCR-text + visual) is identical across a text-bearing image and a
    blank image.
    """
    text_backend = FakeOCRBackend("URGENT verify your account")
    blank_backend = FakeOCRBackend("")

    with _ImportBlocker(["cv2", "imagehash"]):
        text_features = extract_image_features(text_png_bytes, text_backend)
        blank_features = extract_image_features(blank_png_bytes, blank_backend)

    assert set(text_features.keys()) == set(blank_features.keys())
    for key in _VISUAL_FEATURE_KEYS:
        assert key in text_features
        assert key in blank_features


def test_extract_image_features_key_set_identical_with_and_without_deps(
    text_png_bytes,
):
    """The full extract_image_features key set is identical whether or not
    cv2/imagehash are importable — the constant-key invariant that protects
    the downstream ensemble model (RESEARCH.md Pitfall 6).
    """
    fake_backend = FakeOCRBackend("Verify your account now")

    normal_features = extract_image_features(text_png_bytes, fake_backend)
    with _ImportBlocker(["cv2", "imagehash"]):
        fallback_features = extract_image_features(text_png_bytes, fake_backend)

    assert set(normal_features.keys()) == set(fallback_features.keys())


def test_default_visual_features_has_documented_defaults():
    """_default_visual_features() defaults every key to 0.0 except
    visual_hash_distance, which defaults to 64.0 (maximally distant on a
    64-bit perceptual hash).
    """
    defaults = _default_visual_features()

    assert set(defaults.keys()) == set(_VISUAL_FEATURE_KEYS)
    assert defaults["visual_hash_distance"] == 64.0
    assert defaults["visual_brand_similarity_flag"] == 0.0
    assert defaults["visual_edge_density"] == 0.0
    assert defaults["visual_color_concentration"] == 0.0
    assert defaults["visual_rect_element_count"] == 0.0


def test_brand_match_threshold_is_tunable_constant():
    """BRAND_MATCH_THRESHOLD exists as a documented, tunable module
    constant (RESEARCH.md Pitfall 5 / Assumption A2) — not asserted as a
    validated fact, just present and usable.
    """
    assert isinstance(BRAND_MATCH_THRESHOLD, int)
    assert BRAND_MATCH_THRESHOLD > 0
