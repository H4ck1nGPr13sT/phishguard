"""API endpoints for PhishGuard.

Endpoints:
    - GET /: Root endpoint with API information
    - GET /health: Health check with model status
    - POST /predict: URL phishing prediction
"""

import time
import numpy as np
from fastapi import APIRouter, HTTPException

from src.api.models import (
    URLRequest,
    PredictionResponse,
    HealthResponse,
    ErrorResponse,
)
from src.features.extractors import extract_url_features
from src.api.main import ml_models

router = APIRouter()


@router.get("/", tags=["root"])
def root():
    """Root endpoint with API information."""
    return {
        "service": "PhishGuard API",
        "version": "1.0.0",
        "endpoints": ["/predict", "/health", "/docs"],
    }


@router.get("/health", response_model=HealthResponse, tags=["health"])
def health():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy" if "phishing_detector" in ml_models else "unhealthy",
        model_loaded="phishing_detector" in ml_models,
    )


@router.post("/predict", response_model=PredictionResponse, tags=["prediction"])
def predict(request: URLRequest):
    """
    Predict phishing probability for URL.

    NOTE: Using sync 'def' not 'async def' because ML inference
    is CPU-bound, not I/O-bound. FastAPI runs sync functions
    in threadpool automatically.

    Requirements addressed:
    - INPUT-01: Accepts URL via API
    - ML-08: Returns phishing probability
    """
    start_time = time.time()

    if "phishing_detector" not in ml_models:
        raise HTTPException(
            status_code=503, detail="Model not loaded. Service unavailable."
        )

    try:
        # Extract features from URL
        features = extract_url_features(request.url)
        feature_array = np.array([list(features.values())])

        # Predict with loaded model
        model = ml_models["phishing_detector"]
        proba = model.predict_proba(feature_array)[0]

        processing_time = (time.time() - start_time) * 1000  # Convert to ms

        return PredictionResponse(
            url=request.url,
            phishing_probability=float(proba[1]),  # Class 1 = phishing
            prediction="phishing" if proba[1] > 0.5 else "legitimate",
            confidence=float(max(proba)),
            processing_time_ms=processing_time,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
