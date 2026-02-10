"""Configuration settings loaded from environment variables.

This module loads configuration from .env file at import time and provides
settings as module-level constants. Uses python-dotenv for .env file support.

Environment Variables:
    DATA_DIR: Path to external data storage (default: ./data)
    CACHE_DIR: Path to cache directory (default: ./cache)
    PHISHTANK_API_KEY: API key for PhishTank dataset downloads
    RANDOM_SEED: Random seed for reproducibility (default: 42)
"""

import os
import random
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()

# Configuration constants
DATA_DIR = Path(os.getenv('DATA_DIR', './data'))
CACHE_DIR = Path(os.getenv('CACHE_DIR', './cache'))
PHISHTANK_API_KEY = os.getenv('PHISHTANK_API_KEY', '')
RANDOM_SEED = int(os.getenv('RANDOM_SEED', '42'))

# Create directories if they don't exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def set_seeds(seed: int = None) -> None:
    """Set random seeds for reproducibility across libraries.

    Sets seeds for:
    - Python's random module
    - NumPy (legacy and current APIs)

    Args:
        seed: Random seed value. If None, uses RANDOM_SEED from config.

    Note:
        This function should be called at the start of any pipeline or experiment
        to ensure reproducible results. Individual estimators should also receive
        random_state parameter where available.
    """
    if seed is None:
        seed = RANDOM_SEED

    random.seed(seed)

    # Set NumPy seed (legacy API, needed for compatibility with sklearn/imblearn)
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass  # NumPy not installed yet, skip
