# Pitfalls Research

**Domain:** Phishing Detection Systems
**Researched:** 2026-02-09
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Training on Temporally Unrealistic Data Splits

**What goes wrong:**
Models are trained and evaluated using random train-test splits that ignore temporal progression of phishing behaviors. Studies document detection accuracies exceeding 95%, but frequently depend on random train-test partitions that overestimate real-world performance by disregarding the temporal evolution of phishing techniques. This leads to severe performance degradation in production when models encounter new phishing tactics not seen during training.

**Why it happens:**
Random splitting is convenient and produces impressive benchmark scores. Researchers prioritize publishable accuracy numbers over realistic evaluation. The temporal dimension of adversarial evolution is overlooked in favor of standard ML evaluation practices.

**How to avoid:**
- Use strict temporal splits: all training data must come before all test data
- Implement time-aware cross-validation with forward chaining
- Maintain a holdout set from recent data (last 3-6 months) never used in training
- Track performance metrics over time to detect degradation trends
- Test on zero-day phishing samples collected after model deployment

**Warning signs:**
- High accuracy in testing (>95%) but poor user-reported performance in production
- Performance metrics decline steadily after deployment
- Model struggles with newly launched phishing campaigns
- False negative rate increases over time while training accuracy remains high

**Phase to address:**
Phase 1 (Data Collection & Preparation) - Establish temporal partitioning strategy upfront. Phase 5 (Validation & Testing) - Implement time-aware evaluation protocols.

---

### Pitfall 2: Concept Drift and Model Temporal Degradation

**What goes wrong:**
Machine learning models deployed in phishing detection are susceptible to performance degradation over time due to concept drift, where the statistical properties of input data evolve while the underlying task remains unchanged. Static models fail to accommodate these shifts, potentially resulting in decreased detection accuracy and increased false-positives or negatives. The shifting nature of adversarial strategies, such as new malware variants or phishing tactics, demands that systems adapt swiftly to retain their effectiveness.

**Why it happens:**
Attackers continuously evolve tactics to evade detection. LLM-generated phishing emails can now be created in seconds with slight modifications to trick filters. Traditional static models assume data distribution remains constant, which is fundamentally wrong for adversarial domains like phishing detection.

**How to avoid:**
- Implement continuous drift detection mechanisms that monitor data distribution shifts
- Design event-driven or scheduled model retraining pipelines
- Build adaptive models using continual learning or online learning techniques
- Monitor prediction confidence and flag low-confidence predictions for human review
- Establish systematic performance evaluation with real-time alerting on degradation
- Maintain a feedback loop where newly discovered phishing attempts feed back into training

**Warning signs:**
- Gradual decline in precision, recall, or F1 scores over weeks/months
- Increasing number of user-reported false negatives
- Model confidence scores trending downward
- Emergence of new phishing patterns not represented in training data
- False positive rate increasing as model becomes overly conservative

**Phase to address:**
Phase 3 (Model Development) - Design models with retraining capability. Phase 4 (System Integration) - Build monitoring and retraining infrastructure. Phase 6 (Maintenance & Updates) - Implement continuous drift detection and adaptation.

---

### Pitfall 3: Class Imbalance and Dataset Bias

**What goes wrong:**
In phishing detection, training datasets are inherently limited with imbalanced class distribution, where malicious and phishing samples are typically underrepresented, potentially leading to biased predictions. When combining multiple data sources, class imbalance can become extreme (e.g., URLs representing 97% of samples, with emails, SMS, and websites just 3%). Missing data types from specific populations could bias the model and not reflect the realities of the environment in which it is deployed.

**Why it happens:**
Legitimate content vastly outnumbers phishing content in the real world. Collecting labeled phishing samples is difficult and time-consuming. Researchers often aggregate datasets from multiple sources without considering representativeness across attack vectors (email, SMS, URL, etc.).

**How to avoid:**
- Apply advanced sampling techniques like Borderline-SMOTE for balanced training
- Use GANs to generate synthetic phishing samples addressing data scarcity
- Ensure proportional representation across all attack vectors (email, SMS, URLs, images)
- Apply stratified sampling to maintain realistic class distributions
- Use cost-sensitive learning with higher penalties for false negatives
- Implement ensemble methods that explicitly handle imbalance (e.g., balanced random forest)
- Validate that dataset composition matches production distribution

