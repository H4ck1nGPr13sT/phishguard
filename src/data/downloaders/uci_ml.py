"""UCI ML Repository Phishing Websites dataset downloader.

Downloads and parses the UCI ML Phishing Websites dataset which contains
pre-extracted URL features rather than raw URLs.

Dataset: https://archive.ics.uci.edu/ml/datasets/Phishing+Websites
Citation: Mohammad, R., Thabtah, F., & McCluskey, L. (2014)
"""

import io
import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from scipy.io import arff

from src.config.settings import CACHE_DIR

logger = logging.getLogger('phishguard.downloaders.uci_ml')


def download_uci_phishing(
    cache_dir: Optional[Path] = None,
    force_refresh: bool = False
) -> pd.DataFrame:
    """Download UCI ML Phishing Websites dataset.

    Downloads ARFF-format dataset containing 11,055 samples with 31 URL-based
    features (no raw URLs, only derived features like IP address presence,
    URL length, etc.). Data is cached locally for reuse.

    Note: This dataset contains features only, not raw URLs. It's useful for
    training feature-based classifiers, but cannot be used for URL extraction
    or content analysis.

    Args:
        cache_dir: Directory for caching downloaded data. If None, uses CACHE_DIR
            from config.
        force_refresh: If True, always download fresh data even if cache exists.

    Returns:
        DataFrame with columns:
            - Feature columns (having_IP, URL_Length, etc.)
            - label (int): 0 = legitimate, 1 = phishing
            - source (str): Always 'uci_ml'
            - timestamp: Always None (dataset has no temporal info)

    Raises:
        RuntimeError: If download fails and no cached data available

    Example:
        >>> df = download_uci_phishing()
        >>> print(f"Downloaded {len(df)} samples")
        >>> print(df['label'].value_counts())
    """
    if cache_dir is None:
        cache_dir = CACHE_DIR

    cache_path = cache_dir / 'uci_phishing.csv'

    # Use cache if exists and not forcing refresh
    if cache_path.exists() and not force_refresh:
        logger.info(f"Using cached UCI ML data from {cache_path}")
        df = pd.read_csv(cache_path)
        logger.info(f"Loaded {len(df)} cached UCI ML samples")
        return df

    # Download fresh data
    # Note: UCI URLs can change. This is the current direct download link.
    url = "https://archive.ics.uci.edu/ml/machine-learning-databases/00327/Training%20Dataset.arff"

    try:
        logger.info("Downloading UCI ML Phishing dataset...")
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        logger.info("Parsing ARFF format...")
        # Parse ARFF file - scipy.io.arff expects text mode
        # Convert bytes to text
        arff_text = response.content.decode('utf-8')
        data, meta = arff.loadarff(io.StringIO(arff_text))

        # Convert to DataFrame
        df = pd.DataFrame(data)

        # Convert byte strings to regular strings for categorical columns
        for col in df.columns:
            if df[col].dtype == object:
                # Check if column contains byte strings
                try:
                    # Try to decode first non-null value
                    first_val = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
                    if isinstance(first_val, bytes):
                        df[col] = df[col].apply(lambda x: x.decode('utf-8') if isinstance(x, bytes) else x)
                except (AttributeError, IndexError):
                    pass  # Not a byte string column or empty

        # Standardize label column
        # UCI dataset uses 'Result' column with values -1 (legitimate) and 1 (phishing)
        # Convert to 0/1 binary labels
        if 'Result' in df.columns:
            # Handle both string and numeric representations
            result_col = df['Result'].astype(str).str.replace("b'", "").str.replace("'", "")
            df['label'] = (result_col == '1').astype(int)
            df = df.drop(columns=['Result'])
        else:
            logger.warning("'Result' column not found in UCI dataset. Check dataset format.")
            # Try to infer label column
            if 'class' in df.columns:
                class_col = df['class'].astype(str).str.replace("b'", "").str.replace("'", "")
                df['label'] = (class_col == '1').astype(int)
                df = df.drop(columns=['class'])
            else:
                raise ValueError("Cannot find label column in UCI dataset")

        # Add metadata columns
        df['source'] = 'uci_ml'
        df['timestamp'] = None  # UCI dataset has no timestamps
        df['url'] = ''  # UCI dataset has features only, no raw URLs

        # Cache processed data
        df.to_csv(cache_path, index=False)
        logger.info(f"Cached UCI ML data to {cache_path}")
        logger.info(f"Downloaded {len(df)} UCI ML samples")

        return df

    except requests.RequestException as e:
        logger.error(f"UCI ML download failed: {e}")

        # Fall back to cache if available
        if cache_path.exists():
            logger.warning("Falling back to cached UCI ML data")
            df = pd.read_csv(cache_path)
            logger.info(f"Loaded {len(df)} cached samples (fallback)")
            return df

        raise RuntimeError(f"UCI ML download failed and no cache available: {e}")

    except Exception as e:
        logger.error(f"Unexpected error processing UCI ML data: {e}")
        raise
