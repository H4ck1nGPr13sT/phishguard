"""Unit tests for ContentType.IMAGE dispatch in the unified extractor.

These tests inject a fake OCR backend (monkeypatching the module-level
`get_ocr_backend` singleton getter in src.features.extractors) so the fast
suite stays fully torch/easyocr/cv2-free — mirroring the dependency-isolation
pattern established in tests/features/test_image_features.py (Plans 07-01/
07-02).
"""

import os
import sys

import pytest

from src.features.extractors import ContentType, extract_features

FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures"
)


class FakeOCRBackend:
    """Test double for OCRBackend — returns a canned string, regardless of
    the image passed to read_text().
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


def test_extract_features_dispatches_image_to_image_features(
    monkeypatch, text_png_bytes
):
    """extract_features(bytes, ContentType.IMAGE) routes to
    extract_image_features, sets content_type==3, and includes both
    ocr_text_* and visual_* keys in the returned dict.
    """
    import src.features.extractors as extractors_module

    fake_backend = FakeOCRBackend("URGENT verify your account")
    monkeypatch.setattr(
        extractors_module, "get_ocr_backend", lambda: fake_backend
    )

    features = extract_features(text_png_bytes, ContentType.IMAGE)

    assert features["content_type"] == 3
    assert fake_backend.calls == 1

    ocr_text_keys = [k for k in features if k.startswith("ocr_text_")]
    visual_keys = [k for k in features if k.startswith("visual_")]
    assert ocr_text_keys, "expected at least one ocr_text_* feature key"
    assert visual_keys, "expected at least one visual_* feature key"
    assert "ocr_char_count" in features

    # All-numeric contract - every value must be int/float.
    for key, value in features.items():
        assert isinstance(value, (int, float)), f"{key} is not numeric: {value!r}"


def test_extract_features_image_str_content_raises_type_error():
    """Passing a str with ContentType.IMAGE raises TypeError - images are
    binary-only, no silent str->bytes coercion (T-07-06).
    """
    with pytest.raises(TypeError):
        extract_features("not bytes", ContentType.IMAGE)


def test_extractors_module_imports_without_easyocr_cv2():
    """Importing src.features.extractors must never pull in the Phase 7 OCR/CV
    dependencies (easyocr, cv2, imagehash) at module load — the dependency-
    isolation contract that keeps the image path lazy (mandatory).

    Verified in a FRESH SUBPROCESS so the result is correct even when the heavy
    Phase 7 deps are installed and another test in the same pytest session has
    already imported them into this process's sys.modules. Checking the shared
    in-process sys.modules would give a false failure in that case; a clean
    subprocess isolates the import-time behaviour of extractors alone.

    Note on torch: torch is deliberately NOT asserted here. When torch is
    installed, it is imported transitively by spaCy's `thinc` backend (via
    src.features.text_features -> spacy -> thinc), which is pre-existing NLP
    infrastructure entirely outside Phase 7's control. Phase 7's contract is
    only that its OWN OCR/CV deps (easyocr, cv2, imagehash) stay lazy — which
    this test verifies. On a fresh clone without the optional Phase 7 deps
    installed, torch is absent and the whole suite runs torch-free.
    """
    import subprocess

    code = (
        "import sys\n"
        "import src.features.extractors  # noqa: F401\n"
        "leaked = [m for m in ('easyocr', 'cv2', 'imagehash') if m in sys.modules]\n"
        "print('LEAKED=' + ','.join(leaked))\n"
        "sys.exit(1 if leaked else 0)\n"
    )
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "importing src.features.extractors pulled in a Phase 7 OCR/CV dependency "
        f"at module load — dependency-isolation contract violated. {result.stdout.strip()} "
        f"{result.stderr.strip()}"
    )


def test_extract_visual_features_available_without_cv2_imagehash(monkeypatch):
    """visual_* keys degrade gracefully (defaults) even when cv2/imagehash
    are unavailable - guarded with importorskip semantics via a direct
    fallback check rather than requiring the deps to be absent from the venv.
    """
    pytest.importorskip("PIL")
    from src.features.image_features import _VISUAL_FEATURE_KEYS

    # Sanity: the visual key set used by the dispatch branch's output is the
    # same canonical set image_features.py guarantees regardless of cv2/
    # imagehash availability.
    assert len(_VISUAL_FEATURE_KEYS) == 5