**Warning signs:**
- Model achieves high accuracy but poor recall on minority class (phishing)
- High false negative rate despite good overall accuracy
- Model defaults to predicting "legitimate" for uncertain cases
- Performance metrics vary dramatically across different attack vectors
- User complaints about missed phishing attempts despite high accuracy claims

**Phase to address:**
Phase 1 (Data Collection & Preparation) - Establish balanced dataset collection strategy. Phase 2 (Feature Engineering) - Ensure feature extraction works across all attack vectors. Phase 3 (Model Development) - Apply imbalance-handling techniques during training.

---

### Pitfall 4: Dataset Quality and Labeling Errors

**What goes wrong:**
Ground truth labeling in phishing detection is subjective and error-prone. The categorization of spam vs. phishing presents inherent challenges, as the definition is often subjective and context-dependent, varying between users and environments. Poor-quality datasets suffer from leakage and unrealistic base rates, leading to overly optimistic performance results. In one documented case, a phishing website dataset containing 60k samples had to remove over 65% of phishing samples during cleaning (leaving only 9,398 valid samples from 27k original) due to bad data such as "404 Not Found" pages incorrectly labeled as phishing.

**Why it happens:**
Manual labeling is expensive and inconsistent across annotators. Automated labeling using blacklists or heuristics introduces systematic errors. Datasets scraped from the web contain stale or mislabeled data. There is no standard ground truth for "phishing" - different experts may classify borderline cases differently.

**How to avoid:**
- Implement dual-review process with independent annotators and adjudication process
- Use expert annotators with cybersecurity and psychology backgrounds
- Establish clear labeling guidelines with examples of edge cases
- Apply automated quality checks to remove obvious errors (404s, parsing failures, etc.)
- Track inter-annotator agreement and resolve discrepancies systematically
- Validate samples from third-party sources (PhishTank, etc.) before inclusion
- Maintain provenance metadata: who labeled, when, source, confidence level
- Periodically re-validate older samples to catch labeling errors

**Warning signs:**
- Training accuracy is suspiciously high (>98%) with perfect separation
- Manual inspection reveals obvious mislabeled samples
- Model learns to exploit dataset artifacts rather than true phishing signals
- Performance drops dramatically on external validation datasets
- High variance in performance across different data sources
- Features that shouldn't be predictive show high importance (e.g., HTTP status codes)

**Phase to address:**
Phase 1 (Data Collection & Preparation) - Implement rigorous labeling and quality control processes upfront. This is foundational and cannot be fixed later without complete dataset reconstruction.

---

### Pitfall 5: Over-Reliance on Indicator-Based Detection

**What goes wrong:**
Static checks explain what an email or URL looks like, not what it does. By 2026, phishing chains are built around redirects, delayed execution, and trusted platforms specifically to pass early detection. Indicator-based decisions (checking against blacklists, static URL features, sender domain) are slow to update and unreliable against modern evasion techniques. Traditional defenses like filters, blocklists, and basic pattern matching are no longer enough, and a "good enough" security stack is a liability.

**Why it happens:**
Indicator-based detection is simple to implement and explain. It produces few false positives when indicators are high-quality. Organizational inertia keeps legacy systems in place. There's insufficient awareness of how attackers now bypass indicator-based systems.

**How to avoid:**
- Build layered detection combining indicators, behavioral analysis, and ML predictions
- Implement sandbox environments to observe full phishing chain execution
- Use behavioral analysis to detect anomalous patterns beyond static features
- Incorporate campaign-level intelligence to detect coordinated attacks
- Monitor for evasion tactics: redirects, delayed triggers, abuse of trusted platforms
- Combine multiple analysis paradigms (rule-based, ML, Bayesian, expert system)
- Leverage project's core value: discrepancies between methods provide additional context

