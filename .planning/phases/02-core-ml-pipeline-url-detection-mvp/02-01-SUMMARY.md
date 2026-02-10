---
phase: 02-core-ml-pipeline-url-detection-mvp
plan: 01
type: summary
completed: 2026-02-10
duration: 3 min

subsystem: features
tags: [feature-extraction, url-analysis, ml-preprocessing, tldextract, pytest]

dependencies:
  requires: [01-foundation-data-pipeline]
  provides: [url-feature-extraction-30-features]
  affects: [02-02-model-training, 02-03-api-inference]

tech-stack:
  added: [tldextract>=5.0, pytest>=8.0]
  patterns: [feature-extraction-pipeline, shannon-entropy, url-parsing]

key-files:
  created:
    - src/features/__init__.py
    - src/features/url_features.py
    - src/features/extractors.py
    - tests/test_features.py
  modified:
    - requirements.txt

decisions:
  - id: FE-01
    context: "Feature extraction needs robust domain parsing"
    decision: "Use tldextract for domain parsing (handles Public Suffix List edge cases like co.uk, github.io)"
    rationale: "urllib.parse doesn't handle multi-level TLDs correctly. tldextract uses Public Suffix List for accurate domain/subdomain/TLD extraction"
    alternatives: "urllib.parse (insufficient), manual regex (error-prone)"

  - id: FE-02
    context: "Need to detect suspicious URLs"
    decision: "Suspicious TLD list: tk, ml, ga, cf, gq, xyz, pw, cc"
    rationale: "Research shows these TLDs are commonly used in phishing campaigns"
    alternatives: "Larger list (more false positives), no TLD filtering (miss pattern)"

  - id: FE-03
    context: "Feature extraction must handle edge cases"
    decision: "Return default dict with zeros for empty/invalid URLs"
    rationale: "Prevents crashes, ensures consistent 30-feature output for all inputs"
    alternatives: "Raise exceptions (breaks pipeline), skip invalid URLs (loses data)"

metrics:
  test-coverage: 29 test cases
  features-extracted: 30
  performance: "<50ms per URL (verified in tests)"
  all-tests-passed: true
---

# Phase 2 Plan 01: URL Feature Extraction Module Summary

**One-liner:** Shannon entropy-based URL feature extractor with 30 numeric features using tldextract for robust domain parsing, achieving <50ms extraction time.

## What Was Built

Created a comprehensive URL feature extraction module that converts raw URL strings into 30 numeric features for machine learning model input. The module extracts:

1. **Length features (7):** url_length, domain_length, path_length, hostname_length, subdomain_length, tld_length, query_length
2. **Character count features (10):** dot_count, hyphen_count, underscore_count, slash_count, question_count, equal_count, at_count, ampersand_count, digit_count, special_char_count
3. **Binary indicator features (8):** has_https, has_ip, has_port, has_subdomain, has_query, has_fragment, is_valid, has_suspicious_tld
4. **Structure features (5):** path_depth, subdomain_count, param_count, entropy (Shannon entropy), digit_ratio

The implementation uses:
- `tldextract` for robust domain parsing (handles Public Suffix List edge cases)
- `urllib.parse` for URL parsing (scheme, netloc, path, query, fragment)
- Shannon entropy calculation for randomness detection
- Comprehensive error handling for edge cases (empty URLs, IP addresses, unicode)

