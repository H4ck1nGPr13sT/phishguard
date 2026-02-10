---
phase: 01-foundation-data-pipeline
plan: 02
subsystem: data-pipeline
tags: [python, pandas, pandera, validation, data-quality, deduplication]

# Dependency graph
requires:
  - phase: 01-foundation-data-pipeline
    plan: 01
    provides: Dataset downloaders and project structure
provides:
  - Pandera validation schemas for phishing datasets
  - Data quality checks and deduplication utilities
  - Multi-source dataset merger with standardized output format
  - Validation reporting with rejection reasons and statistics
affects: [02-preprocessing, temporal-splitting, model-training]

# Tech tracking
tech-stack:
  added: []
  patterns: [pandera validation, lazy error collection, source-specific column mapping]

key-files:
  created:
    - src/data/validators/__init__.py
    - src/data/validators/schemas.py
    - src/data/validators/quality.py
    - src/data/preprocessors/__init__.py
    - src/data/preprocessors/merger.py
  modified: []

key-decisions:
  - "Lazy validation with SchemaErrors collection to filter invalid rows instead of failing"
  - "Empty string for UCI ML urls (feature-only dataset) to distinguish from null/missing"
  - "Exact deduplication as default, with fuzzy option for normalized URL matching"
  - "Preserve all UCI ML feature columns as additional columns in merged dataset"

patterns-established:
  - "Pandera DataFrameSchema with custom checks for domain-specific validation"
  - "Validation returns (valid_df, report) tuple for partial success handling"
  - "Merger standardizes columns with source-specific mapping logic"
  - "Quality reports use comprehensive metrics without modifying data"

# Metrics
duration: 3min
completed: 2026-02-10
---

# Phase 01 Plan 02: Data Validation & Merger Summary

**Pandera validation schemas with detailed reporting, quality checks, and multi-source dataset merger for PhishTank, UCI ML, and Nazario datasets**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-10T18:19:10Z
- **Completed:** 2026-02-10T18:22:16Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- PhishingDataSchema with Pandera for url, label, content, timestamp, source columns
- URL validation accepts http/https prefixes or empty strings (for UCI feature-based data)
- Label validation enforces binary 0/1 classification
- Source validation restricts to phishtank/uci_ml/nazario
- validate_dataset filters invalid rows with lazy error collection, returns detailed report
- deduplicate_dataset with exact and fuzzy URL matching options
- check_data_quality generates comprehensive quality metrics without modification
- merge_datasets standardizes columns across PhishTank (verified_at), UCI ML (Result, features), and Nazario (body, date)
- Merger preserves UCI ML feature columns as additional columns in merged output
- All functions have comprehensive docstrings with Args, Returns, Example sections

## Task Commits

Each task was committed atomically:

1. **Task 1: Pandera validation schemas** - `2bcff81` (feat)
2. **Task 2: Quality checks and dataset merger** - `1fd67d6` (feat)

## Files Created/Modified

- `src/data/validators/__init__.py` - Module exports for PhishingDataSchema, validate_dataset, deduplicate_dataset, check_data_quality
- `src/data/validators/schemas.py` - Pandera schema definition with custom URL validation check
- `src/data/validators/quality.py` - Deduplication (exact/fuzzy) and quality reporting functions
- `src/data/preprocessors/__init__.py` - Module exports for merge_datasets
- `src/data/preprocessors/merger.py` - Multi-source dataset standardization and merging

## Decisions Made

**Lazy validation approach:** Used `lazy=True` with Pandera to collect all validation errors at once, then filter invalid rows instead of failing completely. This allows partial data recovery and detailed rejection reporting.

**Empty string for UCI ML URLs:** UCI ML dataset has features only (no raw URLs). Used explicit empty string `''` instead of None/NaN to distinguish from missing data and pass validation.

**Fuzzy deduplication option:** Implemented both exact and fuzzy URL matching. Fuzzy normalizes URLs (lowercase, strip trailing slash, remove www.) before deduplication to catch variations of the same URL.

**UCI ML feature preservation:** In merge_datasets, all UCI ML feature columns are preserved as additional columns in the merged DataFrame. Only Result column is mapped to label, all other columns pass through.

**Source-specific column mapping:**
- PhishTank: verified_at → timestamp
- UCI ML: Result → label (-1→0, 1→1), features preserved
- Nazario: body → content, date → timestamp

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Pandera deprecation warning:** Pandera warns about importing from top-level module (`import pandera as pa`). Future version will require `import pandera.pandas as pa`. Not blocking, but should be updated in future maintenance.

**Pandas concat FutureWarning:** DataFrame concatenation with empty/all-NA columns shows deprecation warning. Not blocking, behavior is correct. Will resolve naturally when Pandas updates.

## Next Phase Readiness

**Ready for Phase 02 (Preprocessing):**
- Data validation schemas operational and tested
- Quality checks can identify data issues before processing
- Dataset merger combines multiple sources into unified format
- UCI ML features preserved for both URL-based and feature-based modeling

**Validation capabilities:**
- Empty content detection
- Invalid URL filtering (non-http/https protocols)
- Label constraint enforcement (binary 0/1)
- Duplicate URL detection and removal
- Comprehensive quality reporting with source distribution and class balance

**No blockers for next phase.**

---
*Phase: 01-foundation-data-pipeline*
*Completed: 2026-02-10*

## Self-Check: PASSED
