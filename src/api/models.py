"""Pydantic models for API request/response validation.

Models:
    - URLRequest: Validates incoming URL for prediction
    - PredictionResponse: Structured prediction result
    - HealthResponse: Health check status
    - ErrorResponse: Error details
    - ClassifierResult: Individual classifier prediction
    - DisagreementInfo: Disagreement analysis details
    - EnsemblePredictionResponse: Ensemble prediction with all classifiers
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, List


class URLRequest(BaseModel):
    """Request model for URL prediction."""

    url: str = Field(
        ...,
        description="URL to analyze for phishing detection",
        examples=["https://example.com", "http://suspicious-site.tk/login"],
    )

    @field_validator("url")
    def validate_url_format(cls, v):
        """Ensure URL has valid format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        if len(v) < 10:
            raise ValueError("URL too short (minimum 10 characters)")
        if len(v) > 2048:
            raise ValueError("URL too long (maximum 2048 characters)")
        return v


class PredictionResponse(BaseModel):
    """Response model for prediction results."""

    url: str
    phishing_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Probability that URL is phishing (0.0-1.0)",
    )
    prediction: str = Field(
        ..., description="Binary prediction: 'phishing' or 'legitimate'"
    )
    confidence: float = Field(
        ...,
        ge=0.5,
        le=1.0,
        description="Confidence of prediction (max probability)",
    )
    processing_time_ms: float = Field(
        ..., description="Time taken to process request in milliseconds"
    )


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    model_loaded: bool
    email_model_loaded: bool = False
    sms_model_loaded: bool = False
    ocr_backend_loaded: bool = False
    version: str = "3.0.0"


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    detail: str
    url: Optional[str] = None


class ClassifierResult(BaseModel):
    """Individual classifier prediction result."""

    name: str = Field(..., description="Classifier name (rf, svm, mlp, etc.)")
    phishing_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Probability that URL is phishing (0.0-1.0)",
    )
    prediction: Literal["phishing", "legitimate"] = Field(
        ..., description="Binary prediction"
    )
    confidence: float = Field(
        ...,
        ge=0.5,
        le=1.0,
        description="Confidence of prediction (max probability)",
    )


class DisagreementInfo(BaseModel):
    """Disagreement analysis between classifiers."""

    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized entropy 0-1 (0=agreement, 1=disagreement)",
    )
    is_edge_case: bool = Field(
        ..., description="True if disagreement exceeds threshold (0.7)"
    )
    vote_distribution: dict = Field(
        ..., description="Vote counts: {'phishing': N, 'legitimate': M}"
    )
    agreeing_classifiers: list[str] = Field(
        ..., description="Classifiers agreeing with majority"
    )
    dissenting_classifiers: list[str] = Field(
        ..., description="Classifiers disagreeing with majority"
    )


class EnsemblePredictionResponse(BaseModel):
    """Response model for ensemble prediction with individual classifier results."""

    url: str
    ensemble_prediction: str = Field(
        ..., description="Ensemble prediction: 'phishing' or 'legitimate'"
    )
    ensemble_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Soft voting probability for phishing",
    )
    ensemble_confidence: float = Field(
        ...,
        ge=0.5,
        le=1.0,
        description="Confidence of ensemble prediction",
    )
    individual_predictions: list[ClassifierResult] = Field(
        ..., description="Predictions from all 7 classifiers"
    )
    disagreement: DisagreementInfo = Field(
        ..., description="Disagreement analysis across classifiers"
    )
    voting_method: str = Field(..., description="Voting method: 'soft' or 'hard'")
    processing_time_ms: float = Field(
        ..., description="Time taken to process request in milliseconds"
    )


class FiredRule(BaseModel):
    """Fired rule from rule-based system."""

    name: str = Field(..., description="Rule identifier")
    description: str = Field(..., description="Human-readable rule description")
    weight: float = Field(..., ge=0.0, le=1.0, description="Rule weight")
    matched_values: list[str] = Field(
        default_factory=list,
        description="Specific values that triggered this rule"
    )


