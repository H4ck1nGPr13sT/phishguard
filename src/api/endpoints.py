"""API endpoints for PhishGuard.

Endpoints:
    - GET /: Root endpoint with API information
    - GET /health: Health check with model status
    - POST /predict: URL phishing prediction
    - POST /predict/ensemble: Ensemble prediction with all classifiers
"""

import time
import numpy as np
from fastapi import APIRouter, HTTPException

from src.api.models import (
    URLRequest,
    PredictionResponse,
    HealthResponse,
    ErrorResponse,
    EnsemblePredictionResponse,
    ClassifierResult,
    DisagreementInfo,
)
from src.features.extractors import extract_url_features
from src.api.main import ml_models
from src.models.ensemble import get_individual_predictions
from src.models.disagreement import get_disagreement_summary

router = APIRouter()


@router.get("/", tags=["root"])
def root():
    """Root endpoint with API information."""
    return {
        "service": "PhishGuard API",
        "version": "1.0.0",
        "endpoints": ["/predict", "/predict/ensemble", "/health", "/docs"],
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


@router.post("/predict/ensemble", response_model=EnsemblePredictionResponse, tags=["prediction"])
def predict_ensemble(request: URLRequest):
    """
    Predict phishing using ensemble of 7 classifiers with disagreement detection.

    Returns individual predictions from all classifiers plus ensemble verdict.
    Flags edge cases when classifier disagreement exceeds threshold.

    Requirements addressed:
    - ENS-05: Reports disagreement between classifiers
    - WEB-05: Returns comparison of all classifier results

    NOTE: Using sync 'def' not 'async def' because ML inference
    is CPU-bound, not I/O-bound. FastAPI runs sync functions
    in threadpool automatically.
    """
    start_time = time.time()

    if "voting_soft" not in ml_models:
        raise HTTPException(
            status_code=503,
            detail="Ensemble models not loaded. Run ensemble training first."
        )

    try:
        # Extract features from URL (same as /predict)
        features = extract_url_features(request.url)
        feature_array = np.array([list(features.values())])

        # Get individual predictions from voting ensemble
        individual_preds = get_individual_predictions(ml_models["voting_soft"], feature_array)

        # Get ensemble prediction using soft voting
        ensemble_proba = ml_models["voting_soft"].predict_proba(feature_array)[0]

        # Calculate disagreement
        disagreement_info = get_disagreement_summary(individual_preds)

        processing_time = (time.time() - start_time) * 1000  # Convert to ms

        return EnsemblePredictionResponse(
            url=request.url,
            ensemble_prediction="phishing" if ensemble_proba[1] > 0.5 else "legitimate",
            ensemble_probability=float(ensemble_proba[1]),
            ensemble_confidence=float(max(ensemble_proba)),
            individual_predictions=[
                ClassifierResult(name=name, **pred) for name, pred in individual_preds.items()
            ],
            disagreement=DisagreementInfo(**disagreement_info),
            voting_method="soft",
            processing_time_ms=processing_time
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ensemble prediction failed: {str(e)}")
