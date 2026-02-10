"""API module for PhishGuard REST API.

Exports:
    - URLRequest, PredictionResponse, ErrorResponse, HealthResponse: Pydantic models
    - app: FastAPI application instance (imported from main.py when available)
"""

from src.api.models import (
    URLRequest,
    PredictionResponse,
    ErrorResponse,
    HealthResponse,
)

# Import app only if main.py exists (lazy import to avoid circular dependency)
try:
    from src.api.main import app
    __all__ = [
        "URLRequest",
        "PredictionResponse",
        "ErrorResponse",
        "HealthResponse",
        "app",
    ]
except ImportError:
    # main.py not created yet
    __all__ = [
        "URLRequest",
        "PredictionResponse",
        "ErrorResponse",
        "HealthResponse",
    ]
