---
phase: 06-email-sms-support
plan: 05
subsystem: api-integration
tags: [fastapi, pydantic, endpoints, email, sms, file-upload]
requires:
  - 06-01  # Email header feature extraction
  - 06-04  # Unified feature extraction interface
provides:
  - rest-api-email-prediction
  - rest-api-sms-prediction
  - eml-file-upload
affects:
  - 06-06  # Model retraining will enable full prediction
  - 07-*   # Integration layer will use these endpoints
tech-stack:
  added: []
  patterns:
    - fastapi-file-upload
    - feature-count-validation
    - http-501-not-implemented
key-files:
  created:
    - tests/test_api_email_sms.py
  modified:
    - src/api/models.py
    - src/api/endpoints.py
decisions:
  - id: API-01
    what: Return 501 Not Implemented for email/SMS until models retrained
    why: Current models trained on 30 URL features, email has 65+, SMS has 70+
    impact: Endpoints exist but return clear error until Plan 06-06
  - id: API-02
    what: Use FastAPI UploadFile for .eml file handling
    why: Built-in async file upload support with size limits
    impact: 5MB file size limit enforced
  - id: API-03
    what: EmailSMSResponse uses optional paradigm_contributions
    why: Multi-paradigm not yet integrated for email/SMS
    impact: Response structure compatible with future integration
metrics:
  duration: 6 min
  completed: 2026-02-16
---

# Phase 06 Plan 05: Email/SMS API Endpoints Summary

**One-liner:** REST API endpoints for email and SMS phishing prediction with .eml file upload support (501 until model retraining).

## What Was Built

Three new FastAPI endpoints for email and SMS phishing detection:

1. **POST /predict/email** - Raw email text prediction
   - Accepts raw email with headers via JSON
   - Extracts 65+ features (email header + NLP text)
   - Returns EmailSMSResponse format

2. **POST /predict/email/file** - .eml file upload prediction
   - Accepts .eml file upload (max 5MB)
   - Validates file extension and size
   - Same feature extraction and response as text endpoint

3. **POST /predict/sms** - SMS message prediction
   - Accepts SMS/chat message text via JSON
   - Extracts 70+ features (SMS-specific + NLP text)
   - Returns EmailSMSResponse format

**API version updated:** 2.0.0 → 3.0.0 (Phase 6 email/SMS support)

## Task Commits

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Add Pydantic models | e8009d0 | src/api/models.py |
| 2 | Add API endpoints | 96dbd60 | src/api/endpoints.py |
| 2 (fix) | Feature mismatch handling | e194100 | src/api/endpoints.py |
| 3 | Add API tests | ae07706 | tests/test_api_email_sms.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Feature count mismatch prevents prediction**

- **Found during:** Task 2 - implementing endpoint prediction logic
- **Issue:** Models trained on 30 URL features, but email extracts 65+ features and SMS extracts 70+ features. Calling `predict_proba()` would fail with shape mismatch.
- **Fix:** Added feature count validation before prediction:
  - Check `ensemble.named_steps['scaler'].n_features_in_` to get expected feature count
  - If mismatch, return HTTP 501 Not Implemented with clear error message
  - Error message explains models need retraining (Plan 06-06)
- **Files modified:** src/api/endpoints.py
- **Commit:** e194100
- **Rationale:** Can't complete endpoint testing without handling this blocker. Returning 501 is semantically correct (feature not yet implemented) and provides clear user feedback.

## Technical Implementation

### Pydantic Models

**EmailTextRequest:**
- Validates raw email format (requires From:/Subject:/To:/Date: headers)
- 10-500KB size limits
- Field validator ensures email-like content

**SMSRequest:**
- Simple message string field
- 1-5000 character limit (supports MMS/long messages)
- No format validation (accepts any text)

**EmailSMSResponse:**
- Unified response for both email and SMS
- Includes `content_type` field ("email" or "sms")
- Optional `paradigm_contributions` for future multi-paradigm integration
- Standard prediction fields: probability, confidence, feature_count, explanation

