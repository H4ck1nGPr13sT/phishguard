"""API endpoints for PhishGuard.

Endpoints:
    - GET /: Root endpoint with API information
    - GET /health: Health check with model status
    - POST /predict: URL phishing prediction
    - POST /predict/ensemble: Ensemble prediction with all classifiers
"""

import time
import numpy as np
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Annotated

from src.api.models import (
    URLRequest,
    PredictionResponse,
    HealthResponse,
    ErrorResponse,
    EnsemblePredictionResponse,
    ClassifierResult,
    DisagreementInfo,
    MultiParadigmResponse,
    FiredRule,
    ParadigmContribution,
    ParadigmContributions,
    ParadigmDisagreementInfo,
    EmailTextRequest,
    SMSRequest,
    EmailSMSResponse,
)
from src.features.extractors import extract_url_features, extract_email_features, extract_sms_features, ContentType
from src.api.main import ml_models
from src.models.ensemble import get_individual_predictions
from src.models.disagreement import get_disagreement_summary

router = APIRouter()


@router.get("/", tags=["root"])
def root():
    """Root endpoint with API information."""
    return {
        "service": "PhishGuard API",
        "version": "3.0.0",  # Updated for Phase 6 - Email/SMS support
        "endpoints": [
            "/predict",
            "/predict/ensemble",
            "/predict/multi-paradigm",
            "/predict/email",
            "/predict/email/file",
            "/predict/sms",
            "/health",
            "/docs"
        ],
    }


@router.get("/health", response_model=HealthResponse, tags=["health"])
def health():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy" if "phishing_detector" in ml_models else "unhealthy",
        model_loaded="phishing_detector" in ml_models,
        email_model_loaded="email_ensemble" in ml_models,
        sms_model_loaded="sms_ensemble" in ml_models,
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


@router.post("/predict/multi-paradigm", response_model=MultiParadigmResponse, tags=["prediction"])
def predict_multi_paradigm(request: URLRequest):
    """
    Predict phishing using all three paradigms: ML ensemble, rule-based, Bayesian.

    This endpoint combines predictions from:
    - ML ensemble: 7 classifiers with weighted soft voting
    - Rule-based: Expert system with 15-20 phishing detection rules
    - Bayesian: GaussianNB probabilistic classifier

    Returns aggregated prediction with paradigm contributions, disagreement
    detection, and list of active rules.

    Requirements addressed:
    - AGG-01: Combines ML ensemble, rules, and Bayesian
    - AGG-02: Detects cross-paradigm disagreements
    - AGG-03: Generates final decision with confidence
    - AGG-04: Shows weighted contributions from each paradigm
    - RULE-07: Returns active rules list with justifications

    NOTE: Using sync 'def' not 'async def' because ML inference
    is CPU-bound, not I/O-bound. FastAPI runs sync functions
    in threadpool automatically.
    """
    start_time = time.time()

    # Check required models are loaded
    required_models = ["voting_soft", "rule_engine", "bayesian", "aggregator"]
    missing = [m for m in required_models if m not in ml_models]
    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"Required models not loaded: {missing}. "
                   f"Run model training scripts first."
        )

    try:
        # Extract features from URL
        features = extract_url_features(request.url)
        feature_array = np.array([list(features.values())])

        # 1. Get ML ensemble prediction
        ensemble = ml_models["voting_soft"]
        ensemble_proba = ensemble.predict_proba(feature_array)[0]
        ml_result = {
            'ensemble_probability': float(ensemble_proba[1]),
            'prediction': 'phishing' if ensemble_proba[1] > 0.5 else 'legitimate'
        }

        # 2. Get rule-based prediction
        # Pass raw_url for keyword matching (Plan 05-01 implements raw_url parameter)
        rule_result = ml_models["rule_engine"].evaluate(features, raw_url=request.url)

        # 3. Get Bayesian prediction
        bayesian_result = ml_models["bayesian"].predict_with_posterior(feature_array)

        # 4. Aggregate all three paradigms
        aggregated = ml_models["aggregator"].aggregate(
            ml_result, rule_result, bayesian_result
        )

        processing_time = (time.time() - start_time) * 1000

        # Build response with proper Pydantic models
        paradigm_contributions = ParadigmContributions(
            ml_ensemble=ParadigmContribution(
                probability=aggregated['paradigm_contributions']['ml_ensemble']['probability'],
                weight=aggregated['paradigm_contributions']['ml_ensemble']['weight'],
                weighted_contribution=aggregated['paradigm_contributions']['ml_ensemble']['weighted_contribution'],
                prediction=aggregated['paradigm_contributions']['ml_ensemble']['prediction']
            ),
            rules=ParadigmContribution(
                probability=aggregated['paradigm_contributions']['rules']['probability'],
                weight=aggregated['paradigm_contributions']['rules']['weight'],
                weighted_contribution=aggregated['paradigm_contributions']['rules']['weighted_contribution'],
                prediction=aggregated['paradigm_contributions']['rules']['prediction']
            ),
            bayesian=ParadigmContribution(
                probability=aggregated['paradigm_contributions']['bayesian']['probability'],
                weight=aggregated['paradigm_contributions']['bayesian']['weight'],
                weighted_contribution=aggregated['paradigm_contributions']['bayesian']['weighted_contribution'],
                prediction=aggregated['paradigm_contributions']['bayesian']['prediction']
            )
        )

        disagreement = ParadigmDisagreementInfo(
            score=aggregated['disagreement']['score'],
            is_edge_case=aggregated['disagreement']['is_edge_case'],
            vote_distribution=aggregated['disagreement']['vote_distribution'],
            probability_variance=aggregated['disagreement']['probability_variance'],
            disagreeing_paradigms=aggregated['disagreement']['disagreeing_paradigms'],
            probability_spread=aggregated['disagreement']['probability_spread']
        )

        active_rules = [
            FiredRule(
                name=rule.get('name', ''),
                description=rule.get('description', ''),
                weight=rule.get('weight', 0.0),
                matched_values=rule.get('matched_values', [])
            )
            for rule in aggregated['active_rules']
        ]

        return MultiParadigmResponse(
            url=request.url,
            final_prediction=aggregated['final_prediction'],
            final_probability=aggregated['final_probability'],
            confidence=aggregated['confidence'],
            paradigm_contributions=paradigm_contributions,
            disagreement=disagreement,
            active_rules=active_rules,
            explanation=aggregated['explanation'],
            processing_time_ms=processing_time
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Multi-paradigm prediction failed: {str(e)}"
        )


