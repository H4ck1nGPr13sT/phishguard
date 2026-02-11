# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-09)

**Core value:** Integracja wielu paradygmatów analizy w jeden spójny system, gdzie rozbieżności między metodami dostarczają dodatkowego kontekstu i zwiększają wiarygodność decyzji klasyfikacyjnej.

**Current focus:** Phase 3 - ML Ensemble Expansion

## Current Position

Phase: 3 of 10 (ML Ensemble Expansion)
Plan: 1 of TBD in current phase
Status: In progress
Last activity: 2026-02-11 — Completed 03-01-PLAN.md (Base Classifier Training)

Progress: [██░░░░░░░░] 22%

## Performance Metrics

**Velocity:**
- Total plans completed: 10
- Average duration: 72 min
- Total execution time: 12 hours 5 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation-data-pipeline | 4 | 21 min | 5 min |
| 02-core-ml-pipeline-url-detection-mvp | 5 | 11h 39min | 2h 20min |
| 03-ml-ensemble-expansion | 1 | 5 min | 5 min |

**Recent Trend:**
- Last 5 plans: 02-03 (3 min), 02-04 (2 min), 02-05 (11h 27min), 03-01 (5 min)
- Note: 02-05 duration includes human verification pause, actual automation time ~2 min

*Updated after each plan completion*

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

### Pending Todos

None yet.

### Blockers/Concerns

**Phase 1:**
- PhishTank API key not configured yet - need user to register at phishtank.com
- Nazario corpus availability uncertain (original site archived) - may need Web Archive or alternative source
- UCI ML dataset has features only (no raw URLs) - Phase 02 preprocessing must handle both URL-based and feature-based inputs

**Phase 3:** Research needed for genetic algorithm fitness function design and hyperparameter search spaces

**Phase 5:** Research needed for Bayesian network structure and modern rule-based heuristics (2026 threat landscape)

**Phase 7:** Research needed for OCR preprocessing techniques for adversarial images and visual similarity algorithms

## Session Continuity

Last session: 2026-02-11
Stopped at: Completed 03-01-PLAN.md (Base Classifier Training)
Resume file: None

---
*State initialized: 2026-02-09*
*Last updated: 2026-02-11 (after 03-01)*
