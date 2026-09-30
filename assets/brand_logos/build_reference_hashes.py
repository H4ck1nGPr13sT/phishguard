"""Build the committed reference brand perceptual-hash table (Phase 7, Plan 07-02).

Produces `src/features/ocr/reference_brand_hashes.json`: a map of
`{brand: "<hex phash string>"}` used by `perceptual_hash_similarity()` in
`src/features/image_features.py` to flag visual similarity to commonly-
phished brands (INPUT-07).

Why placeholder tiles, not real logos
--------------------------------------
Real brand login-page screenshots/logos cannot be committed to this repo:
they are copyrighted assets and fetching them would require network access
at build time (neither is acceptable for a reproducible, offline-buildable
academic project). Instead, this script generates a deterministic Pillow
placeholder tile per brand — a solid brand-associated background color plus
the brand name rendered as text — and hashes that. The resulting phash
values are internally consistent (each brand's placeholder differs from the
others) but are NOT expected to match real-world screenshots of that brand
out of the box.

A developer with legitimate access to real brand assets can drop PNG
screenshots named `<brand>.png` into this directory (`assets/brand_logos/`)
and re-run this script — see `assets/brand_logos/README.md` for the full
replacement workflow. Real per-brand images, when present, are used
instead of the generated placeholder for that brand.

Usage
-----
    .venv/bin/pip install imagehash   # lightweight — only pulls Pillow/numpy
    .venv/bin/python assets/brand_logos/build_reference_hashes.py

Re-runnable: always overwrites `src/features/ocr/reference_brand_hashes.json`
with a freshly computed table. The committed JSON is the source of truth for
the fast (non-imagehash-installed) runtime path — this script is a build-time
tool, never imported/executed by application code or the fast test suite.
"""

import json
import os

from PIL import Image, ImageDraw

# Curated list of commonly-phished brands (paypal, major tech, two generic
# banks). Each entry maps to a background color used only for the
# placeholder tile — arbitrary, chosen to be visually distinct per brand so
# the resulting phashes differ from one another.
BRAND_COLORS = {
    "paypal": (0, 48, 135),
    "microsoft": (0, 120, 215),
    "apple": (30, 30, 30),
    "google": (66, 133, 244),
    "amazon": (255, 153, 0),
    "bank_of_america": (200, 16, 46),
    "chase": (17, 62, 141),
}

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(
    ASSETS_DIR, "..", "..", "src", "features", "ocr", "reference_brand_hashes.json"
)
TILE_SIZE = (256, 256)


def _placeholder_tile(brand: str, color: tuple) -> Image.Image:
    """Deterministic Pillow-only placeholder tile for a brand.

    perceptual_hash (imagehash.phash) discards the DC/average frequency
    term, so a plain solid-color background + small centered text is NOT
    enough to differentiate brands whose only difference is background
    color/text position — those collapse to identical hashes. To produce
    per-brand-distinct low-frequency structure, each tile also gets a
    deterministic geometric layout (vertical color bar width + horizontal
    color band height, both derived from a hash of the brand name) so the
    DCT coefficients phash inspects actually differ brand-to-brand.
    """
    image = Image.new("RGB", TILE_SIZE, color="white")
    draw = ImageDraw.Draw(image)

    # Deterministic per-brand seed drives structurally distinct layouts —
    # NOT just a color/text difference, which phash would largely ignore.
    seed = sum((i + 1) * ord(c) for i, c in enumerate(brand))
    bar_width = 40 + (seed * 7) % (TILE_SIZE[0] - 80)
    band_height = 30 + (seed * 13) % (TILE_SIZE[1] - 60)

    # Vertical color bar (width varies per brand).
    draw.rectangle((0, 0, bar_width, TILE_SIZE[1]), fill=color)
    # Horizontal color band (height + vertical offset vary per brand).
    band_top = (seed * 5) % (TILE_SIZE[1] - band_height)
    draw.rectangle((0, band_top, TILE_SIZE[0], band_top + band_height), fill=color)

    label = brand.replace("_", " ").upper()
    # No custom font dependency — default bitmap font is deterministic
    # across platforms for this build-time-only script.
    draw.text((10, TILE_SIZE[1] - 30), label, fill=color)
    return image


def _brand_tile(brand: str, color: tuple) -> Image.Image:
    """Return the brand's tile: a real dropped-in `<brand>.png` if present
    under `assets/brand_logos/`, otherwise the generated placeholder.
    """
    real_path = os.path.join(ASSETS_DIR, f"{brand}.png")
    if os.path.isfile(real_path):
        return Image.open(real_path).convert("RGB")
    return _placeholder_tile(brand, color)


def build_reference_hashes() -> dict:
    """Compute {brand: hex phash string} for every curated brand.

    Imports imagehash lazily (build-time-only dependency; never required by
    the fast unit-test suite or the runtime fallback path).
    """
    import imagehash  # local import — build-time-only dependency

    table = {}
    for brand, color in BRAND_COLORS.items():
        tile = _brand_tile(brand, color)
        phash = imagehash.phash(tile)
        table[brand] = str(phash)
    return table


def main() -> None:
    table = build_reference_hashes()
    output_path = os.path.normpath(OUTPUT_PATH)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as fh:
        json.dump(table, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(f"Wrote {len(table)} brand hashes to {output_path}")


if __name__ == "__main__":
    main()
