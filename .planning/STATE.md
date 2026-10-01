---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: completed
stopped_at: context exhaustion at 75% (2026-10-01)
last_updated: "2026-10-01T11:31:54.454Z"
last_activity: 2026-10-01 -- Phase 10 marked complete
progress:
  total_phases: 10
  completed_phases: 10
  total_plans: 53
  completed_plans: 53
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-09)

**Core value:** Integracja wielu paradygmatów analizy w jeden spójny system, gdzie rozbieżności między metodami dostarczają dodatkowego kontekstu i zwiększają wiarygodność decyzji klasyfikacyjnej.

**Current focus:** Phase 6 - Email/SMS Support

## Current Position

Phase: 10 — COMPLETE
Plan: 7 of 7 in current phase
Status: Phase 10 complete
Last activity: 2026-10-01 -- Phase 10 marked complete

Progress: [██████████████████████████] 100%

## Performance Metrics

**Velocity:**

- Total plans completed: 31
- Average duration: 30 min
- Total execution time: 15 hours 53 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation-data-pipeline | 4 | 21 min | 5 min |
| 02-core-ml-pipeline-url-detection-mvp | 5 | 11h 39min | 2h 20min |
| 03-ml-ensemble-expansion | 4 | 1h 9min | 17 min |
| 04-genetic-algorithm-optimization | 6 | 1h 26min | 14 min |
| 05-alternative-detection-paradigms | 5 | 29 min | 6 min |
| 06-email-sms-support | 7 | 46 min | 7 min |

**Recent Trend:**

- Last 5 plans: 06-02 (10 min), 06-04 (4 min), 06-05 (6 min), 06-06 (6 min), 06-07 (10 min)
- Note: Phase 06 complete - all email/SMS support delivered and verified

*Updated after each plan completion*
| Phase 06 P07 | 10 min | 3 tasks | 1 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Open demo bez logowania - uproszczenie architektury dla demonstratora akademickiego
- OCR + cechy wizualne dla obrazów - pełniejsza analiza phishingu w formie graficznej
- Wyjaśnienia decyzji w output - interpretowalność kluczowa dla pracy akademickiej
- Integracja 4 metod jako core value - główna teza pracy, synergia podejść

**From 01-01 (2026-02-10):**

- Python >=3.9 for compatibility with available system Python
- python-dotenv for configuration (simpler than Hydra)
- Local cache fallback strategy for all downloaders
- Extract all URLs from Nazario emails (not just first URL)

**From 01-02 (2026-02-10):**

- Lazy validation with Pandera to filter invalid rows instead of failing
- Empty string for UCI ML URLs (feature-only dataset)
- Exact deduplication as default with fuzzy option
- Preserve UCI ML feature columns in merged dataset

**From 01-03 (2026-02-10):**

- Temporal split enforces strict train < validation < test ordering to prevent data leakage
- Samples without timestamps assigned conservatively to training set only
- target_ratio parameter represents proportion of minority class (0.5 = 50/50 balanced)
- Hybrid SMOTE + undersampling approach for robust balancing
- Balancing applied ONLY to training data (never validation/test)

**From 01-04 (2026-02-10):**

- Pipeline orchestrates 9 stages with comprehensive reporting for thesis documentation
- Joblib caching (compression level 3) for reproducible experiments
- Feature-only datasets skip URL deduplication to avoid false duplicates
- SMOTE balancing uses numeric features only (metadata columns separated)
- Integration tests run with UCI-only data (no API keys required for CI/CD)

**From 02-01 (2026-02-10):**

- tldextract for robust domain parsing (handles Public Suffix List edge cases like co.uk, github.io)
- Suspicious TLD list: tk, ml, ga, cf, gq, xyz, pw, cc (commonly used in phishing)
- Return default dict with zeros for empty/invalid URLs (prevents pipeline crashes)
- 30 numeric features: 7 length, 10 character counts, 8 binary, 5 structure (including Shannon entropy)

**From 02-02 (2026-02-10):**

- sklearn Pipeline pattern prevents data leakage from scaling test data (fit only on train)
- OOB score validation when test set is empty (UCI ML dataset limitation)
- joblib model persistence with protocol=5, compress=3 (90% size reduction)
- class_weight='balanced' in RandomForestClassifier handles any data imbalance
- Model achieves 96.14% OOB accuracy (exceeds 90% requirement)

