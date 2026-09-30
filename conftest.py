"""Project-wide pytest configuration.

This file is imported by pytest very early — before any test module is
collected — which is exactly why the OpenMP workaround below lives here.

OpenMP duplicate-runtime guard (macOS):
    Once the optional Phase 7 dependencies are installed, both PyTorch (via
    EasyOCR) and XGBoost (via the email/SMS ensembles) ship their own OpenMP
    runtime. Loading both into a single Python process on macOS triggers a hard
    segmentation fault ("OMP: Error #15 ... libomp already initialized"). Setting
    ``KMP_DUPLICATE_LIB_OK=TRUE`` before either library is imported lets them
    coexist. This only matters on a machine where the heavy Phase 7 deps are
    installed; the fast, torch-free suite is unaffected. We set it here rather
    than relying on the caller's shell so ``pytest`` works out of the box.
"""

import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")


def pytest_configure(config):
    """Register custom markers so they don't emit PytestUnknownMarkWarning."""
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (real EasyOCR/torch backend; deselect with '-m \"not slow\"')",
    )
