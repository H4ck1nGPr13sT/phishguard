# Phase 1: Foundation & Data Pipeline - Context

**Gathered:** 2026-02-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish data acquisition, preprocessing, and quality validation infrastructure. This phase builds the pipeline that downloads public phishing datasets, validates data quality, implements temporal train-test splits, and handles class imbalance. The pipeline outputs clean, balanced, temporally-split datasets ready for model training in Phase 2.

</domain>

<decisions>
## Implementation Decisions

### Dataset Acquisition
- Download from multiple sources equally: PhishTank + UCI ML Repository + Nazario corpus
- Merge all available datasets into unified format
- Use local cache fallback: download fresh when possible, use cached snapshots as fallback
- Log which sources succeeded/failed during acquisition
- Store datasets at external configurable path (outside project directory)

### Temporal Validation
- Use 70/15/15 split: 70% training, 15% validation, 15% test
- All splits are temporal: training data strictly before validation, validation before test
- Samples without valid timestamps: assign to training set only (conservative approach to prevent leakage)

### Class Imbalance Handling
- Use hybrid approach: combine SMOTE (oversample minority) + undersampling (reduce majority)
- Target ratio is configurable via config for experimentation
- Generate detailed balancing report: original counts, technique used, final counts, synthetic sample count

### Quality Controls
- Strict validation criteria: reject empty content, invalid URLs, duplicates, missing labels, encoding errors
- Generate full validation report: samples processed, rejected by reason, statistics

### Claude's Discretion
- External data path configuration method (env var vs config file)
- Temporal split reproducibility/seed handling
- Strictness of temporal ordering validation
- Rejected sample handling (log vs quarantine)
- Duplicate detection scope (exact vs near-duplicates)
- Balancing timing (before/after temporal split)

</decisions>

<specifics>
## Specific Ideas

- Reproducibility is important for academic thesis — cached datasets enable consistent experiments
- Detailed reports support thesis documentation (can cite exact preprocessing statistics)
- Conservative temporal handling preferred to ensure no leakage claims in thesis

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation-data-pipeline*
*Context gathered: 2026-02-09*