class ParadigmContribution(BaseModel):
    """Contribution from a single paradigm."""

    probability: float = Field(..., ge=0.0, le=1.0, description="Paradigm probability")
    weight: float = Field(..., ge=0.0, le=1.0, description="Paradigm weight in aggregation")
    weighted_contribution: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="probability * weight"
    )
    prediction: Literal["phishing", "legitimate"] = Field(
        ..., description="This paradigm's individual prediction"
    )


class ParadigmContributions(BaseModel):
    """All paradigm contributions."""

    ml_ensemble: ParadigmContribution
    rules: ParadigmContribution
    bayesian: ParadigmContribution


class ParadigmDisagreementInfo(BaseModel):
    """Cross-paradigm disagreement analysis."""

    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized entropy across paradigms (0=agreement, 1=max disagreement)"
    )
    is_edge_case: bool = Field(
        ..., description="True if disagreement exceeds threshold (0.7)"
    )
    vote_distribution: dict = Field(
        ..., description="Vote counts: {'phishing': N, 'legitimate': M}"
    )
    probability_variance: float = Field(
        ..., description="Variance in probabilities across paradigms"
    )
    disagreeing_paradigms: list[str] = Field(
        ..., description="Paradigms disagreeing with majority"
    )
    probability_spread: float = Field(
        ..., description="Max - min probability across paradigms"
    )


class MultiParadigmResponse(BaseModel):
    """Response model for multi-paradigm prediction endpoint.

    Combines predictions from:
    - ML ensemble (7 classifiers with weighted voting)
    - Rule-based expert system (weighted phishing rules)
    - Bayesian probabilistic classifier (GaussianNB)

    Requirements addressed:
    - AGG-01: Combines all three paradigms
    - AGG-02: Includes disagreement detection with is_edge_case
    - AGG-03: Final prediction with confidence
    - AGG-04: Paradigm contributions with weights
    - RULE-07: Active rules list with explanations
    """

    url: str
    final_prediction: Literal["phishing", "legitimate"] = Field(
        ..., description="Aggregated prediction from all paradigms"
    )
    final_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Weighted probability (threshold 0.5)"
    )
    confidence: float = Field(
        ...,
        ge=0.5,
        le=1.0,
        description="Confidence level (0.5 + distance from threshold)"
    )
    paradigm_contributions: ParadigmContributions = Field(
        ..., description="Contributions from each paradigm"
    )
    disagreement: ParadigmDisagreementInfo = Field(
        ..., description="Cross-paradigm disagreement analysis"
    )
    active_rules: list[FiredRule] = Field(
        ..., description="Rules that fired from rule-based system"
    )
    explanation: str = Field(
        ..., description="Human-readable explanation of prediction"
    )
    processing_time_ms: float = Field(
        ..., description="Total processing time in milliseconds"
    )


class FeatureContribution(BaseModel):
    """Single named, signed SHAP feature contribution (EXPL-02)."""

    feature: str = Field(..., description="Feature name (from extract_url_features)")
    shap_value: float = Field(
        ...,
        description="Signed SHAP contribution in standardized-feature space "
                    "(relative contribution, not a raw probability unit)",
    )
    raw_value: float = Field(
        ..., description="Unscaled raw feature value for this URL"
    )


class ShapExplanation(BaseModel):
    """SHAP feature-importance block for the consolidated /explain response.

    v1 is URL-only (content_type fixed to "url") and explains the single
    representative RF Pipeline (model fixed to "rf") — see
    09-RESEARCH.md Pitfall 2 (VotingClassifier is not SHAP-explained).
    """

    available: bool = Field(
        ..., description="True if SHAP computation succeeded for this request"
    )
    content_type: Literal["url"] = Field(
        "url", description="SHAP v1 scope: URL-only"
    )
    model: str = Field("rf", description="Representative model explained")
    top_features: List[FeatureContribution] = Field(
        default_factory=list,
        description="Top-N signed contributions, ordered by descending |shap_value|",
    )
    note: str = Field(
        "", description="Human-readable caveat/status note (e.g. scaled-space label)"
    )