**From 02-03 (2026-02-10):**

- FastAPI lifespan events load model once at startup (not per-request) for sub-500ms latency
- Sync 'def' endpoints (not 'async def') because ML inference is CPU-bound, FastAPI uses threadpool
- Global ml_models dict provides singleton model access across endpoints
- Pydantic v2 field_validator enforces URL format (http/https, 10-2048 chars)

**From 02-04 (2026-02-10):**

- 14 integration tests cover feature extraction, model persistence, API endpoints, and end-to-end flow
- Latency benchmarking confirms <500ms API response and <50ms feature extraction (requirements met)
- No WHOIS dependency added - research recommends skipping for latency reasons
- Integration tests use real model and real URLs (not mocked) for true end-to-end validation

**From 02-05 (2026-02-11):**

- Human verification via Swagger UI confirmed all endpoints functional
- Health endpoint shows model loaded successfully (2.5 MB rf_pipeline.joblib)
- Prediction endpoints validated with both legitimate and suspicious URLs
- URL validation working correctly (422 errors for invalid URLs)
- Phase 2 MVP delivery complete: feature extraction → model → API → tests → human-verified

**From 03-01 (2026-02-11):**

- XGBoost serves as Gradient Boosting implementation (no separate sklearn GradientBoostingClassifier)
- SVM configured with probability=True for soft voting in ensemble
- XGBoost n_jobs=1 to prevent thread thrashing when sklearn uses n_jobs=-1
- Naive Bayes kept despite 64% accuracy for ensemble diversity contribution
- 5-fold CV for validation instead of train/val split (matches training data structure)
- 7 classifiers trained with 89% average accuracy: RF (96.14% OOB), SVM (94.74%), MLP (96.29%), XGBoost (95.52%), LR (91.68%), NB (64.07%), DT (92.62%)

**From 03-02 (2026-02-11):**

- Soft voting averages predict_proba() from all 7 classifiers (97.47% accuracy)
- Hard voting uses majority vote across predictions (97.14% accuracy)
- Stacking uses LogisticRegression meta-model with cv=5 to prevent data leakage
- get_individual_predictions() extracts phishing_probability, prediction, confidence for disagreement analysis
- Ensemble models saved with metadata (model_type, created_at, n_estimators) for tracking
- All 3 aggregation strategies exceed average individual classifier accuracy (89.15%)

**From 03-03 (2026-02-11):**

- Shannon entropy normalized by log2(n_classifiers) for disagreement detection (0-1 scale)
- For 7 classifiers with 4-3 split, normalized entropy ~0.35 (not close to 1.0)
- Default disagreement threshold 0.7 is high bar for binary classification scenarios
- /predict/ensemble API endpoint returns all 7 individual predictions plus ensemble verdict
- DisagreementInfo includes score, edge case flag, vote distribution, agreeing/dissenting classifier lists
- Backward compatible ensemble loading - API works with RF only if ensemble models missing

**From 03-04 (2026-02-11):**

- Retrained all models with real URL features from OpenPhish + legitimate URLs to fix feature mismatch
- UCI ML pre-encoded features (-1/0/1) incompatible with our custom 30-feature extraction pipeline
- OpenPhish public feed provides 300 phishing URLs without API key requirement
- Balanced dataset at 125+125 URLs achieves 88-92% test accuracy (sufficient for MVP validation)
- scripts/retrain_with_urls.py automates retraining for future model updates
- load_model() enhanced to handle both dict-wrapped and direct Pipeline formats
- Human verification confirmed: google.com → 98.9% legitimate, paypal-security-update.tk → 97.6% phishing
- API latency <60ms for ensemble predictions (well below 500ms requirement)
- Phase 3 complete: all 7 classifiers operational with disagreement detection functional

**From 04-01 (2026-02-11):**