@router.post("/predict/email", response_model=EmailSMSResponse, tags=["prediction"])
def predict_email(request: EmailTextRequest):
    """
    Predict phishing probability for raw email text.

    Extracts header features (SPF, DKIM, sender) and text features (NLP).
    Currently uses ensemble model directly (full multi-paradigm integration
    comes after model retraining in Plan 06).

    Requirements addressed:
    - INPUT-02: Accepts raw email/SMS text
    - FEAT-07: Extracts email header features

    NOTE: Using sync 'def' not 'async def' because ML inference
    is CPU-bound, not I/O-bound. FastAPI runs sync functions
    in threadpool automatically.
    """
    start_time = time.time()

    # Verify models loaded - use email_ensemble if available, fallback to voting_soft
    if "email_ensemble" not in ml_models:
        raise HTTPException(
            status_code=503,
            detail="Email model not loaded. Run scripts/train_email_sms_models.py"
        )

    try:
        # Extract features from email text
        # Convert string to bytes for email parser
        raw_bytes = request.raw_email.encode('utf-8')
        features = extract_email_features(raw_bytes)
        feature_array = np.array([list(features.values())])

        # Use email-specific ensemble model
        ensemble = ml_models["email_ensemble"]

        # Get prediction using ensemble model
        proba = ensemble.predict_proba(feature_array)[0]
        phishing_prob = float(proba[1])
        prediction = "phishing" if phishing_prob > 0.5 else "legitimate"
        confidence = float(max(proba))

        processing_time = (time.time() - start_time) * 1000

        # Build explanation
        explanation = f"Email analyzed with {len(features)} features. "
        if confidence > 0.9:
            explanation += f"High confidence {prediction} ({confidence:.1%})."
        elif confidence > 0.7:
            explanation += f"Moderate confidence {prediction} ({confidence:.1%})."
        else:
            explanation += f"Low confidence {prediction} ({confidence:.1%}). Consider manual review."

        return EmailSMSResponse(
            content_type="email",
            final_prediction=prediction,
            final_probability=phishing_prob,
            confidence=confidence,
            feature_count=len(features),
            paradigm_contributions=None,  # Not using multi-paradigm yet
            active_rules=[],
            explanation=explanation,
            processing_time_ms=processing_time
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email prediction failed: {str(e)}")


@router.post("/predict/email/file", response_model=EmailSMSResponse, tags=["prediction"])
async def predict_email_file(
    file: Annotated[UploadFile, File(description="Email file in .eml format")]
):
    """
    Predict phishing probability for uploaded .eml file.

    Accepts .eml file upload, parses email content, extracts features.
    Currently uses ensemble model directly (full multi-paradigm integration
    comes after model retraining in Plan 06).

    Requirements addressed:
    - INPUT-03: Accepts .eml file upload

    NOTE: Using async def for file upload I/O, but ML inference
    runs in threadpool automatically.
    """
    start_time = time.time()

    # Validate file type
    if file.filename and not file.filename.endswith('.eml'):
        raise HTTPException(status_code=400, detail="File must be .eml format")

    # Size limit: 5MB
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")

    # Verify models loaded
    if "email_ensemble" not in ml_models:
        raise HTTPException(
            status_code=503,
            detail="Email model not loaded. Run scripts/train_email_sms_models.py"
        )

    try:
        # Extract features from email bytes
        features = extract_email_features(contents)
        feature_array = np.array([list(features.values())])

        # Use email-specific ensemble model
        ensemble = ml_models["email_ensemble"]

        # Get prediction using ensemble model
        proba = ensemble.predict_proba(feature_array)[0]
        phishing_prob = float(proba[1])
        prediction = "phishing" if phishing_prob > 0.5 else "legitimate"
        confidence = float(max(proba))

        processing_time = (time.time() - start_time) * 1000

        # Build explanation
        explanation = f"Email file analyzed with {len(features)} features. "
        if confidence > 0.9:
            explanation += f"High confidence {prediction} ({confidence:.1%})."
        elif confidence > 0.7:
            explanation += f"Moderate confidence {prediction} ({confidence:.1%})."
        else:
            explanation += f"Low confidence {prediction} ({confidence:.1%}). Consider manual review."

        return EmailSMSResponse(
            content_type="email",
            final_prediction=prediction,
            final_probability=phishing_prob,
            confidence=confidence,
            feature_count=len(features),
            paradigm_contributions=None,  # Not using multi-paradigm yet
            active_rules=[],
            explanation=explanation,
            processing_time_ms=processing_time
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email file prediction failed: {str(e)}")


@router.post("/predict/sms", response_model=EmailSMSResponse, tags=["prediction"])
def predict_sms(request: SMSRequest):
    """
    Predict phishing probability for SMS/chat message.

    Extracts SMS-specific features and NLP text features.
    Currently uses ensemble model directly (full multi-paradigm integration
    comes after model retraining in Plan 06).

    Requirements addressed:
    - INPUT-02: Accepts SMS/chat text

    NOTE: Using sync 'def' not 'async def' because ML inference
    is CPU-bound, not I/O-bound. FastAPI runs sync functions
    in threadpool automatically.
    """
    start_time = time.time()

    # Verify models loaded - use sms_ensemble
    if "sms_ensemble" not in ml_models:
        raise HTTPException(
            status_code=503,
            detail="SMS model not loaded. Run scripts/train_email_sms_models.py"
        )

    try:
        # Extract features from SMS message
        features = extract_sms_features(request.message)
        feature_array = np.array([list(features.values())])

        # Use SMS-specific ensemble model
        ensemble = ml_models["sms_ensemble"]

        # Get prediction using ensemble model
        proba = ensemble.predict_proba(feature_array)[0]
        phishing_prob = float(proba[1])
        prediction = "phishing" if phishing_prob > 0.5 else "legitimate"
        confidence = float(max(proba))

        processing_time = (time.time() - start_time) * 1000

        # Build explanation
        explanation = f"SMS message analyzed with {len(features)} features. "
        if confidence > 0.9:
            explanation += f"High confidence {prediction} ({confidence:.1%})."
        elif confidence > 0.7:
            explanation += f"Moderate confidence {prediction} ({confidence:.1%})."
        else:
            explanation += f"Low confidence {prediction} ({confidence:.1%}). Consider manual review."

        return EmailSMSResponse(
            content_type="sms",
            final_prediction=prediction,
            final_probability=phishing_prob,
            confidence=confidence,
            feature_count=len(features),
            paradigm_contributions=None,  # Not using multi-paradigm yet
            active_rules=[],
            explanation=explanation,
            processing_time_ms=processing_time
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SMS prediction failed: {str(e)}")
