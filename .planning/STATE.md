# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-09)

**Core value:** Integracja wielu paradygmatów analizy w jeden spójny system, gdzie rozbieżności między metodami dostarczają dodatkowego kontekstu i zwiększają wiarygodność decyzji klasyfikacyjnej.

**Current focus:** Phase 2 - Core ML Pipeline - URL Detection MVP

## Current Position

Phase: 2 of 10 (Core ML Pipeline - URL Detection MVP)
Plan: 1 of TBD in current phase
Status: In progress
Last activity: 2026-02-10 — Completed 02-01-PLAN.md (URL Feature Extraction)

Progress: [██░░░░░░░░] 11%

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: 4.8 min
- Total execution time: 0.40 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation-data-pipeline | 4 | 21 min | 5 min |
| 02-core-ml-pipeline-url-detection-mvp | 1 | 3 min | 3 min |

**Recent Trend:**
- Last 5 plans: 01-02 (3 min), 01-03 (5 min), 01-04 (8 min), 02-01 (3 min)
- Trend: Consistent execution velocity, feature extraction faster than expected

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

Last session: 2026-02-10
Stopped at: Completed 02-01-PLAN.md (URL Feature Extraction Module)
Resume file: None

---
*State initialized: 2026-02-09*
*Last updated: 2026-02-10*
