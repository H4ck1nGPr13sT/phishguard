"""Pluggable, lazy-loaded OCR backend abstraction.

This module defines the `OCRBackend` interface used by `image_features.py` to
extract text from images without forcing a hard dependency on `easyocr`/`torch`
at import time. This is the mandatory dependency-isolation pattern for Phase 7:
the fast unit-test suite must keep running with NO torch/easyocr installed.

Three implementations are provided:
    - `NullOCRBackend`: always returns "" (used as a safe fallback and as a
      cheap default for environments without easyocr/torch installed).
    - `EasyOCRBackend`: wraps `easyocr.Reader`, but only ever imports `easyocr`
      lazily, inside `_get_reader()` — never at module top level.
    - `resolve_ocr_backend()`: factory that tries to build an `EasyOCRBackend`
      and falls back to `NullOCRBackend` if `easyocr` is not importable.

Unit tests should inject a fake/test double implementing the same
`read_text(image) -> str` contract rather than relying on `EasyOCRBackend`.
"""

import logging
from typing import List, Protocol, Sequence, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class OCRBackend(Protocol):
    """Structural interface every OCR backend implements.

    Any object exposing a compatible `read_text` method satisfies this
    protocol — no explicit inheritance required (duck typing), which is what
    makes fake/test backends trivial to inject in unit tests.
    """

    def read_text(self, image) -> str:
        """Extract and return recognized text from an image.

        Args:
            image: A PIL.Image.Image or numpy array representing the image
                to run OCR on.

        Returns:
            The recognized text as a single string. Implementations should
            return "" (never raise) when no text is found or OCR is
            unavailable, so downstream feature extraction always receives a
            string.
        """
        ...


class NullOCRBackend:
    """Fallback OCR backend used when easyocr/torch is not installed or fails
    to load.

    Always returns an empty string and logs a warning. Downstream text-feature
    extraction (`TextFeatureExtractor.extract_all_features`) already handles
    an empty string gracefully (all-zero linguistic features), so the request
    pipeline degrades gracefully instead of crashing.
    """

    def read_text(self, image) -> str:
        """Return "" and log a warning that OCR is unavailable.

        Args:
            image: Unused — accepted only to satisfy the `OCRBackend`
                protocol signature.

        Returns:
            Always "".
        """
        logger.warning("OCR backend unavailable — returning empty text")
        return ""


class EasyOCRBackend:
    """Lazy-loaded EasyOCR-backed OCR backend.

    The `easyocr.Reader` (and therefore `torch`) is NEVER imported at module
    top level or in `__init__`. It is constructed on first use inside
    `_get_reader()` (or eagerly via `warm_up()`), then cached on the instance
    — mirroring the singleton-on-first-use pattern used for the spaCy-backed
    `TextFeatureExtractor` in `src/features/extractors.py`.
    """

    def __init__(self, languages: Sequence[str] = ("en",), gpu: bool = False):
        """Store configuration only — does not load any model weights.

        Args:
            languages: Language codes passed to `easyocr.Reader`.
            gpu: Whether to request GPU inference from EasyOCR. Defaults to
                False (CPU-only), matching the project's Standard Stack
                decision to use CPU wheels for torch.
        """
        self._languages: List[str] = list(languages)
        self._gpu = gpu
        self._reader = None  # NOT loaded here — loaded lazily in _get_reader()

    def _get_reader(self):
        """Lazily construct and cache the `easyocr.Reader` instance.

        This is the ONLY place in the module that imports `easyocr`. Import
        happens inside the function body so that importing this module (or
        `src.features.ocr`) never requires easyocr/torch to be installed.

        Returns:
            A cached `easyocr.Reader` instance.
        """
        if self._reader is None:
            import easyocr  # local import — heavy dep isolated here

            self._reader = easyocr.Reader(
                self._languages, gpu=self._gpu, verbose=False
            )
        return self._reader

    def warm_up(self) -> None:
        """Force the reader to load now rather than on first `read_text` call.

        Intended to be called once at process startup (e.g., FastAPI
        `lifespan`) so the multi-second model-load cost is paid once, not on
        the first user request.
        """
        self._get_reader()

    def read_text(self, image) -> str:
        """Run OCR on `image` and return recognized text joined by spaces.

        Args:
            image: A PIL.Image.Image or numpy array. EasyOCR's `readtext`
                accepts either directly, so no conversion happens here.

        Returns:
            Recognized text strings (confidence > 0.3) joined by a single
            space. Returns "" if nothing is recognized above the confidence
            threshold.
        """
        reader = self._get_reader()
        # readtext returns a list of (bbox, text, confidence) tuples.
        results = reader.readtext(image, detail=1)
        return " ".join(text for _, text, conf in results if conf > 0.3)


def resolve_ocr_backend() -> "OCRBackend":
    """Factory: build the best available OCR backend.

    Tries to import `easyocr` (availability check only) and, if successful,
    returns an `EasyOCRBackend`. If `easyocr` is not installed, falls back to
    `NullOCRBackend` so the rest of the application keeps functioning.

    Returns:
        An `EasyOCRBackend` if easyocr is importable, else a `NullOCRBackend`.
    """
    try:
        import easyocr  # noqa: F401 — import-only availability check

        return EasyOCRBackend()
    except ImportError:
        logger.warning(
            "easyocr not installed — resolve_ocr_backend() falling back to "
            "NullOCRBackend"
        )
        return NullOCRBackend()
