"""PhishTank dataset downloader.

Downloads phishing URL data from PhishTank API with caching support.
PhishTank provides hourly-updated JSON datasets of verified phishing URLs.

API Documentation: https://www.phishtank.com/developer_info.php
"""

import bz2
import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from tqdm import tqdm

from src.config.settings import PHISHTANK_API_KEY, CACHE_DIR

logger = logging.getLogger('phishguard.downloaders.phishtank')


def download_phishtank(
    api_key: Optional[str] = None,
    cache_dir: Optional[Path] = None,
    force_refresh: bool = False
) -> pd.DataFrame:
    """Download PhishTank verified phishing dataset.

    Downloads the latest verified phishing URLs from PhishTank API. Data is
    cached locally and reused if available (unless force_refresh=True).
    On download failure, falls back to cached data if exists.

    Args:
        api_key: PhishTank API key. If None, uses PHISHTANK_API_KEY from config.
            Register at phishtank.com for automated downloads.
        cache_dir: Directory for caching downloaded data. If None, uses CACHE_DIR
            from config.
        force_refresh: If True, always download fresh data even if cache exists.

    Returns:
        DataFrame with columns:
            - url (str): Phishing URL
            - label (int): Always 1 (phishing)
            - timestamp (datetime): Verification timestamp
            - source (str): Always 'phishtank'

    Raises:
        RuntimeError: If download fails and no cached data available

    Example:
        >>> df = download_phishtank()
        >>> print(f"Downloaded {len(df)} phishing URLs")
        >>> print(df[['url', 'timestamp']].head())
    """
    if api_key is None:
        api_key = PHISHTANK_API_KEY
        if not api_key:
            logger.warning("No PhishTank API key provided. Using cached data if available.")

    if cache_dir is None:
        cache_dir = CACHE_DIR

    cache_path = cache_dir / 'phishtank_latest.json'

    # Use cache if exists and not forcing refresh
    if cache_path.exists() and not force_refresh:
        logger.info(f"Using cached PhishTank data from {cache_path}")
        df = pd.read_json(cache_path)
        logger.info(f"Loaded {len(df)} cached PhishTank samples")
        return _standardize_phishtank_format(df)

    # Download fresh data
    if not api_key:
        if cache_path.exists():
            logger.warning("No API key and force_refresh=True. Using stale cache.")
            df = pd.read_json(cache_path)
            return _standardize_phishtank_format(df)
        raise RuntimeError(
            "PhishTank API key required for download. "
            "Set PHISHTANK_API_KEY environment variable."
        )

    url = f"http://data.phishtank.com/data/{api_key}/online-valid.json.bz2"

    try:
        logger.info(f"Downloading PhishTank dataset from API...")
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()

        # Get total size for progress bar
        total_size = int(response.headers.get('content-length', 0))

        # Download with progress bar
        compressed_data = bytearray()
        with tqdm(total=total_size, unit='B', unit_scale=True, desc="PhishTank") as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                compressed_data.extend(chunk)
                pbar.update(len(chunk))

        # Decompress bz2
        logger.info("Decompressing data...")
        json_data = bz2.decompress(compressed_data)

        # Parse JSON
        df = pd.read_json(json_data)

        # Cache for future use
        df.to_json(cache_path)
        logger.info(f"Cached PhishTank data to {cache_path}")
        logger.info(f"Downloaded {len(df)} PhishTank samples")

        return _standardize_phishtank_format(df)

    except requests.RequestException as e:
        logger.error(f"PhishTank download failed: {e}")

        # Fall back to cache if available
        if cache_path.exists():
            logger.warning("Falling back to cached PhishTank data")
            df = pd.read_json(cache_path)
            logger.info(f"Loaded {len(df)} cached samples (fallback)")
            return _standardize_phishtank_format(df)

        raise RuntimeError(f"PhishTank download failed and no cache available: {e}")

    except Exception as e:
        logger.error(f"Unexpected error processing PhishTank data: {e}")
        raise


def _standardize_phishtank_format(df: pd.DataFrame) -> pd.DataFrame:
    """Convert PhishTank raw format to standardized format.

    Args:
        df: Raw PhishTank DataFrame

    Returns:
        Standardized DataFrame with columns: url, label, timestamp, source
    """
    # PhishTank JSON structure: [{url, phish_id, phish_detail_url, submission_time,
    # verified, verified_at, online, target, ...}, ...]

    standardized = pd.DataFrame({
        'url': df['url'],
        'label': 1,  # All PhishTank entries are phishing
        'timestamp': pd.to_datetime(df['verification_time'], errors='coerce'),
        'source': 'phishtank'
    })

    return standardized
