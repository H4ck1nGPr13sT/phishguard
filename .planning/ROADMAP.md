# Roadmap: PhishGuard

## Overview

PhishGuard delivers a multi-paradigm phishing detection system that integrates 7 ML classifiers, genetic algorithm optimization, rule-based expert systems, and Bayesian probabilistic analysis. The roadmap starts with foundational data handling and temporal validation (Phase 1-2), expands to multi-paradigm ensemble detection with genetic optimization (Phase 3-5), adds multimodal analysis for email, SMS, and images with OCR (Phase 6-7), then completes the system with explainability, batch processing, and comprehensive documentation (Phase 8-10). Each phase builds incrementally, addressing critical pitfalls (temporal leakage, concept drift, class imbalance) early while demonstrating core differentiator (classifier disagreement as signal) by Phase 3.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation & Data Pipeline** - Establish data acquisition, temporal validation, and quality controls ✓ 2026-02-10
- [x] **Phase 2: Core ML Pipeline - URL Detection MVP** - Single-classifier URL phishing detector with FastAPI endpoint ✓ 2026-02-11
- [x] **Phase 3: ML Ensemble Expansion** - 7-classifier ensemble with voting and disagreement detection ✓ 2026-02-11
- [x] **Phase 4: Genetic Algorithm Optimization** - Hyperparameter tuning and model versioning ✓ 2026-02-12
- [x] **Phase 5: Alternative Detection Paradigms** - Rule-based expert system and Bayesian probabilistic analysis ✓ 2026-02-13
- [x] **Phase 6: Email & SMS Support** - Expand input types with NLP feature extraction ✓ 2026-02-17
- [ ] **Phase 7: OCR & Visual Analysis** - Image-based phishing detection with text extraction
- [ ] **Phase 8: Batch Processing & Web Interface** - User-facing web application and CSV batch analysis
- [ ] **Phase 9: Explainability & Dashboard** - SHAP/LIME explanations and multi-classifier comparison UI
- [ ] **Phase 10: Evaluation & Documentation** - Academic documentation and comprehensive evaluation

## Phase Details

### Phase 1: Foundation & Data Pipeline
**Goal**: Establish data acquisition, preprocessing, and quality validation infrastructure that prevents temporal leakage and handles class imbalance.

**Depends on**: Nothing (first phase)

**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DOC-01, DOC-02

**Success Criteria** (what must be TRUE):
  1. System downloads and preprocesses public phishing datasets (PhishTank, UCI ML Repository)
  2. System implements temporal train-test split (all training data before all test data)
  3. System handles class imbalance using SMOTE/undersampling with configurable ratios
  4. System validates data quality and rejects malformed/mislabeled samples
  5. System caches extracted features for reuse across model training runs

**Plans**: 4 plans

Plans:
- [x] 01-01-PLAN.md — Project setup and dataset downloaders
- [x] 01-02-PLAN.md — Data validation and merger
- [x] 01-03-PLAN.md — Temporal split and class balancing
- [x] 01-04-PLAN.md — Pipeline orchestration and documentation

### Phase 2: Core ML Pipeline - URL Detection MVP
**Goal**: Functional end-to-end URL phishing detector with single classifier (Random Forest), feature extraction, and REST API endpoint responding sub-second.

**Depends on**: Phase 1

**Requirements**: INPUT-01, FEAT-01, FEAT-05, FEAT-08, ML-01, ML-08, MODEL-01, MODEL-02, EVAL-01, EVAL-02, EVAL-03

**Success Criteria** (what must be TRUE):
  1. System accepts URL via FastAPI endpoint and returns phishing probability
  2. System extracts 30+ URL features (domain age, length, HTTPS, suspicious patterns)
  3. System trains Random Forest classifier achieving 90%+ accuracy on temporal test set
  4. System responds within 500ms for single URL analysis
  5. System saves and loads trained models without retraining

**Plans**: 5 plans

Plans:
- [x] 02-01-PLAN.md — URL feature extraction pipeline (30+ features)
- [x] 02-02-PLAN.md — Model training and evaluation (Random Forest + metrics)
- [x] 02-03-PLAN.md — FastAPI REST API with /predict endpoint
- [x] 02-04-PLAN.md — Integration tests and dependency updates
- [x] 02-05-PLAN.md — Human verification of complete system

### Phase 3: ML Ensemble Expansion
**Goal**: 7-classifier ensemble with soft/hard/stacking voting that exposes individual predictions and detects classifier disagreements via normalized entropy.

**Depends on**: Phase 2

**Requirements**: ML-02, ML-03, ML-04, ML-05, ML-06, ML-07, ENS-01, ENS-02, ENS-03, ENS-04, ENS-05, WEB-05