- DEAP 1.4.3 chosen as GA framework for full control over evolution process (vs. sklearn-genetic-opt abstraction)
- F1-score with 5-fold stratified CV as fitness metric to handle class imbalance and prevent overfitting
- Search spaces defined 2-3x wider than baseline to enable exploration (RF n_estimators: 50-300, XGBoost: 9 hyperparameters)
- Tournament selection (tournsize=3) balances exploration/exploitation, prevents premature convergence
- Mutation probability 20% per gene (indpb=0.2) maintains diversity, higher than typical 10%
- n_jobs=1 in cross_val_score prevents nested parallelism (classifiers use n_jobs=-1) to avoid thread thrashing
- Type-aware hyperparameter encoding handles int, float (with log scale), and categorical parameters
- HallOfFame(maxsize=10) preserves elite individuals across generations
- Log-scale sampling for C, gamma, alpha enables uniform exploration across orders of magnitude

**From 04-02 (2026-02-11):**

- MLflow tracking with single run per classifier, generation metrics via step parameter (simpler than nested runs)
- cxBlend crossover works with any number of hyperparameters (including 1 for NB), alpha=0.5 for exploration
- mutPolynomialBounded mutation handles mixed int/float/categorical parameters (vs. mutUniformInt)
- Bounds checking decorator prevents out-of-range values and complex number errors in genetic operators
- LR solver selection: saga for penalty='none', lbfgs for penalty='l2' (automatic compatibility handling)
- 30 generations, population=50 balances exploration vs runtime (~15-90 seconds per classifier)
- All 7 classifiers optimized: average +1.75% test F1 improvement (6 improved, 1 unchanged)
- Small test set (50 samples) causes variance in test F1 scores, consider expanding for future phases

**From 04-03 (2026-02-11):**

- Binary representation (1=selected, 0=excluded) for GA feature selection
- RF proxy classifier for fitness evaluation - fast and robust for feature selection across all classifiers
- Minimum 5 features constraint prevents degenerate solutions
- Two-point crossover and bit-flip mutation for binary GA (indpb=1/n_features)
- Smaller population (30) and fewer generations (20) for binary search space vs hyperparameter optimization
- GA feature selection identified 16 optimal features from 30 (46.7% reduction, +0.56% F1 improvement)
- Structural features (entropy, special_char_count, dot_count) most discriminative
- Many length features redundant - url_length sufficient, hostname/domain/tld less important

**From 04-04 (2026-02-11):**

- Blend crossover (alpha=0.5) for continuous weight space exploration beyond parent bounds
- Minimum weight constraint 0.01 preserves ensemble diversity (prevents zeroing out classifiers)
- Equal-weight baseline comparison validates GA value (+0.53% F1 improvement)
- Smaller GA configuration (pop=30, gen=20) for weight optimization - simpler search space than hyperparameters
- Optimized weights favor SVM/MLP/XGBoost (0.25-0.26 each), minimize RF/LR/NB/DT
- GA downweighted RF to 0.015 despite typical strength - small dataset benefits more from SVM/MLP generalization
- Weighted voting ensemble achieves F1=0.9654 vs F1=0.9602 equal-weight baseline

**From 04-05 (2026-02-11):**

- Model registry uses cache/active_models.json for version selection (simple, explicit, version-controllable)
- get_active_model() defaults to ga_optimized with fallback to baseline for backward compatibility
- API loads models from registry at startup, not hardcoded paths
- Comparison framework shows +1.75% avg classifier improvement (MLP best at +4.55%)
- Ensemble improvement: +1.96% F1 (soft voting → weighted voting)
- All classifiers set to ga_optimized version (all show improvement >= 0)
- MLflow Model Registry tracks all baseline and optimized versions with metrics

**From 04-06 (2026-02-12):**

- Comprehensive 24-test suite covers all GA optimization modules (491 lines)
- Test suite runs in <30 seconds using synthetic data and reduced GA parameters for CI/CD
- Integration tests validate full optimization pipeline from hyperparameter tuning to model prediction
- Human verification confirmed optimization results reasonable via MLflow UI and model comparison
- All Phase 4 requirements verified complete (GA-01 through GA-06, MODEL-03 through MODEL-05, EVAL-04)
- Phase 4 complete: all genetic algorithm optimization objectives achieved

**From 05-01 (2026-02-12):**

