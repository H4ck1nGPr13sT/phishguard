"""FastAPI application with lifespan events for model loading.

CRITICAL: Model is loaded ONCE at startup via lifespan events,
not per-request. This ensures sub-500ms response times.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from pathlib import Path

from src.models.predict import load_model

# Global model storage - loaded once at startup
ml_models = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML model at startup, clean up at shutdown.

    CRITICAL: Model loaded once here, not per-request.
    This ensures sub-500ms response times.
    """
    print("Loading ML model...")
    model_path = Path("models/rf_pipeline.joblib")

    if not model_path.exists():
        raise FileNotFoundError(
            f"Model not found at {model_path}. "
            "Run training first: python -m src.models.train"
        )

    ml_models["phishing_detector"] = load_model(model_path)
    print(f"Model loaded successfully: {type(ml_models['phishing_detector']).__name__}")

    yield  # Application runs here

    print("Shutting down, clearing models...")
    ml_models.clear()


app = FastAPI(
    title="PhishGuard API",
    description="REST API for URL phishing detection using Random Forest classifier",
    version="1.0.0",
    lifespan=lifespan,
)

# Import and include endpoints
from src.api.endpoints import router

app.include_router(router)
