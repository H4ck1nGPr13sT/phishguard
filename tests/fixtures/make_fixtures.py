"""Generate deterministic PNG test fixtures for Phase 7 image-feature tests.

Uses ONLY Pillow (already an installed project dependency) — no OCR/CV
libraries required, so fixture generation itself stays torch-free.

Produces four fixtures under `tests/fixtures/`:
    - text_login.png: white background with drawn text resembling a login
      prompt (used to exercise the OCR-text feature path with a fake/real
      backend).
    - blank.png: solid white image, no text (used to exercise the
      empty-OCR-text / graceful-degradation path).
    - truncated.png: a valid PNG header followed by deliberately truncated
      bytes, simulating a corrupt upload (used to exercise the
      invalid-image-bytes ValueError path).
    - form_like.png: white image with drawn rectangles resembling input
      fields/buttons (used by later Phase 7 plans for visual/layout
      features).

Run directly to (re)generate the fixtures on disk:
    .venv/bin/python tests/fixtures/make_fixtures.py
"""

import io
import os

from PIL import Image, ImageDraw


def _make_text_login() -> Image.Image:
    """White background with black text resembling a login/verify prompt."""
    image = Image.new("RGB", (400, 200), color="white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 40), "Verify your PayPal account", fill="black")
    draw.text((20, 90), "Password", fill="black")
    draw.rectangle((20, 120, 300, 150), outline="black", width=2)
    return image


def _make_blank() -> Image.Image:
    """Solid white image with no text or shapes."""
    return Image.new("RGB", (200, 200), color="white")


def _make_form_like() -> Image.Image:
    """White image with rectangles resembling input fields/buttons."""
    image = Image.new("RGB", (400, 300), color="white")
    draw = ImageDraw.Draw(image)
    # "Input fields"
    draw.rectangle((30, 40, 350, 80), outline="black", width=2)
    draw.rectangle((30, 100, 350, 140), outline="black", width=2)
    # "Button"
    draw.rectangle((30, 180, 180, 220), fill=(0, 90, 200))
    return image


def _make_truncated(target_dir: str) -> bytes:
    """Build a valid PNG in-memory, then chop trailing bytes to corrupt it.

    Returns the truncated bytes (also written to disk by `generate_all`).
    """
    image = Image.new("RGB", (100, 100), color="red")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    full_bytes = buffer.getvalue()
    # Keep the PNG signature + partial header, drop the rest so decoding fails.
    truncated_bytes = full_bytes[: max(16, len(full_bytes) // 4)]
    return truncated_bytes


def generate_all(target_dir: str) -> None:
    """Generate all four fixture PNGs into `target_dir`.

    Args:
        target_dir: Directory to write the fixture files into. Created if it
            does not already exist.
    """
    os.makedirs(target_dir, exist_ok=True)

    _make_text_login().save(os.path.join(target_dir, "text_login.png"))
    _make_blank().save(os.path.join(target_dir, "blank.png"))
    _make_form_like().save(os.path.join(target_dir, "form_like.png"))

    truncated_bytes = _make_truncated(target_dir)
    with open(os.path.join(target_dir, "truncated.png"), "wb") as fh:
        fh.write(truncated_bytes)


if __name__ == "__main__":
    _here = os.path.dirname(os.path.abspath(__file__))
    generate_all(_here)
    print(f"Fixtures written to {_here}")