**Success Criteria** (what must be TRUE):
  1. System runs 7 classifiers (Random Forest, SVM, MLP, Gradient Boosting, Logistic Regression, Naive Bayes, Decision Tree) on same input
  2. System aggregates predictions using soft voting (average probabilities) and hard voting (majority vote)
  3. System calculates and displays disagreement score (normalized entropy across classifiers)
  4. System flags edge cases when disagreement exceeds threshold (e.g., entropy > 0.7)
  5. Web interface shows side-by-side comparison of all classifier predictions with confidence scores

**Plans**: 4 plans

Plans:
- [x] 03-01-PLAN.md — Train 6 additional classifiers (SVM, MLP, GB, XGB, LR, NB, DT)
- [x] 03-02-PLAN.md — Create ensemble models (soft voting, hard voting, stacking)
- [x] 03-03-PLAN.md — Disagreement detection and ensemble API endpoint
- [x] 03-04-PLAN.md — Human verification of ensemble system

### Phase 4: Genetic Algorithm Optimization
**Goal**: Automated hyperparameter optimization for all 7 classifiers using DEAP genetic algorithm framework with MLflow tracking and model versioning.

**Depends on**: Phase 3

**Requirements**: GA-01, GA-02, GA-03, GA-04, GA-05, GA-06, MODEL-03, MODEL-04, MODEL-05, EVAL-04

**Success Criteria** (what must be TRUE):
  1. System optimizes hyperparameters for all 7 classifiers using genetic algorithm (tournament selection, single-point crossover, mutation)
  2. System maximizes F1-score using 5-fold cross-validation as fitness function
  3. System tracks optimization runs in MLflow with fitness history across generations
  4. System saves both baseline and optimized models with version tags
  5. System compares baseline vs. optimized performance showing measurable improvement (5-10% accuracy gain)

**Plans**: 6 plans

Plans:
- [x] 04-01-PLAN.md — GA foundation and search spaces (DEAP, MLflow, fitness function)
- [x] 04-02-PLAN.md — Individual classifier optimization (all 7 classifiers)
- [x] 04-03-PLAN.md — Feature selection optimization (GA-02)
- [x] 04-04-PLAN.md — Ensemble weight optimization (GA-03)
- [x] 04-05-PLAN.md — Model versioning and comparison (MODEL-03/04/05, EVAL-04)
- [x] 04-06-PLAN.md — Testing and human verification

### Phase 5: Alternative Detection Paradigms
**Goal**: Integrate rule-based expert system and Bayesian probabilistic classifier with ML ensemble to complete multi-paradigm architecture.

**Depends on**: Phase 3

**Requirements**: RULE-01, RULE-02, RULE-03, RULE-04, RULE-05, RULE-06, RULE-07, PROB-01, PROB-02, PROB-03, PROB-04, AGG-01, AGG-02, AGG-03, AGG-04

**Success Criteria** (what must be TRUE):
  1. Rule-based system fires weighted rules for phishing indicators (urgent keywords, shortened URLs, IP addresses, homoglyphs)
  2. Bayesian system calculates posterior probability P(phishing|features) using Naive Bayes and custom model
  3. Aggregation layer combines ML ensemble, rule-based, and Bayesian predictions with configurable weights
  4. System detects paradigm disagreements (e.g., ML says 95% phishing, Bayesian says 40%) and flags for review
  5. Final verdict includes contributions from all three paradigms with confidence score and active rules list

**Plans**: 5 plans

Plans:
- [x] 05-01-PLAN.md — Rule-based expert system with weighted YAML rules
- [x] 05-02-PLAN.md — Bayesian probabilistic classifier (GaussianNB)
- [x] 05-03-PLAN.md — Multi-paradigm aggregation layer with disagreement detection
- [x] 05-04-PLAN.md — /predict/multi-paradigm API endpoint
- [x] 05-05-PLAN.md — Testing and human verification

### Phase 6: Email & SMS Support
**Goal**: Expand from URL-only to email and SMS analysis with NLP-based feature extraction (headers, sentiment, stylometry).

**Depends on**: Phase 2

**Requirements**: INPUT-02, INPUT-03, FEAT-02, FEAT-03, FEAT-04, FEAT-06, FEAT-07

**Success Criteria** (what must be TRUE):
  1. System parses raw email text and .eml files extracting headers (SPF, DKIM, sender domain)
  2. System parses SMS/chat messages extracting text content
  3. System extracts NLP features (lexical n-grams, syntactic structure, stylometric complexity, sentiment/urgency)
  4. System retrains all classifiers with expanded feature set including email/SMS-specific features
  5. System handles email, SMS, and URL inputs via unified API with content-type detection

**Plans**: 7 plans

Plans:
- [x] 06-01-PLAN.md — Email parser and header feature extraction
- [x] 06-02-PLAN.md — NLP text feature extraction (spaCy, textstat)
- [x] 06-03-PLAN.md — SMS feature extraction with shortened URL detection
- [x] 06-04-PLAN.md — Unified feature extractor integration
- [x] 06-05-PLAN.md — API endpoints for email and SMS prediction
- [x] 06-06-PLAN.md — Model retraining with expanded features
- [x] 06-07-PLAN.md — Testing and human verification