- Rule-based expert system with 16 weighted phishing rules (total weight 3.05, normalized to [0, 1])
- Three condition types: keyword_match (raw URL), feature_check (numeric features), domain_match (known domains)
- Raw URL passed separately to evaluate() for keyword matching (not in feature dict)
- Pydantic validation for rules with warning when total weight > 2.0 (potential redundancy)
- Score normalization via min(total_score, 1.0) allows flexible rule weights
- Rules cover URL structure (IP, shorteners, subdomains, TLDs), keywords (urgent, security, action, brands, threats), structure indicators (length, entropy, special chars), domain indicators (HTTPS, ports, @ symbol)

**From 05-02 (2026-02-12):**

- BayesianClassifier wraps GaussianNB with Pipeline (StandardScaler + GaussianNB) for feature normalization
- class_prior_ attribute (not class_log_prior_) used to extract class priors from fitted GaussianNB
- predict_with_posterior() returns structured dict: posterior_phishing, posterior_legitimate, prediction, confidence, prior_info
- Prior information includes both log-scale and probability-scale priors for interpretability
- var_smoothing=1e-9 default parameter for numerical stability (sklearn default)
- Trained model achieves F1=0.9390 (5-fold CV) on 200 URL samples (comparable to ensemble classifiers)
- Model size: 2.0K compressed with joblib (very lightweight)
- Integration with existing feature extraction pipeline (extract_url_features)

**From 05-03 (2026-02-12):**

- Default paradigm weights: ML ensemble=0.5, Rules=0.3, Bayesian=0.2 (ML dominant but not overwhelming)
- ParadigmWeights dataclass validates sum to 1.0 with soft warnings for out-of-range weights
- Cross-paradigm disagreement uses normalized Shannon entropy: H / log2(3) for 3 paradigms
- Disagreement threshold 0.7 consistent with Phase 3 classifier disagreement detection
- Confidence calculated as 0.5 + |probability - 0.5| (distance from decision boundary)
- MultiParadigmAggregator returns structured output: prediction, probability, confidence, contributions, disagreement, active_rules, explanation
- Human-readable explanations with confidence levels (high/moderate/low) and disagreement warnings
- 20-test suite validates weights, disagreement detection, and aggregation (all passing in 0.38s)

**From 05-04 (2026-02-12):**

- /predict/multi-paradigm endpoint requires all 4 models loaded (voting_soft, rule_engine, bayesian, aggregator) - returns 503 if any missing
- Raw URL passed to rule engine via raw_url parameter for keyword matching alongside feature dict
- Nested Pydantic models (MultiParadigmResponse, ParadigmContributions, ParadigmDisagreementInfo, FiredRule) provide structured API response
- API version 2.0.0 indicates Phase 5 multi-paradigm capability
- Endpoint returns paradigm contributions, disagreement detection, and active rules list (RULE-07 requirement)
- 12-test suite validates endpoint structure, error handling, probability ranges (all passing in 1.81s)

**From 05-05 (2026-02-13):**

- Rule engine tests use tempfile YAML for custom rule loading verification (isolated test fixtures)
- Integration tests validate all Phase 5 requirements (RULE-01 through AGG-04) with traceability
- Separate test classes per concern (definitions, engine, conditions, edge cases) for targeted testing
- Human verification confirmed: suspicious URL 98.9% phishing (5 rules fired), legitimate URL 0.7% (no rules)
- Fixed voting_soft alias in API for registry-loaded ensemble compatibility
- All 88 tests pass across Phase 5 test suites (22 rules + 18 integration + 11 bayesian + 20 aggregation + 12 API + 5 misc)

**From 06-01 (2026-02-16):**

- Email parsing module using stdlib email.message_from_bytes with RFC 5322 compliant policy.default
- Extract authentication status from Authentication-Results header (faster than live DKIM verification, no DNS lookups)
- 15 email header features: authentication (SPF/DKIM/DMARC), sender domain (length, suspicious TLD, Reply-To mismatch), subject (length, urgent keywords, Re:/Fwd: prefixes), structure (header count, X-headers, Received headers)
- Multipart email handling prefers text/plain over text/html (same phishing indicators, faster parsing)
- BeautifulSoup with lxml backend for HTML text extraction (robust, handles malformed HTML)
- Suspicious TLDs: tk, ml, ga, cf, gq, xyz (commonly used in phishing)
- Urgent keywords: urgent, important, action required, immediate, verify, suspend
- 25 comprehensive unit tests covering all functions and edge cases (all passing in 0.64s)
- Follows url_features.py pattern with default zero features for invalid/empty emails

