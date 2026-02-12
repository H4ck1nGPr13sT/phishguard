---
phase: 05-alternative-detection-paradigms
plan: 01
subsystem: detection-rules
tags: [pydantic, yaml, rule-engine, expert-system, weighted-scoring]

# Dependency graph
requires:
  - phase: 02-core-ml-pipeline-url-detection-mvp
    provides: Feature extraction pipeline (extract_url_features with 30 numeric features)
provides:
  - Rule-based phishing detection with 16 weighted rules
  - RuleEngine class with interpretable explanations
  - Pydantic validation for rule definitions
  - YAML-based rule configuration
affects: [05-02-bayesian, 05-03-aggregation, multi-paradigm-consensus]

# Tech tracking
tech-stack:
  added: [pyyaml]
  patterns: [rule-based expert system, weighted scoring, Pydantic validation, YAML configuration]

key-files:
  created:
    - src/paradigms/__init__.py
    - src/paradigms/rules/__init__.py
    - src/paradigms/rules/definitions.py
    - src/paradigms/rules/engine.py
    - src/paradigms/rules/phishing_rules.yaml
  modified: []

key-decisions:
  - "Total rule weight 3.05 allows multiple rules to fire without easily exceeding 1.0 normalized score"
  - "Three condition types: keyword_match (raw URL), feature_check (numeric features), domain_match (known domains)"
  - "0.5 threshold for phishing prediction with confidence as distance from threshold"
  - "Raw URL passed separately to enable keyword matching (not in feature dict)"

patterns-established:
  - "Rule definitions in YAML with Pydantic validation for type safety"
  - "Weighted scoring with normalization to [0, 1] range via min(total_score, 1.0)"
  - "Detailed explanations with fired_rules list containing matched values"
  - "Condition type abstraction supports multiple evaluation strategies"

# Metrics
duration: 3min
completed: 2026-02-12
---

# Phase 05 Plan 01: Rule-Based Expert System Summary

**Rule-based phishing detector with 16 weighted rules covering keywords, URL structure, and domain indicators, returning scores with interpretable explanations**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-12T20:46:02Z
- **Completed:** 2026-02-12T20:49:02Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Created rule-based expert system with 16 phishing detection rules
- Implemented RuleEngine with three condition types (keyword_match, feature_check, domain_match)
- Established YAML-based rule configuration with Pydantic validation
- Achieved interpretable detection with detailed explanations of fired rules

## Task Commits

Each task was committed atomically:

1. **Task 1: Create rule definitions with Pydantic validation** - `b6a394b` (feat)
2. **Task 2: Create phishing rules YAML with 16 detection rules** - `5481930` (feat)
3. **Task 3: Implement RuleEngine with weighted evaluation** - `fc72494` (feat)

## Files Created/Modified

- `src/paradigms/__init__.py` - Module structure for alternative detection paradigms
- `src/paradigms/rules/__init__.py` - Rule-based detection module exports
- `src/paradigms/rules/definitions.py` - Pydantic models (RuleCondition, PhishingRule, RuleSet) with validation
- `src/paradigms/rules/engine.py` - RuleEngine class with weighted scoring and explanation generation
- `src/paradigms/rules/phishing_rules.yaml` - 16 phishing detection rules organized by category

## Rule Coverage

**URL Structure (4 rules):**
- IP addresses (0.35 weight)
- URL shorteners (0.20 weight)
- Excessive subdomains (0.15 weight)
- Suspicious TLDs (0.25 weight)

**Keywords (5 rules):**
- Urgent/pressure keywords (0.20 weight)
- Security keywords (0.15 weight)
- Action keywords (0.15 weight)
- Brand impersonation (0.25 weight)
- Threat keywords (0.20 weight)

**Structure Indicators (4 rules):**
- Long URLs (0.10 weight)
- Many special chars (0.15 weight)
- High entropy (0.15 weight)
- Deep paths (0.10 weight)

**Domain Indicators (3 rules):**
- No HTTPS (0.15 weight)
- Non-standard port (0.20 weight)
- @ symbol obfuscation (0.30 weight)

**Total weight:** 3.05 (allows multiple rules to fire, normalized to [0, 1] range)

## Decisions Made

1. **Raw URL parameter:** Added raw_url as optional parameter to evaluate() for keyword_match conditions, since keywords need to be checked in the original URL string (not numeric features)

2. **Domain match strategy:** domain_match condition checks if any domain from list appears in URL (substring match), handles both exact domains and domains within URL

3. **Score normalization:** min(total_score, 1.0) caps score at 1.0, allowing flexible rule weights while maintaining consistent output range

4. **Pydantic validation:** RuleSet validator warns if total weight > 2.0 (potential redundancy), but doesn't error (allows flexibility)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - implementation proceeded smoothly. All verifications passed on first attempt.

## Test Results

**Suspicious URL test:** `http://192.168.1.1/login/verify`
- Score: 0.70
- Prediction: phishing
- Fired rules: 4
  - ip_address_host (0.35)
  - urgent_keywords (0.20) - matched "verify"
  - action_keywords (0.15) - matched "login"
  - no_https (0.15)

**Legitimate URL test:** `https://google.com`
- Score: 0.00
- Prediction: legitimate
- Fired rules: 0

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Phase 05 Plan 02 (Bayesian reasoning):**
- Rule-based paradigm complete and tested
- RuleEngine provides interpretable explanations
- Can be integrated with Bayesian network for multi-paradigm analysis
- Feature extraction pipeline compatible (uses same 30 numeric features)

**Blockers:** None

**Considerations for next phases:**
- Bayesian network can incorporate rule scores as evidence nodes
- Multi-paradigm aggregation will combine rule-based, ML, and Bayesian predictions
- Rule explanations provide interpretability layer for black-box ML models

---
*Phase: 05-alternative-detection-paradigms*
*Completed: 2026-02-12*

## Self-Check: PASSED

All files and commits verified successfully.
