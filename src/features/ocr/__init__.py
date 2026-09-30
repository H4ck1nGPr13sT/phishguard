"""OCR backend subpackage.

Re-exports the OCR backend interface and implementations so callers can
`from src.features.ocr import resolve_ocr_backend` etc. Importing this
package never requires easyocr/torch to be installed — see backend.py for
the lazy-import contract.
"""

from src.features.ocr.backend import (
    EasyOCRBackend,
    NullOCRBackend,
    OCRBackend,
    resolve_ocr_backend,
)

__all__ = [
    "OCRBackend",
    "NullOCRBackend",
    "EasyOCRBackend",
    "resolve_ocr_backend",
]
