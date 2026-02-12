"""Rule-based phishing detection expert system.

This module implements a weighted rule engine that evaluates URLs against
explicit phishing indicators:
- Urgent/pressure keywords ("verify", "suspended", "urgent")
- URL structure anomalies (IP addresses, excessive subdomains, suspicious TLDs)
- Domain indicators (shortened URLs, missing HTTPS, non-standard ports)
- Content patterns (brand impersonation, security-themed language)

The rule engine provides interpretable detection with detailed explanations
of which rules fired and why, complementing black-box ML models.
"""

from src.paradigms.rules.definitions import (
    PhishingRule,
    RuleCondition,
    RuleSet,
)

from src.paradigms.rules.engine import RuleEngine

__all__ = ['RuleEngine', 'PhishingRule', 'RuleCondition', 'RuleSet']
