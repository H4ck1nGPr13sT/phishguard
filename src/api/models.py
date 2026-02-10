"""Pydantic models for API request/response validation.

Models:
    - URLRequest: Validates incoming URL for prediction
    - PredictionResponse: Structured prediction result
    - HealthResponse: Health check status
    - ErrorResponse: Error details
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional


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
    version: str = "1.0.0"


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    detail: str
    url: Optional[str] = None