class ExplainResponse(BaseModel):
    """Response model for the consolidated POST /explain endpoint (Phase 9).

    Reuses URLRequest for input validation (no new input surface) and
    consolidates in ONE call: 7 individual ML predictions (EXPL-03),
    paradigm contributions, SHAP top-10 (EXPL-02, URL-only), fired rules
    with weights (EXPL-01), the fuller disagreement explanation (EXPL-04),
    and an NL verdict enriched with the top SHAP feature (EXPL-05).
    """

    url: str
    final_prediction: Literal["phishing", "legitimate"] = Field(
        ..., description="Aggregated prediction from all paradigms"
    )
    final_probability: float = Field(
        ..., ge=0.0, le=1.0, description="Weighted probability (threshold 0.5)"
    )
    confidence: float = Field(
        ..., ge=0.5, le=1.0, description="Confidence level"
    )
    individual_predictions: List[ClassifierResult] = Field(
        ..., description="Predictions from all 7 classifiers (EXPL-03)"
    )
    paradigm_contributions: ParadigmContributions = Field(
        ..., description="Contributions from each paradigm"
    )
    shap: ShapExplanation = Field(
        ..., description="SHAP feature importance (EXPL-02, URL-only)"
    )
    active_rules: List[FiredRule] = Field(
        ..., description="Rules that fired from the rule-based system (EXPL-01)"
    )
    disagreement: ParadigmDisagreementInfo = Field(
        ..., description="Cross-paradigm disagreement analysis"
    )
    disagreement_explanation: str = Field(
        ..., description="Fuller per-paradigm disagreement text (EXPL-04)"
    )
    explanation: str = Field(
        ..., description="Human-readable NL verdict, SHAP-enriched (EXPL-05)"
    )
    processing_time_ms: float = Field(
        ..., description="Total processing time in milliseconds"
    )


class EmailTextRequest(BaseModel):
    """Request model for raw email text prediction."""

    raw_email: str = Field(
        ...,
        description="Raw email content including headers and body",
        examples=["From: sender@example.com\nSubject: Test\n\nEmail body here."],
        min_length=10,
        max_length=500000  # 500KB text limit
    )

    @field_validator("raw_email")
    def validate_email_format(cls, v):
        """Basic validation that content looks like email."""
        # Should have at least one header-like pattern
        if not any(header in v for header in ["From:", "Subject:", "To:", "Date:"]):
            raise ValueError("Content doesn't appear to be email format (missing headers)")
        return v


class SMSRequest(BaseModel):
    """Request model for SMS/chat message prediction."""

    message: str = Field(
        ...,
        description="SMS or chat message text",
        examples=["URGENT: Your account has been suspended. Click here to verify."],
        min_length=1,
        max_length=5000  # Allow for MMS/longer messages
    )


class EmailSMSResponse(BaseModel):
    """Response model for email/SMS prediction.

    Similar to MultiParadigmResponse but adapted for email/SMS input.
    """

    content_type: Literal["email", "sms", "image"] = Field(
        ..., description="Type of content analyzed"
    )
    final_prediction: Literal["phishing", "legitimate"] = Field(
        ..., description="Aggregated prediction"
    )
    final_probability: float = Field(
        ..., ge=0.0, le=1.0, description="Phishing probability"
    )
    confidence: float = Field(
        ..., ge=0.5, le=1.0, description="Prediction confidence"
    )
    feature_count: int = Field(
        ..., description="Number of features extracted"
    )
    paradigm_contributions: Optional[ParadigmContributions] = Field(
        None, description="Paradigm contributions (if multi-paradigm enabled)"
    )
    active_rules: List[FiredRule] = Field(
        default_factory=list, description="Fired rules from rule engine"
    )
    explanation: str = Field(
        ..., description="Human-readable explanation"
    )
    processing_time_ms: float = Field(
        ..., description="Processing time in milliseconds"
    )
    visual_closest_brand: Optional[str] = Field(
        None,
        description="Closest-matching brand by perceptual-hash similarity "
                     "(image content only; None for email/sms). Diagnostic, "
                     "not a standalone verdict.",
    )
    visual_hash_distance: Optional[float] = Field(
        None,
        description="Hamming distance (0-64) to the closest brand reference "
                     "hash (image content only; None for email/sms). Lower "
                     "= more visually similar.",
    )
