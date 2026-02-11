"""FastAPI application with lifespan events for model loading.

CRITICAL: Model is loaded ONCE at startup via lifespan events,
not per-request. This ensures sub-500ms response times.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from pathlib import Path

from src.models.predict import load_model
from src.models.ensemble import load_ensemble

# Global model storage - loaded once at startup
ml_models = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML model at startup, clean up at shutdown.

    CRITICAL: Model loaded once here, not per-request.
    This ensures sub-500ms response times.
    """
    print("Loading ML models...")

    # Load primary Random Forest model
    model_path = Path("models/rf_pipeline.joblib")
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model not found at {model_path}. "
            "Run training first: python -m src.models.train"
        )
    ml_models["phishing_detector"] = load_model(model_path)
    print(f"Primary model loaded: {type(ml_models['phishing_detector']).__name__}")

    # Load ensemble models (optional - fallback for backward compatibility)
    ensemble_dir = Path("models/ensemble")
    ensemble_loaded = 0

    if ensemble_dir.exists():
        # Load soft voting ensemble
        soft_path = ensemble_dir / "voting_soft.joblib"
        if soft_path.exists():
            try:
                ml_models["voting_soft"] = load_ensemble(soft_path)
                ensemble_loaded += 1
                print(f"Loaded voting_soft ensemble")
            except Exception as e:
                print(f"Warning: Failed to load voting_soft: {e}")

        # Load hard voting ensemble
        hard_path = ensemble_dir / "voting_hard.joblib"
        if hard_path.exists():
            try:
                ml_models["voting_hard"] = load_ensemble(hard_path)
                ensemble_loaded += 1
                print(f"Loaded voting_hard ensemble")
            except Exception as e:
                print(f"Warning: Failed to load voting_hard: {e}")

        # Load stacking ensemble (optional)
        stacking_path = ensemble_dir / "stacking.joblib"
        if stacking_path.exists():
            try:
                ml_models["stacking"] = load_ensemble(stacking_path)
                ensemble_loaded += 1
                print(f"Loaded stacking ensemble")
            except Exception as e:
                print(f"Warning: Failed to load stacking: {e}")
    else:
        print(f"Warning: Ensemble directory not found at {ensemble_dir}")

    total_models = len(ml_models)
    print(f"Total models loaded: {total_models} (1 primary + {ensemble_loaded} ensemble)")

    yield  # Application runs here

    print("Shutting down, clearing models...")
    ml_models.clear()


app = FastAPI(
    title="PhishGuard API",
    description="REST API for URL phishing detection using ensemble of ML classifiers. "
                "Provides single predictions (/predict) and ensemble predictions with "
                "disagreement analysis (/predict/ensemble).",
    version="1.0.0",
    lifespan=lifespan,
)

# Import and include endpoints
from src.api.endpoints import router

app.include_router(router)