### Phase 7: OCR & Visual Analysis
**Goal**: Image-based phishing detection with OCR text extraction (EasyOCR) and visual similarity analysis for brand logo detection.

**Depends on**: Phase 6

**Requirements**: INPUT-04, INPUT-06, INPUT-07

**Success Criteria** (what must be TRUE):
  1. System extracts text from images (PNG, JPG, screenshots) using EasyOCR with preprocessing for low-quality images
  2. System analyzes visual features (layout structure, logo presence, color schemes, suspicious UI elements)
  3. System handles OCR processing asynchronously to avoid blocking (<500ms API response requirement)
  4. System detects visual similarity to legitimate brands using perceptual hashing or CNN embeddings
  5. System combines OCR-extracted text analysis with visual feature analysis for final verdict

**Plans**: TBD

Plans:
- [ ] To be planned

### Phase 8: Batch Processing & Web Interface
**Goal**: User-facing web application with form input, file upload (CSV batch, .eml, images), and responsive design for mobile/desktop.

**Depends on**: Phase 2

**Requirements**: INPUT-05, WEB-01, WEB-02, WEB-03, WEB-07, WEB-08

**Success Criteria** (what must be TRUE):
  1. Web interface displays form for pasting text/URL with submit button
  2. Web interface accepts file uploads (CSV for batch, .eml for email, PNG/JPG for images)
  3. Web interface displays analysis results with phishing verdict and confidence level (Low/Medium/High/Critical)
  4. System processes CSV batch uploads asynchronously and displays progress/results table
  5. Web interface is responsive and functional on mobile browsers and desktop

**Plans**: TBD

Plans:
- [ ] To be planned

### Phase 9: Explainability & Dashboard
**Goal**: SHAP/LIME feature importance explanations and multi-classifier comparison dashboard with visualization of disagreements.

**Depends on**: Phase 5

**Requirements**: EXPL-01, EXPL-02, EXPL-03, EXPL-04, EXPL-05, WEB-04, WEB-06

**Success Criteria** (what must be TRUE):
  1. System displays which expert rules fired with weights and justifications
  2. System displays SHAP or LIME feature importance showing top 10 contributing features for ML predictions
  3. Dashboard visualizes predictions from all classifiers (7 ML + rule-based + Bayesian) with bar chart comparison
  4. System explains disagreements when present (e.g., "SVM and Naive Bayes disagree due to URL length vs. lexical features")
  5. System generates natural language explanation summarizing verdict (e.g., "Flagged as phishing because domain registered 2 days ago, uses PayPal branding, and contains urgent language")

**Plans**: TBD

Plans:
- [ ] To be planned

### Phase 10: Evaluation & Documentation
**Goal**: Academic-grade documentation with theoretical background, architecture diagrams, comprehensive evaluation, and API documentation meeting thesis requirements.

**Depends on**: Phase 4

**Requirements**: EVAL-05, EVAL-06, DOC-03, DOC-04, DOC-05, DOC-06, DOC-07

**Success Criteria** (what must be TRUE):
  1. System analyzes impact of feature groups (URL, lexical, visual, etc.) on classification accuracy
  2. System generates exportable evaluation reports (PDF/CSV) with confusion matrices, ROC curves, and metric tables
  3. API is documented with OpenAPI/Swagger specification with interactive testing interface
  4. Documentation includes architecture diagrams (system components, data flow, classification pipeline)
  5. Documentation includes theoretical descriptions of all algorithms (ML classifiers, genetic algorithm, Bayesian networks, rule-based systems) meeting academic thesis standards

**Plans**: TBD

Plans:
- [ ] To be planned

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Data Pipeline | 4/4 | ✓ Complete | 2026-02-10 |
| 2. Core ML Pipeline - URL Detection MVP | 5/5 | ✓ Complete | 2026-02-11 |
| 3. ML Ensemble Expansion | 4/4 | ✓ Complete | 2026-02-11 |
| 4. Genetic Algorithm Optimization | 6/6 | ✓ Complete | 2026-02-12 |
| 5. Alternative Detection Paradigms | 5/5 | ✓ Complete | 2026-02-13 |
| 6. Email & SMS Support | 7/7 | ✓ Complete | 2026-02-17 |
| 7. OCR & Visual Analysis | 0/TBD | Not started | - |
| 8. Batch Processing & Web Interface | 0/TBD | Not started | - |
| 9. Explainability & Dashboard | 0/TBD | Not started | - |
| 10. Evaluation & Documentation | 0/TBD | Not started | - |

---
*Roadmap created: 2026-02-09*
*Last updated: 2026-03-08*