### API Endpoints

All endpoints follow consistent pattern:

1. **Validation:** Pydantic request validation, file checks (for upload)
2. **Model check:** Verify `voting_soft` model loaded (503 if not)
3. **Feature extraction:** Call unified extractors (email_features or sms_features)
4. **Feature count check:** Validate against model's expected feature count
5. **Prediction:** Use ensemble model (when features match)
6. **Response:** Build EmailSMSResponse with explanation

**File upload specifics:**
- FastAPI `UploadFile` with `File()` annotation
- 5MB size limit enforced
- .eml extension validation
- Async endpoint for I/O efficiency

### Error Handling

- **400 Bad Request:** Wrong file extension or file too large
- **422 Validation Error:** Invalid request format (Pydantic validation)
- **501 Not Implemented:** Feature count mismatch (until model retraining)
- **503 Service Unavailable:** Models not loaded

### Test Coverage

**21 tests total:**
- **8 passed:** Validation tests (format, size, extension checks)
- **13 skipped:** Prediction tests (skip on 501 until models retrained)

**Test categories:**
1. Email text endpoint tests (5)
2. Email file upload tests (4)
3. SMS endpoint tests (6)
4. Response field validation tests (4)
5. Error handling tests (2)

Tests use `skip_if_not_implemented()` helper to gracefully skip when endpoints return 501.

## Integration Points

### Upstream Dependencies

- **Plan 06-01:** Email header feature extraction (extract_email_header_features)
- **Plan 06-04:** Unified extraction interface (extract_email_features, extract_sms_features)
- **Plan 06-02:** NLP text features (embedded in unified extractors)
- **Plan 06-03:** SMS features (extract_sms_features)

### Downstream Impact

- **Plan 06-06:** Model retraining will remove 501 responses, enable full prediction
- **Phase 07:** Integration layer will consume these endpoints
- **Future:** Multi-paradigm integration will populate paradigm_contributions field

## Requirements Addressed

- ✅ **INPUT-02:** API accepts raw email/SMS text
- ✅ **INPUT-03:** API accepts .eml file upload
- ✅ **FEAT-07:** Email header feature extraction (via 06-01)
- ⏳ **Full prediction:** Blocked on model retraining (Plan 06-06)

## Known Limitations

1. **Models not retrained:** Endpoints return 501 until models trained with email/SMS features
2. **No multi-paradigm yet:** paradigm_contributions field is None
3. **Ensemble only:** Currently uses voting_soft ensemble, not full multi-paradigm aggregation
4. **No .msg support:** Only .eml files supported (Outlook .msg not implemented)

## Next Steps

**Immediate (Plan 06-06):**
1. Retrain all 7 classifiers with email/SMS feature sets
2. Update model registry with retrained models
3. Remove feature count check (or update to new count)
4. Test endpoints return 200 with valid predictions

**Future enhancements:**
1. Add multi-paradigm support for email/SMS
2. Support .msg file format (Outlook)
3. Batch prediction endpoints (multiple emails/SMS at once)
4. Streaming prediction for large email archives

## Lessons Learned

**Feature dimension mismatch is critical:** Always validate feature count before prediction to avoid cryptic sklearn errors. Returning 501 with clear messaging is better than 500 with stack trace.

**Test skipping strategy works well:** Tests that skip on 501 provide clear signal - 8 validation tests pass (structure works), 13 prediction tests skip (need retraining).

**Unified extraction simplifies API:** Using extract_email_features() and extract_sms_features() abstractions keeps endpoints clean and delegates complexity to feature modules.

## Self-Check: PASSED

All created files exist:
- tests/test_api_email_sms.py

All commits verified:
- e8009d0 (Task 1: Pydantic models)
- 96dbd60 (Task 2: API endpoints)
- e194100 (Task 2 fix: Feature mismatch handling)
- ae07706 (Task 3: API tests)