**Warning signs:**
- Detection rate drops when attackers use URL shorteners or redirects
- Phishing attempts through trusted platforms (Google Drive, Dropbox) bypass detection
- Time-delayed phishing (QR codes, PDFs with embedded links) evade analysis
- Attackers use session token theft and MFA-bypass techniques undetected
- New phishing campaigns succeed until indicators are manually updated

**Phase to address:**
Phase 2 (Feature Engineering) - Extract behavioral features beyond static indicators. Phase 3 (Model Development) - Integrate multiple detection paradigms. Phase 4 (System Integration) - Build execution environment for behavioral observation.

---

### Pitfall 6: False Positive/False Negative Cost Imbalance

**What goes wrong:**
Security teams must strike a balance between high volume of false positives and the risk of false negatives. A constant barrage of false positives can cripple a security team through alert fatigue. However, false negatives are arguably more dangerous, allowing malicious actors to operate undetected. The bottleneck in 2026 phishing response is no longer detection - it's verification. When alerts arrive without context, teams slow down, second-guess verdicts, and escalate cases unnecessarily.

**Why it happens:**
Default ML optimization targets overall accuracy, treating both error types equally. Security teams often tune for zero false negatives, flooding analysts with alerts. There's insufficient understanding of the true costs: analyst time, user disruption, reputational damage, and breach consequences.

