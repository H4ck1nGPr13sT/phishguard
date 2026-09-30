"""Image feature extraction for OCR-based phishing detection (Phase 7).

Delivers INPUT-06: extract text from an image via a pluggable, mockable OCR
backend (`src.features.ocr.backend.OCRBackend`) and feed that text into the
EXISTING `TextFeatureExtractor` pipeline (Phase 6), exactly the same way
`extract_email_features`/`extract_sms_features` reuse it — rather than
building a new NLP path for image-derived text.

Also delivers INPUT-07 (Plan 07-02): genuinely-new visual signal —
perceptual-hash brand similarity (`imagehash`) against a curated reference
set of commonly-phished brands, plus interpretable OpenCV layout/color
heuristics (edge density, color concentration, rectangular-element count).

Dependency isolation (mandatory, non-negotiable): this module imports only
Pillow (`PIL`) and stdlib at top level. It does NOT import cv2, imagehash,
easyocr, or torch at module scope — those are loaded LAZILY, inside the
functions that use them (`perceptual_hash_similarity`,
`_extract_layout_color_features`), and easyocr only ever loads inside the
injected `OCRBackend`. This keeps the fast unit test suite runnable with
zero torch/easyocr/cv2/imagehash install. Both visual-feature functions wrap
their entire body in try/except ImportError and return the canonical
`_VISUAL_FEATURE_KEYS` set with default values when the dependency is
absent — `extract_visual_features` therefore ALWAYS returns exactly
`_VISUAL_FEATURE_KEYS`, identical whether or not cv2/imagehash are
installed.

Public API:
    - load_and_ocr(image_bytes, ocr_backend) -> (PIL.Image.Image, str)
      The single OCR entry point — validates, preprocesses, and OCRs an
      image exactly once. Reused by this module's extract_image_features
      AND by the API endpoint added in Plan 07-04, so a given upload is
      never OCR'd twice.
    - extract_image_features(image_bytes, ocr_backend) -> Dict[str, float]
      All-numeric, constant-length feature dict combining OCR-derived text
      features, visual features, and an ocr_char_count.
    - extract_visual_features(image) -> Tuple[Dict[str, float], Optional[str]]
      Perceptual-hash brand similarity + layout/color heuristics, merged.
    - perceptual_hash_similarity(image, reference_hashes)
      -> Tuple[Dict[str, float], Optional[str]]
    - BRAND_MATCH_THRESHOLD: tunable Hamming-distance cutoff (see docstring
      on the constant itself — RESEARCH.md Pitfall 5 / Assumption A2).
"""

import io
import warnings
from typing import Dict, Optional, Tuple

from PIL import Image

from src.features.extractors import get_text_extractor
from src.features.ocr.reference_hashes import load_reference_hashes

# Hamming-distance cutoff on a 64-bit perceptual hash (imagehash.phash) used
# to flag "visually similar to a known-phished brand" (visual_brand_
# similarity_flag). 0 = identical hash, 64 = maximally distant.
#
# TUNABLE, NOT A VALIDATED FACT (RESEARCH.md Pitfall 5 / Assumption A2): 10
# is a commonly-cited illustrative starting point in imagehash tutorials,
# not empirically derived against a phishing-specific image dataset in this
# project. Must be validated empirically once a labeled evaluation set is
# available — see assets/brand_logos/README.md.
BRAND_MATCH_THRESHOLD = 10

# Canonical visual-feature key set. Both the cv2/imagehash-installed path
# and the absent-dependency fallback path return EXACTLY these keys — this
# is the mechanism that preserves the constant-key-set invariant guarding
# the downstream ensemble model (RESEARCH.md Pitfall 6) regardless of which
# optional dependencies happen to be installed.
_VISUAL_FEATURE_KEYS = (
    "visual_hash_distance",
    "visual_brand_similarity_flag",
    "visual_edge_density",
    "visual_color_concentration",
    "visual_rect_element_count",
)


def _default_visual_features() -> Dict[str, float]:
    """Every visual_* key defaulted to 0.0, except visual_hash_distance
    which defaults to 64.0 (maximally distant on a 64-bit perceptual hash —
    the "no similarity, unknown" default rather than a false "identical").
    """
    return {
        "visual_hash_distance": 64.0,
        "visual_brand_similarity_flag": 0.0,
        "visual_edge_density": 0.0,
        "visual_color_concentration": 0.0,
        "visual_rect_element_count": 0.0,
    }


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


def perceptual_hash_similarity(
    image: Image.Image, reference_hashes: Dict[str, "object"]
) -> Tuple[Dict[str, float], Optional[str]]:
    """Perceptual-hash brand similarity against a curated reference set.

    Computes `imagehash.phash(image)` and its Hamming distance (via
    `ImageHash.__sub__` — never hand-rolled bit counting) to every entry in
    `reference_hashes`, picking the closest brand.

    Dependency isolation: the ENTIRE body is wrapped in try/except
    ImportError. If `imagehash` is not installed, returns the default
    numeric dict (visual_hash_distance=64.0, visual_brand_similarity_flag=
    0.0) and `None` for the closest-brand label — no exception propagates.

    Args:
        image: A validated RGB PIL.Image.Image.
        reference_hashes: {brand: imagehash.ImageHash}, as returned by
            `src.features.ocr.reference_hashes.load_reference_hashes()`.
            May be empty (e.g. if the reference JSON couldn't be loaded).

    Returns:
        A tuple `(numeric_dict, closest_brand)`:
            - numeric_dict: {"visual_hash_distance": float 0..64,
              "visual_brand_similarity_flag": float 0.0/1.0}.
            - closest_brand: the brand name string with the smallest
              Hamming distance, or None if imagehash is unavailable or
              `reference_hashes` is empty. Kept OUT of the numeric dict —
              callers that need it get it as the second tuple element.
    """
    try:
        import imagehash
    except ImportError:
        return (
            {
                "visual_hash_distance": 64.0,
                "visual_brand_similarity_flag": 0.0,
            },
            None,
        )

    if not reference_hashes:
        return (
            {
                "visual_hash_distance": 64.0,
                "visual_brand_similarity_flag": 0.0,
            },
            None,
        )

    query_hash = imagehash.phash(image)
    distances = {
        brand: query_hash - ref_hash for brand, ref_hash in reference_hashes.items()
    }
    closest_brand = min(distances, key=distances.get)
    closest_distance = distances[closest_brand]

    return (
        {
            "visual_hash_distance": float(closest_distance),
            "visual_brand_similarity_flag": float(
                int(closest_distance <= BRAND_MATCH_THRESHOLD)
            ),
        },
        closest_brand,
    )


