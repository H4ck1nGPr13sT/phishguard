"""Pydantic models for rule-based phishing detection definitions.

This module defines the schema for phishing detection rules:
- RuleCondition: Specifies how to evaluate a single condition
- PhishingRule: Complete rule with condition, weight, and metadata
- RuleSet: Collection of rules with version tracking

All models use Pydantic v2 for validation and type safety.
"""

from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


class RuleCondition(BaseModel):
    """Condition specification for rule evaluation.
    
    Supports three condition types:
    - keyword_match: Check if keywords appear in URL string
    - feature_check: Compare feature value using operator
    - domain_match: Check if domain matches known list (e.g., URL shorteners)
    """
    
    type: Literal['keyword_match', 'feature_check', 'domain_match']
    
    # For feature_check and domain_match
    feature: Optional[str] = None
    
    # For keyword_match (can check multiple features)
    features: Optional[list[str]] = None
    
    # For keyword_match
    keywords: Optional[list[str]] = None
    
    # For domain_match
    domains: Optional[list[str]] = None
    
    # For feature_check
    operator: Optional[Literal['equals', 'greater_than', 'less_than', 'contains']] = None
    value: Optional[Union[float, int, str]] = None
    
    @field_validator('keywords', 'domains')
    @classmethod
    def validate_lists_not_empty(cls, v):
        """Ensure list fields are not empty if provided."""
        if v is not None and len(v) == 0:
            raise ValueError("List cannot be empty")
        return v


class PhishingRule(BaseModel):
    """Single phishing detection rule with condition and weight.
    
    Each rule fires when its condition evaluates to True, contributing
    its weight to the total phishing score.
    """
    
    name: str = Field(..., description="Rule identifier (snake_case)")
    description: str = Field(..., description="Human-readable explanation")
    weight: float = Field(..., ge=0.0, le=1.0, description="Rule weight (0.0-1.0)")
    condition: RuleCondition
    category: Optional[str] = Field(None, description="Rule grouping (url_structure, keywords, domain, etc.)")
    
    @field_validator('name')
    @classmethod
    def validate_snake_case(cls, v):
        """Ensure rule name is snake_case."""
        if not v.islower() or ' ' in v:
            raise ValueError("Rule name must be lowercase snake_case")
        return v


class RuleSet(BaseModel):
    """Collection of phishing detection rules with versioning.
    
    Tracks rule version for reproducibility and warns if total weight
    suggests potential redundancy.
    """
    
    version: str = Field(..., description="Rule version for tracking")
    rules: list[PhishingRule]
    
    @field_validator('rules')
    @classmethod
    def validate_total_weight(cls, v):
        """Warn if total weight > 2.0 (possible redundancy)."""
        total_weight = sum(rule.weight for rule in v)
        if total_weight > 2.0:
            import warnings
            warnings.warn(
                f"Total rule weight {total_weight:.2f} > 2.0 may indicate redundancy. "
                "Consider reviewing rule weights to prevent excessive scores.",
                UserWarning
            )
        return v
