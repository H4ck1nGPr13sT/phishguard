"""Dataset downloaders for multiple phishing data sources."""

from src.data.downloaders.phishtank import download_phishtank
from src.data.downloaders.uci_ml import download_uci_phishing
from src.data.downloaders.nazario import parse_nazario_corpus

__all__ = [
    'download_phishtank',
    'download_uci_phishing',
    'parse_nazario_corpus',
]