**How to avoid:**
- Define explicit cost functions that reflect organizational risk tolerance
- Use cost-sensitive learning with different penalties for FP vs. FN
- Provide rich context with each alert: confidence score, contributing features, similar cases
- Implement tiered response: high-confidence blocks, medium-confidence warnings, low-confidence logging
- Track analyst feedback and tune thresholds based on actual triage outcomes
- Use ensemble disagreement as a confidence signal (project's core value proposition)
- Build human-in-the-loop workflows for borderline cases
- Measure alert quality metrics: precision, analyst time per alert, escalation rate

**Warning signs:**
- Analysts ignore or batch-process alerts due to volume
- Alert fatigue leads to missed true positives
- Users routinely bypass security warnings
- High escalation rate to senior analysts
- Requests to "turn down sensitivity" despite active threats
- Lack of metrics on analyst efficiency or alert quality

**Phase to address:**
Phase 3 (Model Development) - Implement cost-sensitive training and calibrated confidence scoring. Phase 4 (System Integration) - Build alert context enrichment and tiered response workflows. Phase 5 (Validation & Testing) - Tune decision thresholds based on production cost data.

---

### Pitfall 7: Adversarial Robustness and Evasion Attacks

**What goes wrong:**
AI-based approaches including deep learning IDS and ensemble classifiers suffer from vulnerability to adversarial manipulation. LLM-rephrased emails can significantly degrade performance of both ML and LLM-based detectors. Attackers can maintain semantic meaning while controlling similarity through strategies like element elimination, background modifications, or text additions. Public phishing/legitimate datasets currently lack adversarial email examples, keeping detection models vulnerable to targeted evasion.

**Why it happens:**
Models trained on standard datasets haven't seen adversarial examples. Phishing is an adversarial domain - attackers actively probe defenses. Minor perturbations can flip predictions without changing semantic meaning. Adversarial robustness is often an afterthought rather than a design requirement.

**How to avoid:**
- Include adversarial training with perturbed phishing samples in training pipeline
- Use data augmentation to expose models to variations (rephrasing, reformatting, obfuscation)
- Test models against known evasion techniques before deployment
- Implement adversarial detection: flag inputs that appear crafted to evade
- Use ensemble methods with diverse architectures - harder to fool simultaneously
- Monitor for distribution shift that suggests adversarial probing
- Incorporate robust features less susceptible to manipulation (behavioral, temporal)
- Build red team capability to continuously test defenses

**Warning signs:**
- Detection rate suddenly drops for a specific campaign
- Phishing attempts show patterns of systematic testing (A/B variations)
- Small perturbations to caught phishing make it evade detection
- Model confidence scores become bimodal (very high or very low)
- Attackers reuse successful templates repeatedly
- Features that should be stable show unexpected variance

**Phase to address:**
Phase 3 (Model Development) - Implement adversarial training and robustness testing. Phase 5 (Validation & Testing) - Red team testing with adversarial examples. Phase 6 (Maintenance & Updates) - Continuous adversarial monitoring and model hardening.

---

### Pitfall 8: Real-Time Performance and Latency Constraints

**What goes wrong:**
Real-time phishing detection systems must operate within a few hundred milliseconds to minimize user disruption. However, multimodal models incur large computational costs due to duplicated feature extraction pipelines, cannot scale in real-time environments such as browsers or email gateways, and have significant latency issues. Features requiring third-party lookups (WHOIS, DNS, search engines) introduce unacceptable delays. The balancing act between speed and accuracy is a major challenge.

**Why it happens:**
Research prioritizes accuracy over latency in offline evaluation. Complex models (deep ensembles, transformer-based, multimodal) achieve higher accuracy but are computationally expensive. Feature extraction from external sources (DNS, WHOIS, website rendering) adds latency. There's insufficient profiling during development.

**How to avoid:**
- Establish latency budget upfront (e.g., <200ms end-to-end)
- Profile each component: feature extraction, model inference, post-processing
- Prefer lightweight models (Logistic Regression: 0.0001s, RL: 2.3ms) over heavy ones where accuracy is comparable
- Avoid features requiring external lookups in real-time path
- Pre-compute or cache slow features where possible
- Use asynchronous processing: fast initial verdict, detailed analysis in background
- Implement URL-only detection for speed; defer multimodal analysis for borderline cases
- Benchmark on target hardware with realistic load
- Monitor production latency and timeout rates

**Warning signs:**
- User complaints about slow email/web browsing
- High timeout or failure rates during peak load
- Latency percentiles (p95, p99) exceed user tolerance
- Feature extraction takes longer than model inference
- System scales poorly with traffic growth
- Third-party API calls become bottleneck

**Phase to address:**
Phase 2 (Feature Engineering) - Design feature extraction for low latency. Phase 3 (Model Development) - Select models meeting latency budget. Phase 4 (System Integration) - Architect asynchronous processing pipeline. Phase 5 (Validation & Testing) - Load test under realistic conditions.

---

### Pitfall 9: Poor Feature Engineering and External Dependencies

**What goes wrong:**
It is difficult to define all relevant features that impact classification accuracy, even for domain experts. Earlier approaches are complex and unsuitable for real-time environments due to dependency on third-party sources such as search engines. Machine learning solutions necessitate large computations to gather and compute features from diverse sources (URL, HTML source code, website traffic, DNS, WHOIS, search engines). Using such a big dataset makes detection much riskier, and many characteristics are overlooked. Host-based features are less suitable for real-time detection due to retrieval latency.

**Why it happens:**
Feature engineering relies on domain expertise that may be incomplete. Researchers add every possible feature hoping to improve accuracy. External dependencies (DNS, WHOIS, search engines) seem necessary for comprehensive analysis. There's insufficient focus on feature efficiency and redundancy.

**How to avoid:**
- Prioritize features with high information gain and low computational cost
- Use feature importance analysis to eliminate redundant or low-value features
- Minimize external dependencies; prefer on-device or cached feature extraction
- Apply privacy-by-design: limit collection to what's necessary, prefer on-device extraction
- Test feature extraction pipeline independently from model training
- Document feature rationale and limitations
- Use feature selection techniques (genetic algorithms, LASSO, recursive elimination)
- Validate that features generalize across phishing types (email, SMS, URL, image)
- Ensure feature extraction is robust to adversarial obfuscation

**Warning signs:**
- Feature extraction fails frequently due to unavailable external services
- High correlation between many features (redundancy)
- Features that work well in lab fail in production
- Privacy concerns raised about data collection
- Feature extraction is the performance bottleneck
- Features don't generalize across attack vectors

**Phase to address:**
Phase 2 (Feature Engineering) - Design efficient, robust feature extraction. This phase is critical and must be done carefully before model development. Phase 5 (Validation & Testing) - Validate feature robustness across attack vectors.

---

### Pitfall 10: Inadequate OCR and Visual Analysis

**What goes wrong:**
Visual similarity-based models can have inconsistent effectiveness when encountering changed captions, and OCR-aided models incorporate additional textual information but have several vulnerabilities including Faster-RCNN's imprecise logo detection and challenges with borderline logo similarity cases. Visual similarity-based systems show significant performance degradation (20.7%) in real-world scenarios compared to test datasets. The accuracy of phishing detection depends on OCR software, making systems vulnerable to OCR extraction errors and obfuscation techniques. A common 2026 tactic involves sending QR codes in PDFs that bypass email link filters.

**Why it happens:**
Visual phishing (image-based attacks, QR codes) is increasing. OCR and visual similarity are complex problems with inherent limitations. Test datasets don't capture real-world visual variations. Attackers actively exploit OCR weaknesses through obfuscation.

**How to avoid:**
- Use multiple OCR engines and combine results to improve robustness
- Implement multi-modal protection that analyzes both text and visual content
- Apply preprocessing to improve OCR accuracy (deskewing, denoising, contrast enhancement)
- Extract features beyond just text: logo detection, layout analysis, color schemes
- Test against adversarial visual manipulations (background mods, noise, text overlay)
- Don't rely solely on OCR - use deep learning for direct image analysis
- Handle QR codes specifically: decode and analyze target URLs
- Validate that visual analysis works across image formats and qualities
- Build fallback mechanisms when OCR confidence is low

**Warning signs:**
- OCR extraction fails or returns gibberish frequently
- Visual similarity scoring inconsistent across similar phishing attempts
- QR code-based phishing evades detection
- Logo detection fails for legitimate brands
- Performance degrades on poor-quality images
- Adversarial visual modifications (noise, overlays) cause evasion

**Phase to address:**
Phase 2 (Feature Engineering) - Implement robust OCR and visual feature extraction. Phase 3 (Model Development) - Integrate visual analysis models. Phase 5 (Validation & Testing) - Test against adversarial visual obfuscation.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using public datasets without validation | Fast dataset assembly, published benchmarks | Poor quality, labeling errors, unrealistic performance claims | Never - always validate samples |
| Random train-test split instead of temporal | High accuracy scores, simple implementation | Overestimated performance, poor generalization to new attacks | Never in adversarial domains |
| Single model instead of ensemble | Faster training, simpler deployment | Lower accuracy, no confidence calibration, no disagreement signal | Only for baseline/prototype |
| Static model without retraining | No infrastructure overhead | Rapid performance degradation due to concept drift | Only for research, never production |
| Optimizing for accuracy alone | Simple optimization target | Imbalanced false positive/false negative trade-off, poor user experience | Only in initial development |
| Including all possible features | Potentially higher accuracy | Slow inference, external dependencies, privacy issues | Only for feature importance analysis |
| Skipping adversarial robustness testing | Faster time-to-deployment | Vulnerability to evasion attacks | Never - attackers will probe |
| Using heavyweight models (transformers, multimodal) | State-of-art accuracy | Unacceptable latency, cannot scale | Only if latency is not a constraint |

## Integration Gotchas

Common mistakes when integrating multiple detection paradigms (7 ML classifiers, genetic algorithm, rule-based expert system, Bayesian system).

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Ensemble voting | Simple majority vote treats all models equally | Weight votes by model confidence and historical accuracy per phishing type |
| Disagreement handling | Ignoring cases where models disagree | Treat disagreement as valuable signal - escalate for human review or deeper analysis |
| Feature consistency | Each model uses different features | Ensure feature extraction produces consistent inputs for all models; validate feature alignment |
| Threshold tuning | Tuning thresholds independently per model | Tune ensemble thresholds jointly using production cost function |
| Genetic algorithm optimization | Optimizing only for accuracy | Multi-objective optimization: accuracy, latency, false positive rate, robustness |
| Rule-based system maintenance | Static rules never updated | Continuous rule evaluation; deprecate low-performing rules; add rules from pattern analysis |
| Bayesian prior selection | Using uninformative priors | Use domain knowledge and historical data to set informative priors; update with production data |
| Model update coordination | Updating models independently | Coordinate updates to avoid breaking ensemble assumptions; A/B test changes |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Synchronous feature extraction from external APIs | Acceptable latency in testing | Async extraction with caching; eliminate external dependencies from critical path | >100 requests/sec |
| In-memory model storage | Fast model serving | Model registry with lazy loading; shared model cache across instances | >5 models or >1GB RAM |
| Blocking inference calls | Simple implementation | Async inference with batching; request queuing | >1000 requests/sec |
| Full email/page rendering for analysis | High accuracy | Selective rendering based on heuristics; timeout on slow renders | Emails >1MB or complex HTML |
| Logging all predictions | Complete audit trail | Sample logging; aggregate metrics; separate hot and cold paths | >10K predictions/day |
| Single-threaded ensemble | Predictable execution | Parallel model inference; model sharding | >7 models or >100ms total |
| Database writes in critical path | Durable storage | Write to queue; async persistence; use time-series DB | >500 writes/sec |
| Real-time model retraining | Always fresh model | Scheduled retraining (daily/weekly); staged rollout | Dataset >100K samples |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing raw phishing samples without isolation | Accidental execution of malicious code; data breach of phishing corpus | Sandbox storage; encrypt at rest; access controls; automated sanitization |
| Exposing model confidence scores to users | Attackers probe threshold and craft borderline cases | Return binary verdict or risk levels, not raw scores; rate limit queries |
| Allowing arbitrary feature queries | Attackers reverse-engineer feature extraction | Restrict API to predefined inputs; monitor for probing patterns |
| Training data poisoning | Attacker submits mislabeled samples degrading model | Validate all contributed samples; use trusted sources; detect outliers |
| Model theft via prediction API | Attackers clone model through queries | Rate limiting; query pattern detection; watermarking |
| Insufficient input validation | Adversarial inputs cause crashes or evasion | Strict input validation; size limits; format checking; sanitization |
| Leaking training data through memorization | Privacy breach; adversarial advantage | Differential privacy; deduplication; membership inference testing |
| Unencrypted model files | Model theft; intellectual property loss | Encrypt model files; secure deployment pipeline; access controls |

## UX Pitfalls

Common user experience mistakes in phishing detection systems.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Blocking without explanation | User frustration; bypass attempts | Provide clear explanation of why blocked; show suspicious elements |
| Too many false positive warnings | Alert fatigue; ignoring all warnings | Tune thresholds; provide confidence levels; allow temporary bypass with acknowledgment |
| Slow analysis blocking user workflow | Productivity loss; system avoidance | Fast initial verdict (<200ms); detailed analysis async; progress indicators |
| No feedback mechanism | Users can't report errors; model doesn't improve | Easy reporting; visible impact; thank you message |
| Binary verdict without context | Users can't make informed decisions | Show risk factors; explain decision; provide override path |
| Inconsistent decisions | User confusion; loss of trust | Ensemble consistency checks; explain disagreement when it occurs |
| Technical jargon in warnings | Users don't understand threat | Plain language; visual indicators; actionable guidance |
| No learning from user feedback | Repeated mistakes; user frustration | Close feedback loop; update model/rules; notify when issue fixed |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Temporal evaluation:** Often missing time-aware splits - verify model tested only on future data relative to training
- [ ] **Concept drift monitoring:** Often missing production monitoring - verify alerting exists for performance degradation
- [ ] **Adversarial testing:** Often missing red team validation - verify model tested against known evasion techniques
- [ ] **Latency profiling:** Often missing real-world load testing - verify p95/p99 latency under production load
- [ ] **Class imbalance handling:** Often missing validation across all attack vectors - verify performance on minority classes
- [ ] **Label quality validation:** Often missing inter-annotator agreement - verify labeling process and error rates
- [ ] **Feature extraction robustness:** Often missing failure handling - verify behavior when external dependencies fail
- [ ] **Ensemble coordination:** Often missing disagreement analysis - verify what happens when models disagree
- [ ] **Cost-sensitive optimization:** Often missing production cost function - verify false positive/negative costs incorporated
- [ ] **Model retraining pipeline:** Often missing automation - verify retraining can be triggered and deployed safely
- [ ] **Privacy compliance:** Often missing data minimization - verify only necessary features collected; PII handling
- [ ] **OCR fallback:** Often missing low-confidence handling - verify behavior when OCR extraction fails or is uncertain

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Temporal data leakage discovered | HIGH | Rebuild dataset with strict temporal partitioning; retrain all models; re-evaluate; discard previous results |
| Severe concept drift | MEDIUM | Emergency retraining on recent data; deploy updated model; investigate drift cause; improve monitoring |
| Class imbalance causing poor recall | MEDIUM | Apply SMOTE/GAN augmentation; retrain with balanced data; adjust decision threshold; add cost-sensitive weighting |
| Dataset quality issues | HIGH | Manual re-labeling of affected samples; automated quality checks; retrain; may require dataset reconstruction |
| Indicator-only detection failing | MEDIUM | Add behavioral analysis layer; deploy sandbox execution; integrate ML models; multi-layer architecture |
| False positive flood | LOW | Tune decision thresholds; add confidence-based tiers; provide better context; improve alert quality |
| Adversarial evasion campaign | MEDIUM | Collect adversarial examples; adversarial training; model hardening; deploy quickly; investigate attack pattern |
| Latency exceeding budget | MEDIUM | Profile and optimize bottlenecks; switch to lighter models; remove external dependencies; add caching |
| Poor feature engineering | HIGH | Redesign feature extraction; validate across attack vectors; retrain models; may require architecture changes |
| OCR/visual analysis failures | MEDIUM | Add/upgrade OCR engines; improve preprocessing; add fallback analysis; test against obfuscation |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Temporal data leakage | Phase 1: Data Collection | Verify temporal split in code; check no future data in training; test on recent holdout |
| Concept drift | Phase 3: Model Development + Phase 6: Maintenance | Monitor metrics over time; verify retraining triggers; test drift detection |
| Class imbalance | Phase 1: Data Collection + Phase 3: Model Development | Check class distributions; verify per-class metrics; test on minority classes |
| Dataset quality | Phase 1: Data Collection | Inter-annotator agreement scores; automated quality checks; manual sample review |
| Indicator-only detection | Phase 2: Feature Engineering + Phase 3: Model Development | Test against evasion techniques; verify behavioral features included |
| FP/FN imbalance | Phase 3: Model Development + Phase 5: Validation | Cost function implementation; threshold tuning; user feedback metrics |
| Adversarial vulnerability | Phase 3: Model Development + Phase 5: Validation | Red team testing results; adversarial training validation; robustness metrics |
| Latency issues | Phase 2: Feature Engineering + Phase 4: System Integration | Load testing results; latency p95/p99 under production traffic; timeout rates |
| Poor feature engineering | Phase 2: Feature Engineering | Feature importance analysis; cross-vector validation; external dependency audit |
| OCR/visual failures | Phase 2: Feature Engineering + Phase 5: Validation | OCR accuracy metrics; visual similarity testing; adversarial image testing |
| Ensemble integration | Phase 4: System Integration | Disagreement analysis; coordination testing; weighted voting validation |
| Rule system brittleness | Phase 3: Model Development + Phase 6: Maintenance | Rule performance tracking; deprecation process; continuous evaluation |

## Sources

### Critical Pitfalls & Model Performance
- [2026 Phishing Threat Predictions: 5 Key Takeaways](https://cofense.com/blog/2026-phishing-threat-predictions-5-key-takeaways)
- [AI-Powered Phishing Detection & Prevention Strategies for 2026](https://www.uscsinstitute.org/cybersecurity-insights/blog/ai-powered-phishing-detection-and-prevention-strategies-for-2026)
- [The new face of phishing: Why traditional defenses are failing your customers in 2026](https://managedservicesjournal.com/articles/the-new-face-of-phishing-why-traditional-defenses-are-failing-your-customers-in-2026/)
- [Phishing in 2026: New Techniques, Persistent Human Risk, and Real Defenses](https://www.tropicosecurity.com/phishing-2026-techniques/)

### Machine Learning Challenges & Systematic Reviews
- [Machine Learning and Neural Networks for Phishing Detection: A Systematic Review (2017–2024)](https://www.mdpi.com/2079-9292/14/18/3744)
- [Staying ahead of phishers: a review of recent advances and emerging methodologies in phishing detection](https://link.springer.com/article/10.1007/s10462-024-11055-z)
- [Evolution of Phishing Detection with AI: A Comparative Review of Next-Generation Techniques](https://arxiv.org/html/2507.07406v1)

### Concept Drift & Model Degradation
- [Adaptive Cybersecurity through Continuous Model Retraining under Concept Drift](https://www.researchgate.net/publication/395354357_Adaptive_Cybersecurity_through_Continuous_Model_Retraining_under_Concept_Drift)
- [What is Model Drift? Types & 4 Ways to Overcome in 2026](https://research.aimultiple.com/model-drift/)
- [Continual Drift Detection and Adaptation for Cybersecurity Applications](https://link.springer.com/chapter/10.1007/978-981-95-3456-2_21)

### Adversarial Attacks & Robustness
- [Advanced Adversarial Attacks on Phishing Detection Models: Identification and Mitigation](https://insights2techinfo.com/advanced-adversarial-attacks-on-phishing-detection-models-identification-and-mitigation/)
- [Training Data Poisoning: The Invisible Cyber Threat of 2026](https://ttms.com/training-data-poisoning-the-invisible-cyber-threat-of-2026/)

### Class Imbalance & Data Quality
- [Advancing Phishing Email Detection: A Comparative Study of Deep Learning Models](https://pmc.ncbi.nlm.nih.gov/articles/PMC11013960/)
- [PhreshPhish: A Real-World, High-Quality, Large-Scale Phishing Website Dataset and Benchmark](https://arxiv.org/html/2507.10854v1)
- [Constructing and Benchmarking: a Labeled Email Dataset for Text-Based Phishing and Spam Detection Framework](https://arxiv.org/html/2511.21448v1)

### OCR & Visual Analysis
- [Evaluating the Effectiveness and Robustness of Visual Similarity-based Phishing Detection Models](https://arxiv.org/html/2405.19598v1)
- [How Multi-Modal Protection Stops QR Code Phishing](https://ironscales.com/blog/how-multi-modal-protection-stops-qr-code-phishing)

### Real-Time Performance & Latency
- [Real-Time Phishing Detection for Brand Protection Using Temporal Convolutional Network-Driven URL Sequence Modeling](https://www.mdpi.com/2079-9292/14/18/3744)
- [Enhancing Real-Time Phishing Detection with AI: A Comparative Study](https://www.diva-portal.org/smash/get/diva2:1983139/FULLTEXT01.pdf)

### Feature Engineering & Ensemble Methods
- [EnLeM: ensemble learning-based model to detect phishing websites](https://link.springer.com/article/10.1186/s13635-025-00219-1)
- [Enhanced Feature Selection Using Genetic Algorithm for Machine-Learning-Based Phishing URL Detection](https://www.mdpi.com/2076-3417/14/14/6081)
- [Frontiers | Unveiling suspicious phishing attacks: enhancing detection with an optimal feature vectorization algorithm and supervised machine learning](https://www.frontiersin.org/journals/computer-science/articles/10.3389/fcomp.2024.1428013/full)

### Evaluation & Deployment
- [In-Depth Analysis of Phishing Email Detection: Evaluating the Performance of Machine Learning and Deep Learning Models Across Multiple Datasets](https://www.mdpi.com/2076-3417/15/6/3396)
- [Evaluation of AI Models for Phishing Detection Using Open Datasets](https://www.mdpi.com/2673-4591/107/1/37)
- [Enhancing Institutional Cybersecurity through Intelligent Predictive Analytics for Phishing Attack Detection](https://eajournals.org/ejcsit/vol14-issue-1-2026/enhancing-institutional-cybersecurity-through-intelligent-predictive-analytics-for-phishing-attack-detection/)

---
*Pitfalls research for: Phishing Detection Systems*
*Researched: 2026-02-09*
