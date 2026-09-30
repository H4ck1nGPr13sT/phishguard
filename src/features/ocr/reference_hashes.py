"""Loader for the committed reference brand perceptual-hash table.

Reads `src/features/ocr/reference_brand_hashes.json` (built by
`assets/brand_logos/build_reference_hashes.py`, committed to the repo as the
source of truth) and converts each hex phash string into an
`imagehash.ImageHash` via `imagehash.hex_to_hash`.

Dependency isolation: `imagehash` is imported LAZILY, inside
`load_reference_hashes()`, never at module top level. If `imagehash` is not
installed, this raises `ImportError` from inside the function — callers
(`src/features/image_features.py`'s visual-feature path) are expected to
catch that inside their own try/except and fall back to
`_default_visual_features()`. This module is never the source of a hard
crash when imagehash is absent; the caller's try/except owns the
degradation.
"""

import json
import os
from typing import Dict

_REFERENCE_HASHES_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "reference_brand_hashes.json"
)

# Module-level singleton cache — parsed once per process.
_cached_hashes: Dict[str, "object"] = None  # type: ignore[assignment]


def load_reference_hashes() -> Dict[str, "object"]:
    """Return {brand: imagehash.ImageHash} from the committed reference JSON.

    Cached in a module-level singleton after first successful load (mirrors
    the singleton pattern used by `get_text_extractor()` in extractors.py).

    Returns:
        Dict mapping brand name -> imagehash.ImageHash.

    Raises:
        ImportError: If `imagehash` is not installed. Callers must catch
            this and fall back to default/zero visual features — this
            function is only ever invoked from within the visual path's
            try/except (see `extract_visual_features` in image_features.py).
    """
    global _cached_hashes

    import imagehash  # local import — keeps this module torch/cv2-free

    if _cached_hashes is not None:
        return _cached_hashes

    with open(_REFERENCE_HASHES_PATH) as fh:
        raw_table = json.load(fh)

    _cached_hashes = {
        brand: imagehash.hex_to_hash(hex_str) for brand, hex_str in raw_table.items()
    }
    return _cached_hashes
