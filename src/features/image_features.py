"""Image feature extraction for OCR-based phishing detection (Phase 7).

Delivers INPUT-06: extract text from an image via a pluggable, mockable OCR
backend (`src.features.ocr.backend.OCRBackend`) and feed that text into the
EXISTING `TextFeatureExtractor` pipeline (Phase 6), exactly the same way
`extract_email_features`/`extract_sms_features` reuse it — rather than
building a new NLP path for image-derived text.

Dependency isolation (mandatory, non-negotiable): this module imports only
Pillow (`PIL`) and stdlib at top level. It does NOT import cv2, imagehash,
easyocr, or torch at module scope — those are loaded lazily elsewhere
(cv2/imagehash arrive with the visual-feature path in Plan 07-02; easyocr
only ever loads inside the injected `OCRBackend`). This keeps the fast unit
test suite runnable with zero torch/easyocr install.

Public API:
    - load_and_ocr(image_bytes, ocr_backend) -> (PIL.Image.Image, str)
      The single OCR entry point — validates, preprocesses, and OCRs an
      image exactly once. Reused by this module's extract_image_features
      AND by the API endpoint added in Plan 07-04, so a given upload is
      never OCR'd twice.
    - extract_image_features(image_bytes, ocr_backend) -> Dict[str, float]
      All-numeric, constant-length feature dict combining OCR-derived text
      features with an ocr_char_count. Visual features are merged in by
      Plan 07-02 at the marked insertion point below.
"""

import io
import warnings
from typing import Dict, Tuple

from PIL import Image

from src.features.extractors import get_text_extractor


def _load_and_validate_image(image_bytes: bytes) -> Image.Image:
    """Decode and validate raw image bytes into an RGB PIL image.

    Mitigates T-07-01 (decompression bomb DoS) and T-07-02 (tampering via a
    malformed/polyglot file handed to the decoder):
        - Promotes Image.DecompressionBombWarning to an exception (Pillow
          only *warns* by default between 1x-2x MAX_IMAGE_PIXELS; this
          module treats that warning as a hard failure instead).
        - Leaves Image.MAX_IMAGE_PIXELS enabled (never disabled) so Pillow's
          own decompression-bomb ceiling still applies.
        - Calls `.verify()` on a first handle for structural validation,
          then re-opens a fresh handle (verify() leaves the image unusable
          for further operations) before converting to RGB.
        - Operates entirely in-memory via io.BytesIO; never writes the
          uploaded bytes to disk.

    Args:
        image_bytes: Raw, untrusted image bytes (e.g. from an HTTP upload).

    Returns:
        A validated PIL.Image.Image in RGB mode.

    Raises:
        ValueError: If the bytes are not a valid/decodable image, or if the
            image exceeds the configured decompression-bomb pixel ceiling.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)

            # First handle: structural validation only. verify() leaves the
            # image object unusable for further decoding, so we discard it.
            probe = Image.open(io.BytesIO(image_bytes))
            probe.verify()

            # Second handle: fresh open + actual RGB conversion.
            image = Image.open(io.BytesIO(image_bytes))
            rgb_image = image.convert("RGB")
            return rgb_image
    except (
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
    ) as exc:
        raise ValueError(f"Image rejected — decompression bomb guard: {exc}") from exc
    except Exception as exc:
        raise ValueError(f"Invalid or corrupt image bytes: {exc}") from exc


def _preprocess_for_ocr(image: Image.Image) -> Image.Image:
    """Light, dependency-free preparation of an image before OCR.

    Currently a pass-through (returns the RGB PIL image unchanged). OpenCV-
    based denoise/contrast enhancement is deliberately deferred/optional —
    keeping this function torch/cv2-free means the OCR-text feature path
    unit-tests without any heavy image-processing dependency installed.

    Args:
        image: A validated RGB PIL.Image.Image.

    Returns:
        The (possibly transformed) PIL.Image.Image ready to hand to an
        OCRBackend.
    """
    return image


def load_and_ocr(image_bytes: bytes, ocr_backend) -> Tuple[Image.Image, str]:
    """Validate, preprocess, and OCR an image — the single OCR entry point.

    Runs `ocr_backend.read_text()` exactly ONCE per call. Both this module's
    `extract_image_features` and the `/predict/image` API endpoint (Plan
    07-04) call this function rather than invoking the OCR backend directly,
    so a given upload is never OCR'd twice on any code path.

    Args:
        image_bytes: Raw, untrusted image bytes.
        ocr_backend: An object implementing `OCRBackend.read_text(image) ->
            str` (e.g. `NullOCRBackend`, `EasyOCRBackend`, or a test double).

    Returns:
        A tuple `(rgb_image, ocr_text)`:
            - rgb_image: the validated, preprocessed PIL.Image.Image.
            - ocr_text: the raw string returned by the OCR backend.

    Raises:
        ValueError: If `image_bytes` is not a valid/decodable image, or
            exceeds the decompression-bomb pixel ceiling.
    """
    image = _load_and_validate_image(image_bytes)
    preprocessed = _preprocess_for_ocr(image)
    ocr_text = ocr_backend.read_text(preprocessed)
    return image, ocr_text


def extract_image_features(image_bytes: bytes, ocr_backend) -> Dict[str, float]:
    """Extract OCR-derived text features from an image.

    Combines OCR text extraction with the EXISTING `TextFeatureExtractor`
    pipeline (Phase 6) — reusing `get_text_extractor().extract_all_features`
    exactly as `extract_email_features`/`extract_sms_features` do, rather
    than reimplementing NLP feature extraction for image-derived text.

    `extract_all_features` is called UNCONDITIONALLY, even when `ocr_text`
    is "" (blank image / no text detected). This guards against Pitfall 6
    (feature-vector length mismatch breaking the ensemble model): the
    returned dict has the SAME key set and length regardless of whether the
    image contains text.

    Args:
        image_bytes: Raw, untrusted image bytes.
        ocr_backend: An object implementing `OCRBackend.read_text(image) ->
            str`.

    Returns:
        Dictionary mapping feature names to numeric values:
            - Every key from `TextFeatureExtractor.extract_all_features`,
              prefixed as `ocr_text_{k}`.
            - `ocr_char_count`: float length of the raw OCR text.
        (Plan 07-02 merges in visual features — perceptual hash + layout/
        color heuristics — at the marked insertion point below.)

    Raises:
        ValueError: If `image_bytes` is not a valid/decodable image, or
            exceeds the decompression-bomb pixel ceiling (propagated from
            `load_and_ocr`).

    Examples:
        >>> class FakeBackend:
        ...     def read_text(self, image):
        ...         return "Verify your account"
        >>> features = extract_image_features(png_bytes, FakeBackend())
        >>> features['ocr_char_count']
        20.0
    """
    image, ocr_text = load_and_ocr(image_bytes, ocr_backend)

    text_extractor = get_text_extractor()
    text_features = text_extractor.extract_all_features(ocr_text)
    text_features_prefixed = {f"ocr_text_{k}": v for k, v in text_features.items()}

    features: Dict[str, float] = {
        **text_features_prefixed,
        "ocr_char_count": float(len(ocr_text)),
    }

    # --- Visual feature insertion point (Plan 07-02) ---
    # features.update(extract_visual_features(image))
    # ----------------------------------------------------

    return features