def _extract_layout_color_features(image: Image.Image) -> Dict[str, float]:
    """Interpretable OpenCV heuristics for 'suspicious UI element' signal
    (INPUT-07). Not ML-based — simple, explainable metrics consistent with
    the project's interpretability requirement (PROJECT.md).

    Dependency isolation: the ENTIRE body is wrapped in try/except
    ImportError. If `cv2` (or `numpy`, defensively) is not installed,
    returns the default zero-valued dict — no exception propagates.

    Args:
        image: A validated RGB PIL.Image.Image.

    Returns:
        {"visual_edge_density": float 0..1,
         "visual_color_concentration": float 0..1,
         "visual_rect_element_count": float >=0}.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        return {
            "visual_edge_density": 0.0,
            "visual_color_concentration": 0.0,
            "visual_rect_element_count": 0.0,
        }

    arr = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    # Edge density: form-heavy / button-heavy UIs (login pages) tend to have
    # more rectangular structure than plain content screenshots.
    edges = cv2.Canny(gray, 100, 200)
    edge_density = float(np.count_nonzero(edges)) / edges.size

    # Dominant color concentration: phishing login clones often reuse a
    # narrow brand palette — high concentration in a few color bins can be
    # a (weak, heuristic) signal.
    hist = cv2.calcHist([arr], [0, 1, 2], None, [8, 8, 8], [0, 256] * 3)
    hist_normalized = hist.flatten() / hist.sum()
    color_concentration = float(np.max(hist_normalized))

    # Rectangular-contour count as a rough proxy for form fields/buttons.
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    rect_like = sum(
        1
        for c in contours
        if len(cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)) == 4
    )

    return {
        "visual_edge_density": edge_density,
        "visual_color_concentration": color_concentration,
        "visual_rect_element_count": float(rect_like),
    }


def extract_visual_features(
    image: Image.Image,
) -> Tuple[Dict[str, float], Optional[str]]:
    """Perceptual-hash brand similarity + OpenCV layout/color heuristics,
    merged into a single dict with a GUARANTEED constant key set
    (`_VISUAL_FEATURE_KEYS`) regardless of whether cv2/imagehash are
    installed (BLOCKER 1 — graceful degradation).

    Args:
        image: A validated RGB PIL.Image.Image.

    Returns:
        A tuple `(visual_dict, closest_brand)`:
            - visual_dict: exactly `_VISUAL_FEATURE_KEYS`, all floats.
            - closest_brand: string label or None (imagehash unavailable,
              or no reference hashes loaded). Kept OUT of visual_dict.
    """
    try:
        reference_hashes = load_reference_hashes()
    except ImportError:
        reference_hashes = {}

    hash_features, closest_brand = perceptual_hash_similarity(image, reference_hashes)
    layout_features = _extract_layout_color_features(image)

    visual_dict: Dict[str, float] = dict(_default_visual_features())
    visual_dict.update(hash_features)
    visual_dict.update(layout_features)

    return visual_dict, closest_brand


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
    """Extract OCR-derived text features PLUS visual features from an image.

    Combines OCR text extraction with the EXISTING `TextFeatureExtractor`
    pipeline (Phase 6) — reusing `get_text_extractor().extract_all_features`
    exactly as `extract_email_features`/`extract_sms_features` do, rather
    than reimplementing NLP feature extraction for image-derived text — and
    merges in `extract_visual_features` (perceptual-hash brand similarity +
    OpenCV layout/color heuristics, Plan 07-02, INPUT-07).

    `extract_all_features` is called UNCONDITIONALLY, even when `ocr_text`
    is "" (blank image / no text detected), and `extract_visual_features`
    ALWAYS returns the full `_VISUAL_FEATURE_KEYS` set even when cv2/
    imagehash are not installed. This guards against Pitfall 6 (feature-
    vector length mismatch breaking the ensemble model): the returned dict
    has the SAME key set and length regardless of whether the image
    contains text and regardless of which optional visual dependencies are
    installed.

    Args:
        image_bytes: Raw, untrusted image bytes.
        ocr_backend: An object implementing `OCRBackend.read_text(image) ->
            str`.

    Returns:
        Dictionary mapping feature names to numeric values:
            - Every key from `TextFeatureExtractor.extract_all_features`,
              prefixed as `ocr_text_{k}`.
            - `ocr_char_count`: float length of the raw OCR text.
            - Every key in `_VISUAL_FEATURE_KEYS` (visual_hash_distance,
              visual_brand_similarity_flag, visual_edge_density,
              visual_color_concentration, visual_rect_element_count).

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

    visual_features, _closest_brand = extract_visual_features(image)
    features.update(visual_features)

    return features