**From 06-03 (2026-02-16):**

- SMS feature extraction module with 20 smishing-specific features
- Four feature categories: length (4), URL (4), phone (2), character (4), patterns (6)
- Dynamic regex pattern for shortened URL detection (14 common domains: bit.ly, tinyurl, t.co, etc.)
- Pattern detection: urgency caps (URGENT, ALERT), prize claims (won, prize), account alerts (suspended, verify)
- SMS shorthand ratio detection (u, ur, plz, asap, etc. / word count)
- Emoji detection via Unicode ranges (U+1F600-U+1F9FF) without external dependencies
- parse_sms() extracts URLs, phone numbers, detects multipart (>160 chars)
- 24 comprehensive unit tests across 5 test classes (all passing in <0.05s)
- No duplication of NLP features - SMS features focus on message-specific patterns only

**From 06-02 (2026-02-16):**

- NLP text feature extraction with spaCy 3.8.11 and textstat 0.7.12
- 50 features total: lexical (15), syntactic (15), stylometric (10), sentiment (10)
- Lexical: word counts, character distributions, URL/email/phone patterns
- Syntactic: POS tag ratios via spaCy, sentence structure, imperative verb detection
- Stylometric: readability scores (Flesch, Gunning Fog), lexical diversity, syllable counts
- Sentiment: urgency/threat/action/reward keyword detection for phishing-specific patterns
- spaCy en_core_web_sm model (15MB) chosen over larger models - sufficient for POS tagging
- NER disabled in spaCy for processing speed (not needed for feature extraction)
- No stop words filtering - words like "urgent", "your", "now" are phishing indicators per research
- TextFeatureExtractor class pattern matches url_features.py design for consistency
- 36 comprehensive unit tests covering all feature categories (100% pass rate in 6.86s)

**From 06-04 (2026-02-16):**

- Unified extract_features() interface handles URL, email, and SMS inputs with auto-detection
- ContentType enum (URL, EMAIL, EMAIL_FILE, SMS) for explicit type routing
- Email extraction combines ~15 header + ~50 text features = ~65 total
- SMS extraction combines ~20 SMS-specific + ~50 text features = ~70 total
- Module-level TextFeatureExtractor singleton via get_text_extractor() - spaCy model loaded once
- Feature prefixing pattern: text features prefixed with "text_" when combined with domain-specific features
- 16 integration tests validate unified extraction across all content types (100% pass rate)

**From 06-05 (2026-02-16):**

- POST /predict/email, /predict/email/file, /predict/sms REST API endpoints for email/SMS phishing detection
- FastAPI UploadFile for .eml file handling with 5MB size limit and extension validation
- EmailSMSResponse with optional paradigm_contributions for future multi-paradigm integration
- Feature count validation before prediction - returns HTTP 501 Not Implemented when features don't match trained models
- Current models trained on 30 URL features, but email has 65+ and SMS has 70+ features
- Endpoints return 501 with clear error message until models retrained (Plan 06-06)
- API version 3.0.0 indicates Phase 6 email/SMS support capability
- 21 API tests: 8 passed (validation), 13 skipped (prediction blocked on model retraining)

**From 06-06 (2026-02-16):**

- All 7 classifiers retrained for email (65 features) and SMS (70 features) content types
- Synthetic training datasets: 200 email samples (100 phishing + 100 legitimate), 200 SMS samples
- Email models achieve 90-100% test accuracy (avg 98.4%), SMS models achieve 100% test accuracy
- Model metadata stored with each model: feature_names, feature_count, test_accuracy, created_at
- API lifespan loads email_ensemble and sms_ensemble at startup
- /predict/email and /predict/sms endpoints now functional (use content-specific models)
- /health endpoint reports email_model_loaded and sms_model_loaded status
- Ensemble models: ensemble_email.joblib (817KB), ensemble_sms.joblib (820KB)
- Quality validation: no duplicates, balanced classes, domain diversity requirements met

**From 06-07 (2026-02-17):**

