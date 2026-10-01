"""API endpoints for PhishGuard.

Endpoints:
    - GET /api/info: API information (GET / serves the HTML web UI, see src/api/web.py)
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
    FeatureContribution,
    ShapExplanation,
    ExplainResponse,
)
from src.features.extractors import extract_url_features, extract_email_features, extract_sms_features, ContentType
from src.features.image_features import load_and_ocr, extract_visual_features
from src.api.main import ml_models
from src.api.inference import predict_url_multi, predict_email_text, predict_sms_text, ModelsNotLoaded
from src.models.ensemble import get_individual_predictions
from src.models.disagreement import get_disagreement_summary
from src.paradigms.aggregation.disagreement import get_disagreement_explanation
from src.explainability.shap_explain import shap_top_features

router = APIRouter()


def _visual_signal_probability(visual_dict: dict) -> float:
    """Map the numeric visual_* feature dict to a [0,1] phishing-likelihood
    score for use as the aggregator's third (bayesian slot) paradigm input.

    Weighting (TUNABLE, documented per RESEARCH.md Pitfall 5 — not
    empirically validated against a labeled phishing-image dataset yet):
        - visual_brand_similarity_flag dominates (0.7 weight): an image that
          perceptually matches a known-phished brand reference is the
          strongest available visual signal.
        - visual_edge_density and visual_color_concentration each nudge the
          score (0.15 weight each): form/button-heavy, narrow-palette UIs
          are weakly correlated with login-clone phishing pages.
        - visual_rect_element_count is intentionally NOT weighted directly
          (unbounded count, would need normalization); it remains available
          in the response as a diagnostic via feature_count only.

    Args:
        visual_dict: Output of `extract_visual_features` — exactly
            `_VISUAL_FEATURE_KEYS`.

    Returns:
        A float in [0, 1].
    """
    brand_flag = visual_dict.get("visual_brand_similarity_flag", 0.0)
    edge_density = min(max(visual_dict.get("visual_edge_density", 0.0), 0.0), 1.0)
    color_concentration = min(
        max(visual_dict.get("visual_color_concentration", 0.0), 0.0), 1.0
    )

    score = (
        0.7 * brand_flag
        + 0.15 * edge_density
        + 0.15 * color_concentration
    )
    return float(min(max(score, 0.0), 1.0))


@router.get(
    "/api/info",
    tags=["root"],
    summary="Get API service info",
    description=(
        "Returns the service name, version, and the list of available "
        "endpoints. GET / serves the HTML web UI instead (see src/api/web.py)."
    ),
    response_description="Service metadata and endpoint list",
)
def api_info():
    """API information endpoint (moved from GET / in Phase 8 — GET /
    now serves the HTML web UI; see src/api/web.py)."""
    return {
        "service": "PhishGuard API",
        "version": "4.0.0",  # Updated for Phase 7 - Image/OCR support
        "endpoints": [
            "/predict",
            "/predict/ensemble",
            "/predict/multi-paradigm",
            "/predict/email",
            "/predict/email/file",
            "/predict/sms",
            "/predict/image",
            "/explain",
            "/health",
            "/docs"
        ],
    }


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Check service and model-loading health",
    description=(
        "Reports overall service status plus which models are currently "
        "loaded (primary URL classifier, email ensemble, SMS ensemble, OCR "
        "backend). Returns status=unhealthy when the primary URL model is "
        "not loaded."
    ),
    response_description="Health status and per-model loaded flags",
)
def health():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy" if "phishing_detector" in ml_models else "unhealthy",
        model_loaded="phishing_detector" in ml_models,
        email_model_loaded="email_ensemble" in ml_models,
        sms_model_loaded="sms_ensemble" in ml_models,
        ocr_backend_loaded="ocr_backend" in ml_models,
    )


@router.post(
    "/predict",
    response_model=PredictionResponse,
    tags=["prediction"],
    summary="Fast single-model phishing prediction for a URL",
    description=(
        "Extracts the 30 URL features and runs the primary (GA-optimized "
        "Random Forest) classifier for a low-latency phishing probability. "
        "For a richer verdict combining 7 classifiers, rules, and a "
        "Bayesian posterior, use /predict/multi-paradigm instead."
    ),
    response_description="Phishing probability, binary verdict, confidence, and processing time",
)
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


@router.post(
    "/predict/ensemble",
    response_model=EnsemblePredictionResponse,
    tags=["prediction"],
    summary="Phishing prediction from all 7 ML classifiers with disagreement detection",
    description=(
        "Runs the URL through all 7 classifiers (RF, SVM, MLP, XGBoost, "
        "LogReg, NaiveBayes, DecisionTree) in the voting ensemble and "
        "returns each individual verdict plus the soft-voting ensemble "
        "result. Flags edge cases where classifier disagreement exceeds "
        "the configured threshold."
    ),
    response_description="Ensemble verdict, per-classifier breakdown, and disagreement info",
)
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


@router.post(
    "/predict/multi-paradigm",
    response_model=MultiParadigmResponse,
    tags=["prediction"],
    summary="Full multi-paradigm phishing verdict for a URL",
    description=(
        "Runs the URL through all three paradigms (7-classifier ML "
        "ensemble, weighted rule engine, Bayesian posterior) and returns "
        "an aggregated verdict with a cross-paradigm disagreement score. "
        "This is the endpoint that demonstrates the thesis's core value: "
        "disagreement between paradigms as an additional diagnostic "
        "signal, alongside per-paradigm weighted contributions and the "
        "list of fired rules."
    ),
    response_description="Aggregated verdict with per-paradigm contributions, fired rules, and disagreement info",
)
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
        # Shared helper (also used by the batch runner)
        aggregated = predict_url_multi(request.url)

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


@router.post(
    "/explain",
    response_model=ExplainResponse,
    tags=["explainability"],
    summary="Consolidated explainability report for a URL verdict",
    description=(
        "Runs SHAP TreeExplainer (URL-only, RF) and consolidates it with "
        "the already-computed fired rules, all 7 individual ML "
        "predictions, and cross-paradigm disagreement into one response. "
        "Slower than /predict/multi-paradigm (SHAP is never run on the "
        "fast prediction path by design) — use this endpoint only when "
        "an explanation, not just a verdict, is needed. Demonstrates "
        "cross-paradigm disagreement as an additional diagnostic signal "
        "alongside feature-level SHAP attribution."
    ),
    response_description="SHAP top features, per-classifier predictions, fired rules, and disagreement explanation",
)
def explain(request: URLRequest):
    """
    Consolidated on-demand explainability endpoint (Phase 9).

    Separate from /predict/multi-paradigm (SHAP is slow and must never run
    on the fast prediction path — locked decision). Runs SHAP TreeExplainer
    URL-only (EXPL-02) and consolidates it with the already-computed
    EXPL-01/03/04/05 signals (fired rules, 7 individual ML predictions,
    cross-paradigm disagreement, natural-language verdict) into ONE
    response — surfacing/enriching existing aggregator/ensemble/
    disagreement output rather than reinventing it.

    Requirements addressed:
    - EXPL-02: SHAP feature importance for the ML decision (URL-only, RF)
    - EXPL-03: All-classifier comparison data (7 individual predictions)
    - EXPL-04: Fuller cross-paradigm disagreement explanation
    - EXPL-05: NL verdict enriched with the top SHAP feature

    NOTE: Using sync 'def' not 'async def' because ML/SHAP inference is
    CPU-bound, not I/O-bound. FastAPI runs sync functions in threadpool
    automatically.
    """
    start_time = time.time()

    required_models = ["phishing_detector", "voting_soft", "rule_engine", "bayesian", "aggregator"]
    missing = [m for m in required_models if m not in ml_models]
    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"Required models not loaded: {missing}. "
                   f"Run model training scripts first."
        )

    if "shap_explainer" not in ml_models:
        raise HTTPException(
            status_code=503,
            detail="SHAP explainer not available. Install shap and restart."
        )

    try:
        aggregated = predict_url_multi(request.url)
    except ModelsNotLoaded as e:
        raise HTTPException(status_code=503, detail=str(e))

    try:
        # EXPL-03: all 7 individual classifier predictions.
        features = extract_url_features(request.url)
        feature_array = np.array([list(features.values())])
        individual_preds = get_individual_predictions(ml_models["voting_soft"], feature_array)
        individual_predictions = [
            ClassifierResult(name=name, **pred) for name, pred in individual_preds.items()
        ]

        # EXPL-02: SHAP top-10 (URL-only, RF). An unexpected SHAP failure
        # here degrades to available=False + a note rather than a 500 — a
        # missing explainer entirely was already 503'd above.
        try:
            top_features = shap_top_features(request.url, top_n=10)
            shap_block = ShapExplanation(
                available=True,
                content_type="url",
                model="rf",
                top_features=[FeatureContribution(**t) for t in top_features],
                note="SHAP importance is URL-only for v1 (representative RF "
                     "model); values are relative contributions in "
                     "standardized-feature space.",
            )
        except Exception as e:
            top_features = []
            shap_block = ShapExplanation(
                available=False,
                content_type="url",
                model="rf",
                top_features=[],
                note=f"SHAP computation failed: {str(e)}",
            )

        # EXPL-04: fuller per-paradigm disagreement text (currently unused
        # by /predict/multi-paradigm).
        disagreement_explanation = get_disagreement_explanation(aggregated["disagreement"])

        # EXPL-05: NL verdict enriched with the top SHAP feature.
        explanation = aggregated["explanation"]
        if top_features:
            top_feature = top_features[0]
            explanation += (
                f" Top contributing feature: {top_feature['feature']} "
                f"(contribution {top_feature['shap_value']:+.4f})."
            )

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

        processing_time = (time.time() - start_time) * 1000

        return ExplainResponse(
            url=request.url,
            final_prediction=aggregated['final_prediction'],
            final_probability=aggregated['final_probability'],
            confidence=aggregated['confidence'],
            individual_predictions=individual_predictions,
            paradigm_contributions=paradigm_contributions,
            shap=shap_block,
            active_rules=active_rules,
            disagreement=disagreement,
            disagreement_explanation=disagreement_explanation,
            explanation=explanation,
            processing_time_ms=processing_time
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Explain failed: {str(e)}")


@router.post(
    "/predict/email",
    response_model=EmailSMSResponse,
    tags=["prediction"],
    summary="Phishing prediction for raw email text",
    description=(
        "Extracts header features (SPF/DKIM/sender) and NLP text features "
        "from a raw email body/headers string, then classifies with the "
        "trained email ensemble."
    ),
    response_description="Phishing verdict, probability, confidence, and explanation for the email text",
)
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
        result = predict_email_text(request.raw_email)
        processing_time = (time.time() - start_time) * 1000

        return EmailSMSResponse(
            content_type="email",
            final_prediction=result["final_prediction"],
            final_probability=result["final_probability"],
            confidence=result["confidence"],
            feature_count=result["feature_count"],
            paradigm_contributions=None,  # Not using multi-paradigm yet
            active_rules=[],
            explanation=result["explanation"],
            processing_time_ms=processing_time
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email prediction failed: {str(e)}")


@router.post(
    "/predict/email/file",
    response_model=EmailSMSResponse,
    tags=["prediction"],
    summary="Phishing prediction for an uploaded .eml email file",
    description=(
        "Accepts a .eml file upload (max 5MB), parses the email, extracts "
        "header and text features, and classifies with the trained email "
        "ensemble."
    ),
    response_description="Phishing verdict, probability, confidence, and explanation for the uploaded email",
)
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


@router.post(
    "/predict/sms",
    response_model=EmailSMSResponse,
    tags=["prediction"],
    summary="Phishing prediction for an SMS/chat message",
    description=(
        "Extracts SMS-specific features (shortened URLs, call-to-action "
        "phrasing, segment count, etc.) and NLP text features, then "
        "classifies with the trained SMS ensemble."
    ),
    response_description="Phishing verdict, probability, confidence, and explanation for the SMS text",
)
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
        result = predict_sms_text(request.message)
        processing_time = (time.time() - start_time) * 1000

        return EmailSMSResponse(
            content_type="sms",
            final_prediction=result["final_prediction"],
            final_probability=result["final_probability"],
            confidence=result["confidence"],
            feature_count=result["feature_count"],
            paradigm_contributions=None,  # Not using multi-paradigm yet
            active_rules=[],
            explanation=result["explanation"],
            processing_time_ms=processing_time
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SMS prediction failed: {str(e)}")


@router.post(
    "/predict/image",
    response_model=EmailSMSResponse,
    tags=["prediction"],
    summary="Phishing prediction for an uploaded screenshot/photo (OCR + visual)",
    description=(
        "Accepts a PNG/JPG upload (max 8MB), runs OCR once to extract "
        "text, feeds the OCR text into the existing email/text model, "
        "runs rule-engine keyword matching against the OCR text, and "
        "computes a perceptual-hash brand-similarity/layout visual "
        "signal. All three signals are combined via the existing "
        "multi-paradigm aggregator for a single verdict."
    ),
    response_description="Phishing verdict with visual brand-similarity info plus the usual paradigm contributions",
)
async def predict_image(
    file: Annotated[UploadFile, File(description="Image file (.png/.jpg/.jpeg)")]
):
    """
    Predict phishing probability for an uploaded image (screenshot/photo).

    Validates the upload (extension allowlist + 8MB size cap) BEFORE any
    decode, runs OCR exactly once (`load_and_ocr`), feeds the OCR text into
    the EXISTING Phase 6 email/text model on its trained schema (via
    `extract_email_features(b"\\n" + ocr_text)` — the leading blank line
    keeps colon-containing OCR lines, e.g. "Password: ...", in the email
    BODY instead of being mis-parsed as RFC-822 headers), runs the rule
    engine's keyword matching against the OCR text (`raw_url=ocr_text`),
    and computes a visual brand-similarity/layout signal. All three signals
    are combined via the EXISTING `MultiParadigmAggregator` — no new
    aggregation logic and no new trained image model (locked design,
    BLOCKER 3): OCR-text fills the ml slot, rule keyword-matching fills the
    rules slot, and the visual signal fills the third (bayesian) slot.

    Requirements addressed:
    - INPUT-04: Accepts PNG/JPG/screenshot upload
    - INPUT-06: OCR-derived text analysis
    - INPUT-07: Visual/layout analysis
    - SC5 (ROADMAP): Combines OCR text + visual analysis into final verdict

    NOTE: Uploaded bytes are processed entirely in-memory (io.BytesIO
    inside `load_and_ocr`) and are NEVER written to disk (ASVS V12).

    NOTE ON LATENCY: This is a documented exception to the project's
    sub-500ms sync-endpoint contract — OCR inference is inherently slower
    than the numeric-feature paradigms used elsewhere. The EasyOCR reader
    is warmed ONCE at FastAPI lifespan startup (see src/api/main.py) so
    per-request latency reflects only inference time, not model load time.
    """
    start_time = time.time()

    # 1. Extension allowlist — reject BEFORE any read/decode (T-07-10).
    filename = (file.filename or "").lower()
    if not filename.endswith((".png", ".jpg", ".jpeg")):
        raise HTTPException(
            status_code=400,
            detail="File must be .png, .jpg, or .jpeg format",
        )

    # 2. Size cap — reject BEFORE decode, first line of DoS defense (T-07-08).
    contents = await file.read()
    if len(contents) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 8MB)")

    # 3. Verify required models are loaded.
    required_models = ["ocr_backend", "email_ensemble", "rule_engine", "aggregator"]
    missing = [m for m in required_models if m not in ml_models]
    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"Required models not loaded: {missing}.",
        )

    try:
        # 4. Single OCR pass (BLOCKER 3) — load_and_ocr validates in-memory
        # (decompression-bomb guard, structural verify(), never touches
        # disk) and OCRs exactly once. A ValueError here means the bytes
        # were not a valid/decodable image, or exceeded the pixel ceiling.
        try:
            image, ocr_text = load_and_ocr(contents, ml_models["ocr_backend"])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid image")

        # 5. ML text signal — reuse the EXISTING Phase 6 email/text model on
        # its trained schema (BLOCKER 3). The leading b"\n" forces the
        # entire OCR text to be parsed as the email BODY (not headers), so
        # colon-containing OCR lines like "Password: ..." are preserved.
        # OCR is NOT re-run here — ocr_text came from step 4 above.
        email_features = extract_email_features(b"\n" + ocr_text.encode("utf-8"))
        feature_array = np.array([list(email_features.values())])
        ensemble = ml_models["email_ensemble"]
        text_proba = ensemble.predict_proba(feature_array)[0]
        text_prob = float(text_proba[1])
        ml_result = {
            "ensemble_probability": text_prob,
            "prediction": "phishing" if text_prob > 0.5 else "legitimate",
        }

        # 6. Visual signal — perceptual-hash brand similarity + layout/color
        # heuristics (degrades to defaults if cv2/imagehash absent).
        visual_dict, visual_brand = extract_visual_features(image)
        visual_prob = _visual_signal_probability(visual_dict)

        # 7. Rule-based signal — keyword matching against the OCR text via
        # raw_url. URL-only feature_check/domain_match rules simply do not
        # fire since those features are absent from email_features (treated
        # as 0). Defensive wrap: a non-URL feature dict must never 500 here.
        try:
            rule_result = ml_models["rule_engine"].evaluate(
                email_features, raw_url=ocr_text
            )
        except Exception:
            rule_result = {
                "score": 0.0,
                "prediction": "legitimate",
                "confidence": 0.5,
                "fired_rules": [],
                "rule_count": 0,
                "max_possible_score": 0.0,
            }

        # Visual analysis occupies the third paradigm slot (bayesian) — this
        # is precisely how OCR-text + visual are COMBINED for the final
        # verdict (SC5), while reusing the existing aggregator unmodified.
        bayesian_result = {
            "posterior_phishing": visual_prob,
            "prediction": "phishing" if visual_prob > 0.5 else "legitimate",
        }

        # 8. Aggregate all three paradigm slots via the EXISTING aggregator.
        aggregated = ml_models["aggregator"].aggregate(
            ml_result, rule_result, bayesian_result
        )

        processing_time = (time.time() - start_time) * 1000

        paradigm_contributions = ParadigmContributions(
            ml_ensemble=ParadigmContribution(
                probability=aggregated["paradigm_contributions"]["ml_ensemble"]["probability"],
                weight=aggregated["paradigm_contributions"]["ml_ensemble"]["weight"],
                weighted_contribution=aggregated["paradigm_contributions"]["ml_ensemble"]["weighted_contribution"],
                prediction=aggregated["paradigm_contributions"]["ml_ensemble"]["prediction"],
            ),
            rules=ParadigmContribution(
                probability=aggregated["paradigm_contributions"]["rules"]["probability"],
                weight=aggregated["paradigm_contributions"]["rules"]["weight"],
                weighted_contribution=aggregated["paradigm_contributions"]["rules"]["weighted_contribution"],
                prediction=aggregated["paradigm_contributions"]["rules"]["prediction"],
            ),
            bayesian=ParadigmContribution(
                probability=aggregated["paradigm_contributions"]["bayesian"]["probability"],
                weight=aggregated["paradigm_contributions"]["bayesian"]["weight"],
                weighted_contribution=aggregated["paradigm_contributions"]["bayesian"]["weighted_contribution"],
                prediction=aggregated["paradigm_contributions"]["bayesian"]["prediction"],
            ),
        )

        active_rules = [
            FiredRule(
                name=rule.get("name", ""),
                description=rule.get("description", ""),
                weight=rule.get("weight", 0.0),
                matched_values=rule.get("matched_values", []),
            )
            for rule in aggregated["active_rules"]
        ]

        return EmailSMSResponse(
            content_type="image",
            final_prediction=aggregated["final_prediction"],
            final_probability=aggregated["final_probability"],
            confidence=aggregated["confidence"],
            feature_count=len(email_features) + len(visual_dict),
            paradigm_contributions=paradigm_contributions,
            active_rules=active_rules,
            explanation=aggregated["explanation"],
            processing_time_ms=processing_time,
            visual_closest_brand=visual_brand,
            visual_hash_distance=visual_dict["visual_hash_distance"],
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions (400/503 above)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image prediction failed: {str(e)}")
