"""Dataset downloaders for multiple phishing data sources."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from src.data.downloaders.phishtank import download_phishtank
from src.data.downloaders.uci_ml import download_uci_phishing
from src.data.downloaders.nazario import parse_nazario_corpus

__all__ = [
    'download_phishtank',
    'download_uci_phishing',
    'parse_nazario_corpus',
    'download_all_sources',
]

logger = logging.getLogger('phishguard.downloaders')


def download_all_sources(
    phishtank_api_key: Optional[str] = None,
    nazario_path: Optional[Path] = None,
    cache_dir: Optional[Path] = None,
    force_refresh: bool = False
) -> Dict[str, Dict[str, Any]]:
    """Download data from all available sources.

    Convenience function that attempts to download from PhishTank, UCI ML, and
    Nazario corpus. Logs success/failure for each source and returns results.

    Args:
        phishtank_api_key: PhishTank API key (optional if cached data exists)
        nazario_path: Path to Nazario mbox file (optional, skipped if None)
        cache_dir: Cache directory for all downloads
        force_refresh: Force fresh downloads even if cached

    Returns:
        Dictionary mapping source name to result dict:
        {
            'source_name': {
                'status': 'success' | 'failed',
                'samples': int,  # Number of samples (if success)
                'data': DataFrame,  # Downloaded data (if success)
                'error': str  # Error message (if failed)
            }
        }

    Example:
        >>> results = download_all_sources(
        ...     phishtank_api_key='your_key',
        ...     nazario_path=Path('/data/nazario.mbox')
        ... )
        >>> for source, result in results.items():
        ...     if result['status'] == 'success':
        ...         print(f"{source}: {result['samples']} samples")
        ...     else:
        ...         print(f"{source}: FAILED - {result['error']}")
    """
    results = {}

    # Try PhishTank
    logger.info("Downloading from PhishTank...")
    try:
        df = download_phishtank(
            api_key=phishtank_api_key,
            cache_dir=cache_dir,
            force_refresh=force_refresh
        )
        results['phishtank'] = {
            'status': 'success',
            'samples': len(df),
            'data': df
        }
        logger.info(f"PhishTank: Downloaded {len(df)} samples")
    except Exception as e:
        results['phishtank'] = {
            'status': 'failed',
            'error': str(e)
        }
        logger.error(f"PhishTank: Download failed: {e}")

    # Try UCI ML
    logger.info("Downloading from UCI ML Repository...")
    try:
        df = download_uci_phishing(
            cache_dir=cache_dir,
            force_refresh=force_refresh
        )
        results['uci_ml'] = {
            'status': 'success',
            'samples': len(df),
            'data': df
        }
        logger.info(f"UCI ML: Downloaded {len(df)} samples")
    except Exception as e:
        results['uci_ml'] = {
            'status': 'failed',
            'error': str(e)
        }
        logger.error(f"UCI ML: Download failed: {e}")

    # Try Nazario (if path provided)
    if nazario_path:
        logger.info("Parsing Nazario corpus...")
        try:
            df = parse_nazario_corpus(nazario_path)
            results['nazario'] = {
                'status': 'success',
                'samples': len(df),
                'data': df
            }
            logger.info(f"Nazario: Parsed {len(df)} samples")
        except Exception as e:
            results['nazario'] = {
                'status': 'failed',
                'error': str(e)
            }
            logger.error(f"Nazario: Parsing failed: {e}")
    else:
        logger.info("Nazario: Skipped (no mbox path provided)")
        results['nazario'] = {
            'status': 'skipped',
            'error': 'No mbox path provided'
        }

    # Summary
    succeeded = [name for name, res in results.items() if res['status'] == 'success']
    failed = [name for name, res in results.items() if res['status'] == 'failed']

    logger.info(
        f"Download summary: {len(succeeded)} succeeded "
        f"({', '.join(succeeded) if succeeded else 'none'}), "
        f"{len(failed)} failed "
        f"({', '.join(failed) if failed else 'none'})"
    )

    return results
