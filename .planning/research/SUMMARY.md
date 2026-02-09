# Project Research Summary

**Project:** Phishing Detection ML System
**Domain:** Cybersecurity - Phishing Detection and Prevention
**Researched:** 2026-02-09
**Confidence:** HIGH

## Executive Summary

This is a multi-paradigm machine learning system for phishing detection that integrates 7 classical ML classifiers, genetic algorithm optimization, rule-based expert systems, and Bayesian probabilistic analysis. The core differentiator is treating classifier disagreement as valuable signal rather than noise - when models disagree, it indicates edge cases requiring deeper analysis. The system must handle multiple input types (URLs, emails, SMS, images) and provide explainable verdicts with confidence scoring.

The recommended approach uses Python 3.11+ with scikit-learn 1.8.0 as the ML foundation, XGBoost/CatBoost for advanced gradient boosting, DEAP for genetic algorithm optimization, and FastAPI for the REST API layer. Start with URL-based detection using 7 ML classifiers with voting aggregation (Phase 1), add genetic algorithm optimization and alternative paradigms (Phase 2-3), then expand to multimodal analysis with OCR and visual detection (Phase 4-5). The phased approach is critical because temporal data leakage, concept drift, and class imbalance are severe risks that must be addressed architecturally from day one.

Key risks include temporal evaluation pitfalls (random splits overestimate performance by 10-20%), concept drift causing rapid model degradation (phishing tactics evolve weekly), and real-time performance constraints (must respond <500ms). Mitigation requires strict temporal train-test splits, continuous retraining infrastructure, and latency budgets enforced from Phase 1. The multi-paradigm architecture provides robustness against adversarial attacks and evasion techniques that defeat single-model systems.

## Key Findings

### Recommended Stack

The stack centers on mature, production-ready Python ML libraries optimized for classical machine learning rather than deep learning. Python 3.11 offers 10-60% performance improvements over 3.10 while maintaining full ML library compatibility. scikit-learn 1.8.0 (released December 2025) provides all 7 required classifiers with excellent interoperability and stable APIs.

**Core technologies:**
- **Python 3.11+**: Runtime with significant performance improvements - required by scikit-learn 1.8.0, avoid 3.13 experimental features
- **scikit-learn 1.8.0**: Primary ML framework for 7 classifiers (Random Forest, SVM, MLP, Gradient Boosting, Logistic Regression, Naive Bayes, Decision Tree) - industry standard with mature APIs
- **XGBoost 3.1.3**: Advanced gradient boosting achieving 98.4% accuracy in phishing research - superior to scikit-learn's GradientBoosting
- **CatBoost 1.2.8**: Categorical feature handling with minimal preprocessing - ideal for URL/domain features
- **DEAP 1.4.3**: Genetic algorithm framework for hyperparameter optimization - 10x faster than GridSearch with similar accuracy
- **FastAPI 0.128.5**: REST API framework - 4x faster than Flask (20K+ vs 5K req/sec), native async support, auto-generated OpenAPI docs
- **EasyOCR 1.7.2**: OCR engine - 4-7x faster than Tesseract, robust with low-quality images and multi-line text
- **spaCy 3.8.11**: Production NLP for email/SMS analysis - state-of-art speed and accuracy, preferred over NLTK
- **MLflow 3.9.0**: ML lifecycle management - experiment tracking, model registry, deployment orchestration
- **pandas 3.0.0**: Tabular data manipulation with Apache Arrow support and optional GPU acceleration
- **imbalanced-learn 0.14.1**: SMOTE and SMOTETomek for handling imbalanced phishing datasets - achieves 97.7% accuracy in research

**Critical version compatibility:** All packages compatible with Python 3.11. Use Python 3.11.x for best balance of stability, performance, and library compatibility. Avoid Python 3.13 experimental features for production.

**Installation pattern:** Use Poetry for dependency management (modern resolver, faster than Pipenv with complex ML dependencies). Start with minimal stack (scikit-learn, pandas, FastAPI) for Phase 1, add XGBoost/DEAP in Phase 2, OCR/NLP in Phase 4.

### Expected Features