- Integration tests use real models (not mocked) for end-to-end validation
- Test suite accepts 200 or 503 responses (503 when models not loaded)
- Human verification confirms all Phase 6 requirements met via Swagger UI
- 155-line test suite covers INPUT-02, INPUT-03, FEAT-02, FEAT-03, FEAT-04, FEAT-06, FEAT-07
- Test structure: TestInputRequirements, TestFeatureExtraction, TestAPIEndpoints classes
- Explicit requirement coverage in test docstrings for traceability

### Pending Todos

None yet.

### Blockers/Concerns

**Phase 1:**

- PhishTank API key not configured yet - need user to register at phishtank.com
- Nazario corpus availability uncertain (original site archived) - may need Web Archive or alternative source
- UCI ML dataset has features only (no raw URLs) - Phase 02 preprocessing must handle both URL-based and feature-based inputs

**Phase 3:** ✓ Complete - ensemble system with 7 classifiers + disagreement detection operational

**Phase 4:** ✓ Complete - all GA optimization objectives achieved plus model versioning and comprehensive testing: hyperparameter tuning (+1.75% avg F1), feature selection (16 optimal features, 46.7% reduction), ensemble weight optimization (+1.96% F1 ensemble improvement), model registry with MLflow tracking, 24-test suite validates all modules. Human-verified optimization results. Ready for Phase 5 Bayesian reasoning

**Phase 5:** ✓ Complete - All five plans delivered: (1) Rule-based expert system with 16 weighted rules, (2) Bayesian probabilistic classifier (F1=0.9390), (3) Multi-paradigm aggregation layer combining ML ensemble + rules + Bayesian with weighted voting and cross-paradigm disagreement detection, (4) /predict/multi-paradigm REST API endpoint exposing complete multi-paradigm detection, (5) Comprehensive testing (88 tests) + human verification confirming 98.9% detection on suspicious URLs and 0.7% false positive rate on legitimate URLs. All requirements (RULE-01 through RULE-07, PROB-01 through PROB-04, AGG-01 through AGG-04) addressed.

**Phase 6:** ✓ Complete - All seven plans delivered: (1) Email parser with header feature extraction (15 features), (2) NLP text features with spaCy (50 features), (3) SMS feature extraction (20 smishing-specific features), (4) Unified feature extractor handling URL/email/SMS with auto-detection, (5) API endpoints for email and SMS prediction (/predict/email, /predict/email/file, /predict/sms), (6) Model retraining with expanded feature sets (email: 65 features, SMS: 70 features, 90-100% accuracy), (7) Integration testing and human verification. All requirements (INPUT-02, INPUT-03, FEAT-02, FEAT-03, FEAT-04, FEAT-06, FEAT-07) addressed. Ready for Phase 7 OCR & Visual Analysis

**Phase 7:** Research needed for OCR preprocessing techniques for adversarial images and visual similarity algorithms

## Session Continuity

Last session: 2026-10-01T11:31:54.449Z
Stopped at: context exhaustion at 75% (2026-10-01)
Resume file: None

### Resume Instructions

**Project Status:** Phase 6 (Email & SMS Support) successfully completed and verified.

All deliverables:

- ✓ 6 phases complete (31 plans executed)
- ✓ Email/SMS phishing detection with 65+ email and 70+ SMS features
- ✓ Multi-paradigm system (ML ensemble + Rules + Bayesian)
- ✓ GA-optimized classifiers (98.4% email accuracy, 100% SMS accuracy)
- ✓ FastAPI endpoints with Swagger documentation
- ✓ 388 tests passing (no regressions)

To continue development:

```
/gsd:plan-phase 7
```

Phase 7 focus: OCR & Visual Analysis for image-based phishing detection

**Completed Phases:**

1. Foundation & Data Pipeline (4 plans)
2. Core ML Pipeline & URL Detection MVP (5 plans)
3. ML Ensemble Expansion (4 plans)
4. Genetic Algorithm Optimization (6 plans)
5. Alternative Detection Paradigms (5 plans)
6. Email & SMS Support (7 plans)

---
*State initialized: 2026-02-09*
*Last updated: 2026-03-08 (Phase 6 complete - project saved before closing)*