## Task Commits

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Create URL feature extraction module | baba0ad | src/features/*.py |
| 2 | Add comprehensive unit tests | 8b594e0 | tests/test_features.py, requirements.txt |

## Verification Results

All verification criteria met:

1. **Module imports correctly:** `from src.features import extract_url_features` ✓
2. **Returns 30+ numeric features:** All features are int or float ✓
3. **All unit tests pass:** 29/29 tests passed ✓
4. **Performance:** <50ms per URL (verified in performance tests) ✓

Example output:
```python
>>> from src.features import extract_url_features
>>> features = extract_url_features('https://example.com/path?query=1')
>>> len(features)
30
>>> features['has_https']
1
>>> features['url_length']
32
```

## Decisions Made

**FE-01: Use tldextract for domain parsing**
- **Context:** Feature extraction needs to correctly parse domains with multi-level TLDs (co.uk, github.io)
- **Decision:** Use `tldextract` library which implements Public Suffix List
- **Impact:** Accurate subdomain/domain/TLD extraction for all edge cases

**FE-02: Suspicious TLD list**
- **Context:** Need to flag URLs with TLDs commonly used in phishing
- **Decision:** Detect 8 TLDs: tk, ml, ga, cf, gq, xyz, pw, cc
- **Impact:** Binary feature `has_suspicious_tld` for model training

**FE-03: Default features for invalid URLs**
- **Context:** Edge cases (empty URLs, malformed) must not crash pipeline
- **Decision:** Return dict with 30 features all set to 0/0.0
- **Impact:** Consistent output shape, pipeline resilience

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing dependencies**
- **Found during:** Task 2 (test execution)
- **Issue:** pytest and tldextract not in requirements.txt, tests couldn't run
- **Fix:** Added `pytest>=8.0` and `tldextract>=5.0` to requirements.txt
- **Files modified:** requirements.txt
- **Commit:** 8b594e0

No other deviations - plan executed as written.

## Key Learnings

1. **tldextract is essential for robust URL parsing:** urllib.parse fails on multi-level TLDs like co.uk, forums.bbc.co.uk. tldextract handles these correctly using Public Suffix List.

2. **Shannon entropy is effective for randomness detection:** Phishing URLs often have high entropy due to obfuscated/random characters. Simple to calculate, valuable feature.

3. **Edge case handling prevents pipeline failures:** Returning default dict with zeros for invalid URLs ensures consistent output shape and prevents downstream crashes.

4. **Performance is excellent:** Feature extraction averages <10ms per URL (well under 50ms requirement), making real-time inference feasible.

## Integration Points

**Upstream dependencies:**
- None (foundation module)

**Downstream consumers:**
- `02-02`: Model training will use these features to train Random Forest classifier
- `02-03`: FastAPI inference will call `extract_url_features()` for real-time predictions
- Phase 1 data pipeline: Can integrate feature extraction for URL-based datasets

**API surface:**
```python
# Main function (public API)
extract_url_features(url: str) -> Dict[str, float]

# Helper functions (also exported)
calculate_entropy(text: str) -> float
extract_length_features(url, parsed, extracted) -> Dict[str, int]
extract_char_features(url: str) -> Dict[str, int]
extract_binary_features(url, parsed, extracted) -> Dict[str, int]
extract_structure_features(url, parsed, extracted) -> Dict[str, float]
```

## Next Phase Readiness

**Ready for 02-02 (Model Training):**
- ✅ Feature extraction produces 30 numeric features
- ✅ All features are numeric (no strings, no None values)
- ✅ Performance validated (<50ms per URL)
- ✅ Edge cases handled (empty, invalid, unicode URLs)
- ✅ Comprehensive test coverage (29 test cases)

**Blockers:** None

**Concerns/Risks:**
- **Feature selection:** Not all 30 features may be equally important. Model training should analyze feature importance and consider reducing to top-k features if needed.
- **Domain age feature missing:** Research suggests domain age is valuable for phishing detection, but requires WHOIS lookups (200-500ms). Deferred to Phase 2 or 3 based on accuracy requirements.
- **Suspicious TLD list may need updates:** List based on 2026 research, but phishing TLD trends change. Should monitor and update list periodically.

## Statistics

- **Execution time:** 3 minutes
- **Files created:** 4
- **Files modified:** 1
- **Lines of code added:** ~800
- **Test cases:** 29
- **Test pass rate:** 100%
- **Features extracted:** 30
- **Performance:** <10ms avg per URL

## Self-Check: PASSED

All files verified:
- ✓ src/features/__init__.py
- ✓ src/features/url_features.py
- ✓ src/features/extractors.py
- ✓ tests/test_features.py

All commits verified:
- ✓ baba0ad (Task 1)
- ✓ 8b594e0 (Task 2)