Research reveals a clear distinction between table stakes features (expected in any phishing detector), competitive differentiators (this project's unique value), and anti-features (commonly requested but problematic).

**Must have (table stakes):**
- **URL Analysis** - Core phishing indicator present in 90%+ attacks; extract 30+ features (domain age, HTTPS, suspicious patterns, redirects)
- **Multi-Format Input** - Handle email (headers + body), SMS, URLs, raw text, images with embedded text
- **Real-Time Detection** - Sub-second response time; phishing campaigns launch within hours, weekly scans ineffective
- **Machine Learning Classification** - Industry standard requires 95%+ accuracy with ensemble methods (Random Forest, SVM, etc.)
- **Visual Similarity Detection** - Phishing pages mimic legitimate sites; requires perceptual hashing and screenshot comparison
- **Confidence Scoring** - Binary yes/no insufficient; output probability scores or risk levels (Low/Medium/High/Critical)
- **Batch Processing** - Enterprise users need bulk URL scanning, CSV upload, async job processing

**Should have (competitive differentiators):**
- **Multi-Paradigm Integration (7 ML + Rule-Based + Bayesian)** - CORE DIFFERENTIATOR: when classifiers disagree, flag for deeper analysis; consensus voting provides high confidence
- **Explainability Layer (XAI)** - SHAP/LIME for feature importance + LLM translation to natural language (e.g., "Flagged because domain registered 2 days ago and uses PayPal branding")
- **Multi-Modal Analysis Dashboard** - Show how different detection methods rated same sample; side-by-side comparison reveals discrepancies
- **Genetic Algorithm Hyperparameter Optimization** - Self-optimizing system adapts to new phishing patterns without manual retraining
- **Confidence Discrepancy Alerts** - When ML says 95% phishing but Bayesian says 40%, escalate for investigation
- **OCR + Visual Analysis** - Extract text from image-based phishing (screenshots, embedded images); attackers evade filters by converting text to images

**Defer (v2+):**
- **LLM-Powered Natural Language Explanations** - High computational cost, nice-to-have but not essential for v1
- **Real-Time URL Scanning Browser Extension** - Complex deployment, separate project scope
- **Interactive Sandbox Execution** - Security complexity and infrastructure overhead too high for academic project
- **Temporal Campaign Detection** - Requires significant historical data not available initially
- **Deep Learning Embeddings (Transformers)** - High computational requirements, incremental improvement over classical ML

**Anti-features (avoid):**
- **Real-Time Email Gateway Blocking** - Requires deep infrastructure integration; focus on detection/analysis API instead
- **100% Automated Response** - False positives inevitable; use confidence thresholds for tiered response
- **SMS/OTP-Based 2FA** - Not relevant to detection; out of scope
- **Global Blacklist Reliance** - 60%+ phishing uses domains <24 hours old; blacklists always lag

### Architecture Approach

Modern phishing detection systems follow a layered, modular architecture separating data ingestion, feature extraction, classification, and decision aggregation. The multi-paradigm approach requires parallel classification blocks (ML ensemble, rule-based, Bayesian, visual) with a sophisticated voting engine that detects and reports disagreements.

**Major components:**

1. **Data Ingestion Layer** - Input handlers for email, SMS, URL, text, image with content-type validation and sanitization
2. **Feature Extraction Pipeline** - Modular extractors (URL parser, email parser, NLP processor, OCR engine) that cache results and feed multiple classifiers
3. **Classification Layer** - Four parallel blocks:
   - ML Ensemble (7 classifiers: RF, SVM, MLP, GB, LR, NB, DT)
   - Rule-Based Expert System (heuristics, blacklists, domain-specific rules)
   - Bayesian Probabilistic System (P(phishing|features) using Bayes theorem)
   - Visual Analysis Module (CNN for fake logos, layout analysis)
4. **Decision Aggregation Layer** - Ensemble voting engine using soft voting with confidence weighting, conflict detection via normalized entropy, final prediction with individual classifier results exposed
5. **Presentation Layer** - FastAPI REST API, web UI for demonstrations, multi-classifier comparison dashboard
6. **Data Storage Layer** - Trained models (joblib/pickle), feature cache (Redis), results history (PostgreSQL/SQLite), configuration store

**Critical architectural patterns:**
- **Multi-Paradigm Ensemble with Conflict Detection** - Core value proposition; disagreements provide additional context for edge cases
- **Feature Extraction Pipeline with Caching** - Extract features once, cache, reuse across all classifiers; massive performance gain
- **Soft Voting with Confidence Weighting** - Weight votes by historical classifier performance; produces calibrated confidence scores
- **Genetic Algorithm Optimization Loop** - Offline hyperparameter tuning that runs independently; updates models without downtime

**Project structure:** Separate directories for ingestion/, feature_extraction/, classifiers/, aggregation/, api/, training/, with shared utils/ and clear boundaries. Training code isolated from inference code for reproducibility.

### Critical Pitfalls

Research identified 10 critical pitfalls with clear prevention strategies. The top 5 must be addressed architecturally:

1. **Temporal Data Leakage** - Random train-test splits overestimate performance by ignoring temporal evolution of phishing tactics. Models achieving 95%+ accuracy in testing show poor real-world performance when encountering new campaigns. PREVENTION: Use strict temporal splits (all training data before all test data), implement time-aware cross-validation, maintain recent holdout set (3-6 months) never used in training. ADDRESS IN PHASE 1.

2. **Concept Drift and Model Degradation** - Static models fail as attackers evolve tactics; performance degrades over weeks/months. LLM-generated phishing can be created in seconds with variations to evade detection. PREVENTION: Implement continuous drift detection, design event-driven retraining pipelines, use adaptive models with continual learning, maintain feedback loop where new phishing attempts feed back into training. ADDRESS IN PHASE 3-6.

3. **Class Imbalance and Dataset Bias** - Legitimate content vastly outnumbers phishing; models achieve high accuracy but poor recall on minority class. When combining sources, imbalance can be extreme (URLs 97%, email/SMS 3%). PREVENTION: Apply Borderline-SMOTE for balanced training, use GANs for synthetic samples, ensure proportional representation across attack vectors, cost-sensitive learning with higher penalties for false negatives. ADDRESS IN PHASE 1-3.

4. **Dataset Quality and Labeling Errors** - Ground truth labeling is subjective and error-prone. Documented case: phishing dataset had to remove 65% of samples during cleaning due to "404 Not Found" pages mislabeled as phishing. PREVENTION: Dual-review process with independent annotators, expert annotators with cybersecurity background, clear labeling guidelines with edge cases, automated quality checks, inter-annotator agreement tracking. ADDRESS IN PHASE 1.

5. **Over-Reliance on Indicator-Based Detection** - Static checks (blacklists, URL features, sender domain) are slow to update and unreliable against modern evasion (redirects, delayed execution, trusted platforms). Traditional defenses no longer sufficient against 2026 threat landscape. PREVENTION: Build layered detection combining indicators, behavioral analysis, ML predictions; implement sandbox for execution observation; use multiple paradigms (THIS IS THE PROJECT'S CORE STRENGTH). ADDRESS IN PHASE 2-4.

Additional critical pitfalls: False positive/negative cost imbalance (alert fatigue vs. missed threats), adversarial robustness (LLM-rephrased emails degrade detectors), real-time latency constraints (<500ms required but OCR takes 3-5s), poor feature engineering (external dependencies cause failures), inadequate OCR/visual analysis (QR codes in PDFs bypass link filters).

## Implications for Roadmap

Based on research findings, the project should follow an 8-phase structure that addresses dependencies, builds complexity incrementally, and mitigates critical pitfalls early.

### Phase 1: Core ML Pipeline - URL Detection MVP
**Rationale:** Establish end-to-end detection pipeline with single input type (URLs) and single classifier to validate architecture before adding complexity. Must implement temporal data handling and quality controls from day one to avoid rebuilding later.

**Delivers:** Functional URL phishing detector with Random Forest classifier, basic feature extraction (30+ URL features), FastAPI endpoint, temporal train-test split validation.

**Addresses Features:**
- URL Analysis (table stakes)
- Real-Time Detection foundation
- Basic ML Classification

**Avoids Pitfalls:**
- Temporal Data Leakage - implement strict temporal splits from start
- Dataset Quality - establish labeling process and quality checks
- Class Imbalance - apply SMOTE/stratified sampling in initial dataset

**Research Flags:** Standard pattern, well-documented in sklearn tutorials. Skip detailed research.

---

### Phase 2: ML Ensemble Expansion
**Rationale:** Add remaining 6 classifiers and implement voting aggregation to demonstrate multi-paradigm value proposition. This is the core differentiator and must come early.

**Delivers:** 7-classifier ensemble with soft voting, individual classifier results exposure, disagreement detection via entropy calculation, multi-classifier comparison view.

**Uses Stack:**
- scikit-learn 1.8.0 for all 7 classifiers
- XGBoost 3.1.3 to replace/augment scikit-learn GradientBoosting
- Custom voting engine implementation

**Implements Architecture:**
- Classification Layer with parallel ML models
- Decision Aggregation Layer with conflict detection
- Soft voting with confidence weighting

**Addresses Features:**
- Multi-Paradigm Integration (core differentiator)
- Confidence Scoring
- Multi-Classifier Results Display

**Avoids Pitfalls:**
- Over-Reliance on Single Model - ensemble provides robustness
- Adversarial Robustness - diverse architectures harder to fool simultaneously

**Research Flags:** Standard ensemble patterns. Skip research.

---

### Phase 3: Genetic Algorithm Optimization
**Rationale:** Hyperparameter tuning significantly improves accuracy (research shows 10x faster than GridSearch). Must come after baseline ensemble is working to have performance baseline for comparison.

**Delivers:** DEAP-based genetic algorithm optimizer, automated hyperparameter tuning for all 7 classifiers, optimized models with performance comparison, MLflow integration for experiment tracking.

**Uses Stack:**
- DEAP 1.4.3 for genetic algorithm framework
- MLflow 3.9.0 for tracking optimization runs
- joblib for model serialization

**Implements Architecture:**
- Genetic Algorithm Optimization Loop (offline component)
- Model versioning and comparison
- Retraining pipeline foundation

**Addresses Features:**
- Genetic Algorithm Optimization (differentiator)
- Continuous model improvement

**Avoids Pitfalls:**
- Concept Drift - establishes retraining infrastructure
- Sub-optimal Hyperparameters - systematic optimization vs. manual tuning

**Research Flags:** NEEDS RESEARCH - genetic algorithm fitness function design, multi-objective optimization (accuracy + latency), hyperparameter search spaces per classifier.

---

### Phase 4: Alternative Detection Paradigms
**Rationale:** Add rule-based expert system and Bayesian probabilistic system to complete multi-paradigm integration. Must come after ML ensemble is validated because these systems provide complementary signals.

**Delivers:** Rule-based expert system with domain heuristics, Bayesian probabilistic classifier, integrated voting across all paradigms (ML + Rules + Bayesian), enhanced disagreement analysis.

**Implements Architecture:**
- Rule-Based Expert System in Classification Layer
- Bayesian Probabilistic System in Classification Layer
- Multi-paradigm aggregation in Decision Aggregation Layer

**Addresses Features:**
- Complete Multi-Paradigm Integration
- Confidence Discrepancy Alerts (when paradigms disagree significantly)

**Avoids Pitfalls:**
- Over-Reliance on Indicator-Based Detection - combines multiple approaches
- Single Point of Failure - diversified detection methods

**Research Flags:** NEEDS RESEARCH - Bayesian network structure design, rule-based heuristics for modern phishing (2026 tactics), integration of probabilistic and deterministic systems.

---

### Phase 5: Email and SMS Support
**Rationale:** Expand from URL-only to multi-format input. Requires additional feature extraction but builds on validated classification infrastructure.

**Delivers:** Email parser (headers, body, attachments), SMS handler, email-specific features (SPF, DKIM, sender reputation), SMS-specific features, retrained models with expanded feature set.

**Uses Stack:**
- spaCy 3.8.11 for NLP-based email/SMS analysis
- Python email library for header parsing
- Updated feature extraction pipeline

**Implements Architecture:**
- Email Handler and SMS Handler in Data Ingestion Layer
- Text NLP Processor in Feature Extraction Layer
- Extended feature vectors for all classifiers

**Addresses Features:**
- Multi-Format Input (table stakes)
- NLP-based content analysis

**Avoids Pitfalls:**
- Class Imbalance - ensure proportional email/SMS representation
- Feature Engineering - validate features work across input types

**Research Flags:** Standard patterns for email parsing. Skip detailed research.

---

### Phase 6: OCR and Visual Analysis
**Rationale:** Image-based phishing is critical in 2026 threat landscape (QR codes, text-as-image evasion). Must come after text-based detection is solid because OCR is complex and latency-intensive.

**Delivers:** EasyOCR integration, image preprocessing pipeline, visual feature extraction (logo detection, layout analysis), CNN classifier for visual phishing, async processing with task queue (Celery + Redis).

**Uses Stack:**
- EasyOCR 1.7.2 for text extraction
- Pillow 10.4+ for image preprocessing
- OpenCV 4.11+ for visual analysis (optional)
- Celery + Redis for async processing

**Implements Architecture:**
- OCR Engine in Feature Extraction Layer
- Visual Analysis Module in Classification Layer
- Async processing pattern to avoid blocking (<500ms requirement)

**Addresses Features:**
- OCR + Visual Analysis (differentiator)
- Image-based phishing detection
- Visual Similarity Detection (table stakes)

**Avoids Pitfalls:**
- Real-Time Latency Constraints - async processing prevents blocking
- Inadequate OCR - robust preprocessing and fallback mechanisms
- Visual Analysis Failures - multi-OCR strategy, confidence thresholds

**Research Flags:** NEEDS RESEARCH - OCR preprocessing techniques for adversarial images, visual similarity algorithms (perceptual hashing), CNN architecture for brand logo detection.

---

### Phase 7: Explainability and Dashboard
**Rationale:** Once detection is working reliably, add explainability for trust and validation. Must come after all detection paradigms are integrated to explain complete system.

**Delivers:** SHAP/LIME integration for feature importance, explainable predictions showing which features contributed, enhanced web UI with visualization, multi-classifier comparison dashboard, confidence and disagreement displays.

**Uses Stack:**
- SHAP or LIME library for ML explainability
- Plotly/Streamlit for interactive dashboard
- FastAPI frontend integration

**Implements Architecture:**
- Explainability Layer post-processing classification results
- Enhanced Presentation Layer with rich UI

**Addresses Features:**
- Explainability Layer (differentiator)
- Multi-Modal Analysis Dashboard (differentiator)
- Basic Reporting Dashboard (table stakes)

**Avoids Pitfalls:**
- Black Box Predictions - users understand why flagged
- False Positive Management - explanations help users validate decisions

**Research Flags:** Standard SHAP/LIME patterns. Skip research.

---

### Phase 8: Production Hardening
**Rationale:** Final phase adds production-ready features: monitoring, caching, containerization, performance optimization. Deferred until core functionality is complete and validated.

**Delivers:** Prometheus metrics and Grafana dashboards, Redis feature caching, PostgreSQL results storage, Docker containerization, load balancing and auto-scaling setup, concept drift monitoring and alerting.

**Uses Stack:**
- Redis for caching
- PostgreSQL for persistent storage
- Prometheus + Grafana for monitoring
- Docker + Docker Compose for deployment

**Implements Architecture:**
- Feature Cache in Data Storage Layer
- Results History database
- Monitoring and alerting infrastructure

**Addresses Features:**
- Batch Processing at scale
- False Positive Management with persistent storage

**Avoids Pitfalls:**
- Concept Drift - continuous monitoring with automated alerts
- Real-Time Performance - caching and optimization
- Scalability - containerization and horizontal scaling

**Research Flags:** Standard DevOps patterns. Skip research.

---

### Phase Ordering Rationale

The 8-phase structure follows these principles based on research findings:

**Dependencies drive order:**
- Phase 1 (Core Pipeline) must come first - establishes architecture and data handling that all subsequent phases build on
- Phase 2 (Ensemble) depends on Phase 1 working - can't validate voting without baseline
- Phase 3 (GA Optimization) depends on Phase 2 - needs ensemble performance baseline
- Phase 4 (Alternative Paradigms) depends on Phase 2 - integrates with existing ensemble
- Phase 5 (Email/SMS) depends on Phase 1-4 - expands input types for validated classifiers
- Phase 6 (OCR/Visual) depends on Phase 5 - most complex input type, needs everything else working
- Phase 7 (Explainability) depends on Phase 2-6 - explains complete multi-paradigm system
- Phase 8 (Production) depends on all previous - hardening comes last

**Complexity increases incrementally:**
- Start simple: URL-only, single classifier (Phase 1)
- Add ensemble complexity (Phase 2)
- Add optimization complexity (Phase 3)
- Add paradigm diversity (Phase 4)
- Add input diversity (Phase 5-6)
- Add explainability (Phase 7)
- Add production features (Phase 8)

**Risk mitigation early:**
- Temporal data leakage addressed in Phase 1 (foundation)
- Class imbalance addressed in Phase 1 (foundation)
- Dataset quality addressed in Phase 1 (foundation)
- Concept drift infrastructure started in Phase 3, completed in Phase 8
- Adversarial robustness built through ensemble diversity (Phase 2-4)
- Latency constraints enforced from Phase 1, async added in Phase 6

**Core value demonstrated early:**
- Multi-paradigm integration proven in Phase 2-4 (core differentiator)
- Disagreement detection implemented in Phase 2
- Genetic algorithm optimization added in Phase 3
- OCR/visual deferred to Phase 6 (complex but not core value proof)

### Research Flags

**Phases needing deeper research during planning:**

- **Phase 3 (GA Optimization):** Genetic algorithm fitness function design is complex - must balance accuracy, latency, robustness. Multi-objective optimization with DEAP requires careful parameter space definition per classifier. Research hyperparameter search spaces, mutation/crossover strategies, fitness evaluation approaches.

- **Phase 4 (Alternative Paradigms):** Bayesian network structure design for phishing detection is non-trivial. Must research how to integrate probabilistic and deterministic systems in voting. Rule-based heuristics need updating for 2026 threat landscape (LLM-generated phishing, image-based evasion).

- **Phase 6 (OCR/Visual):** Image preprocessing for adversarial resistance needs research - attackers add noise, overlays, background modifications. Visual similarity algorithms (perceptual hashing vs. CNN embeddings) have trade-offs. CNN architecture for logo detection requires labeled brand logo dataset.

**Phases with standard patterns (skip detailed research):**

- **Phase 1 (Core Pipeline):** URL feature extraction and Random Forest classification extensively documented in sklearn tutorials and phishing research papers.

- **Phase 2 (Ensemble):** Ensemble voting patterns well-established. Soft voting implementation straightforward with sklearn.

- **Phase 5 (Email/SMS):** Email parsing and header analysis have standard Python libraries. spaCy NLP patterns well-documented.

- **Phase 7 (Explainability):** SHAP/LIME integration follows standard recipes for sklearn models.

- **Phase 8 (Production):** DevOps patterns (Docker, Redis, Prometheus) are standard practices.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against PyPI releases as of February 2026. Official documentation and version compatibility matrix confirmed. Alternative libraries identified with clear selection criteria. |
| Features | HIGH | Comprehensive analysis of commercial tools (Sublime, Arya.ai, CheckPhish), academic research (2017-2024 systematic review), and 2026 threat landscape. Table stakes vs. differentiators clearly delineated based on industry analysis. |
| Architecture | HIGH | Multiple architecture papers and production systems analyzed. Patterns validated across commercial deployments. Component responsibilities and data flow well-established in field. |
| Pitfalls | HIGH | 10 critical pitfalls identified from recent research (2025-2026 publications), systematic reviews, and documented failures. Prevention strategies backed by published solutions. Recovery costs estimated from project post-mortems. |

**Overall confidence: HIGH**

All research areas supported by official documentation (PyPI for stack), recent academic publications (2025-2026 for features/pitfalls), production system analysis (architecture), and systematic reviews (all areas). Confidence levels reflect source quality: official docs and recent systematic reviews provide high confidence, while implementation details and emerging techniques have medium confidence.

### Gaps to Address

**Minor gaps requiring validation during implementation:**

1. **Genetic Algorithm Convergence:** Research shows GA works well for hyperparameter optimization, but optimal population size, generation count, and mutation rates are problem-specific. Will need experimentation during Phase 3 to find best parameters for this 7-classifier ensemble.

2. **Bayesian Network Structure:** Research validates Bayesian approaches for phishing but doesn't prescribe exact network structure (naive Bayes vs. full Bayesian network). Will need to test different structures during Phase 4 and select based on performance.

3. **OCR Preprocessing Pipeline:** Research confirms EasyOCR superiority over Tesseract but specific preprocessing steps (deskewing, denoising, contrast enhancement) need tuning for adversarial images during Phase 6.

4. **Visual Similarity Thresholds:** Research shows visual similarity detection works but optimal similarity thresholds (what constitutes "too similar" to a brand) are subjective. Will need human validation and threshold tuning during Phase 6.

5. **Real-World Dataset Acquisition:** Research uses public datasets (PhishTank, UCI ML Repository) but real-world phishing samples from 2026 may have different characteristics. Will need to collect/validate recent samples during Phase 1 to ensure training data reflects current threat landscape.

**How to handle gaps:**

- **Phase 3 (GA):** Run parameter sweep experiments, use MLflow to track convergence metrics, select based on validation performance
- **Phase 4 (Bayesian):** Implement multiple Bayesian variants, compare performance, use simplest effective approach
- **Phase 6 (OCR/Visual):** Build preprocessing experimentation framework, test against adversarial examples, iterate based on accuracy metrics
- **Phase 1 (Dataset):** Supplement public datasets with recent PhishTank samples, validate labels manually, track data provenance

None of these gaps are blockers - all have clear validation strategies during implementation.

## Sources

### Primary (HIGH confidence)

**Stack - Official Documentation and PyPI:**
- scikit-learn 1.8.0 Documentation and PyPI (version confirmed Dec 2025)
- FastAPI PyPI v0.128.5 (released Feb 2026)
- MLflow Official v3.9.0 (released Jan 2026)
- spaCy PyPI v3.8.11 (released Nov 2025)
- XGBoost PyPI v3.1.3 (released Jan 2026)
- CatBoost PyPI v1.2.8 (released Apr 2025)
- pandas PyPI v3.0.0 (released Jan 2026)
- DEAP PyPI v1.4.3 (released May 2025)
- EasyOCR PyPI v1.7.2 (released Sep 2024)
- imbalanced-learn PyPI v0.14.1 (released Dec 2025)

**Features - 2026 Industry Analysis:**
- Best Phishing Simulation Tools for Enterprises (2026 Edition) - Hoxhunt
- AI-Powered Phishing Detection & Prevention Strategies for 2026 - USCS Institute
- Top phishing protection software in 2026 - Sublime Security
- Best anti-phishing tools (2026) - Guardio
- 10 Best Anti-Phishing Tools in 2026 - Cybersecurity News

**Architecture - Research Papers and Production Systems:**
- Phishing Detection System Architecture (ResearchGate)
- AI-Powered Phishing Detection System (IGI Global)
- PhishingRTDS: Real-Time Detection System (ScienceDirect)
- Machine Learning Pipelines for Phishing Detection (arXiv 2201.10752)
- Ensemble Methods Systematic Review (MDPI, Springer)

**Pitfalls - Recent Publications (2025-2026):**
- 2026 Phishing Threat Predictions - Cofense
- Machine Learning and Neural Networks Systematic Review (2017-2024) - MDPI Electronics 14/18/3744
- Staying ahead of phishers: review of advances (2024) - Springer
- Evolution of Phishing Detection with AI (2026) - arXiv 2507.07406v1

### Secondary (MEDIUM confidence)

**Stack - Performance Comparisons:**
- FastAPI vs Flask 2025 Comparison - JetBrains survey (38% FastAPI adoption)
- EasyOCR vs Tesseract Comparison - Landeros Labs (4-7x speed improvement)
- XGBoost vs CatBoost vs LightGBM - Neptune.ai, Analytics Vidhya
- Poetry vs Pipenv Comparison - BetterStack
- SMOTETomek-XGBoost for Phishing Detection - ScienceDirect (97.7% accuracy)

**Features - Academic Research:**
- Modeling Hybrid Feature-Based Phishing Websites Detection - PMC 8935623
- Explainable Feature Selection Framework - ScienceDirect
- Consensus and Majority Vote Feature Selection - Springer
- Phishing Website Prediction Using Ensemble Classifiers - Cybersecurity Journal

**Architecture - Implementation Patterns:**
- Encoder-Based Multimodal Ensemble Learning - Springer
- Hybrid Super Learner Ensemble for Mobile Devices - Nature Scientific Reports
- LLM-Based Multimodal Feature Extraction - MDPI Electronics 15/2/368

**Pitfalls - Domain-Specific Challenges:**
- Adaptive Cybersecurity through Continuous Model Retraining - ResearchGate
- What is Model Drift? Types & 4 Ways to Overcome - AIM Multiple
- Advanced Adversarial Attacks on Phishing Detection Models - Insights2TechInfo
- Training Data Poisoning: Invisible Cyber Threat of 2026 - TTMS
- PhreshPhish: Real-World Phishing Dataset and Benchmark - arXiv 2507.10854v1

### Tertiary (LOW confidence - needs validation)

**Emerging Techniques:**
- EXPLICATE: Enhancing Detection through Explainable AI and LLM-Powered Interpretability - arXiv 2503.20796 (needs validation in production)
- AI-Driven Phishing Detection: Enhancing with Reinforcement Learning - MDPI (experimental approach)
- Deep Learning Embeddings with Transformers for phishing - multiple sources (high computational cost, incremental improvement over classical ML)

---
*Research completed: 2026-02-09*
*Ready for roadmap: yes*
