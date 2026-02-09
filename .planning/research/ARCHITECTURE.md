# Architecture Research

**Domain:** Phishing Detection System
**Researched:** 2026-02-09
**Confidence:** HIGH

## Standard Architecture

### System Overview

Modern phishing detection systems follow a layered, modular architecture that separates concerns across data ingestion, feature extraction, classification, and decision aggregation layers.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Web UI     │  │  REST API    │  │   Dashboard  │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                  │                  │                      │
├─────────┴──────────────────┴──────────────────┴──────────────────────┤
│                      Decision Aggregation Layer                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │   Ensemble Voting Engine (Hard/Soft Voting)                  │   │
│  │   - ML Classifiers Aggregation                               │   │
│  │   - Rule-Based System Integration                            │   │
│  │   - Bayesian Probabilistic Fusion                            │   │
│  │   - Confidence Scoring & Conflict Detection                  │   │
│  └───────────────────────┬──────────────────────────────────────┘   │
│                          │                                           │
├──────────────────────────┴───────────────────────────────────────────┤
│                      Classification Layer                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │ ML Block │ │ Rule-    │ │ Bayesian │ │ Visual   │              │
│  │ (7 cls.) │ │ Based    │ │ System   │ │ Analysis │              │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘              │
│       │            │            │            │                      │
├───────┴────────────┴────────────┴────────────┴──────────────────────┤
│                    Feature Extraction Layer                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │ URL      │ │ Email    │ │ Text     │ │ OCR      │              │
│  │ Parser   │ │ Parser   │ │ NLP      │ │ Engine   │              │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘              │
│       │            │            │            │                      │
├───────┴────────────┴────────────┴────────────┴──────────────────────┤
│                    Data Ingestion Layer                              │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │   Input Handlers (Email, SMS, URL, Text, Image)             │   │
│  └──────────────────────────────────────────────────────────────┘   │
├──────────────────────────────────────────────────────────────────────┤
│                    Data Storage Layer                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ Trained  │  │ Feature  │  │ Results  │  │ Config   │           │
│  │ Models   │  │ Cache    │  │ History  │  │ Store    │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Input Handlers** | Accept emails, SMS, URLs, text, images | FastAPI/Flask endpoints with content-type validation |
| **URL Parser** | Extract URL features (domain age, HTTPS, IP-based, redirects) | Python libraries (urllib, tldextract, whois) |
| **Email Parser** | Extract header features (sender, SPF, DKIM, attachments) | Email library, header parsing |
| **Text NLP Processor** | Tokenization, TF-IDF vectorization, sentiment analysis | NLTK, spaCy, scikit-learn TfidfVectorizer |
| **OCR Engine** | Extract text from images in emails/SMS | Tesseract, EasyOCR, cloud OCR APIs |
| **ML Classifier Block** | 7 classifiers: Random Forest, SVM, MLP, Gradient Boosting, Logistic Regression, Naive Bayes, Decision Tree | scikit-learn with trained models |
| **Rule-Based Expert System** | Apply domain-specific rules (blacklists, patterns, heuristics) | Python rule engine or custom if-then logic |
| **Bayesian Probabilistic System** | Calculate P(phishing\|features) using Bayes theorem | Custom Bayesian network or pgmpy |
| **Visual Analysis Module** | Analyze images for fake logos, suspicious layouts | Computer vision (OpenCV, PIL) + trained CNN |
| **Ensemble Voting Engine** | Aggregate predictions using voting (hard/soft) | Custom voting logic with confidence weighting |
| **Genetic Algorithm Optimizer** | Hyperparameter tuning for ML models | DEAP, TPOT, or custom GA implementation |
| **Trained Models Store** | Persist trained model files | Pickle, joblib, ONNX format on disk/S3 |
| **Feature Cache** | Cache extracted features to avoid recomputation | Redis or in-memory cache |
| **Results History** | Store predictions for auditing and retraining | SQLite, PostgreSQL, MongoDB |
| **REST API** | Expose detection endpoints | FastAPI with Pydantic validation |
| **Web UI** | Demonstration interface for testing | React/Vue with form input and result display |
| **Dashboard** | Visualize detection metrics, confidence scores | Plotly Dash, Streamlit, or custom frontend |

## Recommended Project Structure

```
phishing-detection-system/
├── data/
│   ├── raw/                    # Raw datasets for training
│   ├── processed/              # Preprocessed features
│   └── models/                 # Trained model files (.pkl, .joblib)
├── src/
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── email_handler.py   # Parse email content
│   │   ├── sms_handler.py     # Parse SMS messages
│   │   ├── url_handler.py     # Handle URL inputs
│   │   └── image_handler.py   # Handle image inputs
│   ├── feature_extraction/
│   │   ├── __init__.py
│   │   ├── url_features.py    # Extract 15+ URL-based features
│   │   ├── email_features.py  # Extract header/body features
│   │   ├── text_features.py   # NLP-based feature extraction
│   │   ├── ocr_features.py    # OCR + text extraction
│   │   └── visual_features.py # Image analysis features
│   ├── classifiers/
│   │   ├── __init__.py
│   │   ├── ml_ensemble.py     # 7 ML classifiers wrapper
│   │   ├── rule_based.py      # Rule-based expert system
│   │   ├── bayesian.py        # Bayesian probabilistic model
│   │   └── visual_classifier.py # CNN/visual detection
│   ├── optimization/
│   │   ├── __init__.py
│   │   ├── genetic_optimizer.py # GA-based hyperparameter tuning
│   │   └── fitness.py         # Fitness function definitions
│   ├── aggregation/
│   │   ├── __init__.py
│   │   ├── voting_engine.py   # Ensemble voting (hard/soft)
│   │   └── conflict_detector.py # Detect classifier disagreements
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI application
│   │   ├── routes.py          # API endpoint definitions
│   │   └── schemas.py         # Pydantic request/response models
│   ├── web/
│   │   ├── app.py             # Web UI (Streamlit/Flask)
│   │   ├── templates/         # HTML templates
│   │   └── static/            # CSS, JS, images
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── preprocessing.py   # Data cleaning utilities
│   │   ├── validation.py      # Input validation
│   │   └── logging_config.py  # Logging setup
│   └── training/
│       ├── __init__.py
│       ├── train_ml_models.py # Train 7 ML classifiers
│       ├── train_cnn.py       # Train visual CNN model
│       └── evaluate.py        # Model evaluation metrics
├── notebooks/
│   ├── exploratory_analysis.ipynb
│   └── model_comparison.ipynb
├── tests/
│   ├── test_feature_extraction.py
│   ├── test_classifiers.py
│   └── test_api.py
├── config/
│   ├── config.yaml            # System configuration
│   └── hyperparameters.json   # Model hyperparameters
├── scripts/
│   ├── setup_data.sh          # Download/prepare datasets
│   └── start_services.sh      # Start API and web UI
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── requirements.txt
└── README.md
```

### Structure Rationale

- **ingestion/**: Separates input handling by data type (email, SMS, URL, image), allowing independent development and testing of each handler
- **feature_extraction/**: Modular feature extractors that can be composed; critical for maintaining the system as new features are added
- **classifiers/**: Each classification paradigm (ML, rule-based, Bayesian, visual) is isolated, enabling independent optimization and replacement
- **aggregation/**: Central decision logic that combines classifier outputs; this is where disagreements provide valuable context
- **optimization/**: Genetic algorithm code isolated from training; can be run offline without affecting production
- **api/ and web/**: Separate presentation concerns from core detection logic
- **training/**: Training scripts separate from inference code; important for reproducibility

## Architectural Patterns

### Pattern 1: Multi-Paradigm Ensemble with Conflict Detection

**What:** Combine multiple classification paradigms (ML ensemble, rule-based, Bayesian, visual analysis) and explicitly track disagreements between methods.

**When to use:** When detection reliability is critical and no single method is 100% accurate. The core value proposition of this architecture is that discrepancies between methods provide additional context.

**Trade-offs:**
- **Pros:** Higher accuracy, robust to adversarial attacks on single method, disagreements flag edge cases for review
- **Cons:** Higher computational cost, more complex debugging, requires careful aggregation logic

**Example:**
```python
class MultiParadigmEnsemble:
    def __init__(self):
        self.ml_ensemble = MLEnsemble(classifiers=7)
        self.rule_based = RuleBasedSystem()
        self.bayesian = BayesianSystem()
        self.visual = VisualClassifier()

    def predict(self, input_data):
        # Get predictions from each paradigm
        ml_pred = self.ml_ensemble.predict(input_data)
        rule_pred = self.rule_based.predict(input_data)
        bayes_pred = self.bayesian.predict(input_data)
        visual_pred = self.visual.predict(input_data)

        predictions = {
            'ml_ensemble': ml_pred,
            'rule_based': rule_pred,
            'bayesian': bayes_pred,
            'visual': visual_pred
        }

        # Detect conflicts
        conflict_score = self._calculate_disagreement(predictions)

        # Aggregate using weighted voting
        final_pred = self._aggregate_predictions(predictions)

        return {
            'prediction': final_pred,
            'confidence': self._calculate_confidence(predictions),
            'conflict_score': conflict_score,
            'individual_predictions': predictions
        }

    def _calculate_disagreement(self, predictions):
        """High disagreement indicates uncertain/edge case"""
        votes = [p['class'] for p in predictions.values()]
        from collections import Counter
        vote_counts = Counter(votes)
        # Normalized entropy as disagreement measure
        total = len(votes)
        entropy = -sum((count/total) * np.log2(count/total)
                      for count in vote_counts.values())
        max_entropy = np.log2(len(vote_counts))
        return entropy / max_entropy if max_entropy > 0 else 0
```

### Pattern 2: Feature Extraction Pipeline with Caching

**What:** Extract features once, cache them, and reuse across multiple classifiers. Use a pipeline pattern where each stage transforms data for the next.

**When to use:** When multiple classifiers need similar features (URL features, text features, etc.) and feature extraction is expensive (OCR, API calls).

**Trade-offs:**
- **Pros:** Reduces redundant computation, faster prediction time, easier to add new classifiers
- **Cons:** Memory overhead for caching, requires cache invalidation strategy

**Example:**
```python
from functools import lru_cache
import hashlib

class FeatureExtractionPipeline:
    def __init__(self):
        self.url_extractor = URLFeatureExtractor()
        self.text_extractor = TextFeatureExtractor()
        self.ocr_extractor = OCRFeatureExtractor()

    def extract(self, input_data):
        """Extract all features with caching"""
        cache_key = self._generate_cache_key(input_data)

        # Check cache first
        if cached := self._get_cached_features(cache_key):
            return cached

        features = {}

        # Extract URL features if URL present
        if 'url' in input_data:
            features['url'] = self.url_extractor.extract(input_data['url'])

        # Extract text features
        if 'text' in input_data:
            features['text'] = self.text_extractor.extract(input_data['text'])

        # Extract OCR features from images
        if 'image' in input_data:
            ocr_text = self.ocr_extractor.extract(input_data['image'])
            features['ocr'] = self.text_extractor.extract(ocr_text)

        # Cache for future use
        self._cache_features(cache_key, features)

        return features

    def _generate_cache_key(self, input_data):
        """Generate deterministic hash for caching"""
        content = str(sorted(input_data.items()))
        return hashlib.sha256(content.encode()).hexdigest()
```

### Pattern 3: Genetic Algorithm Optimization Loop

**What:** Use genetic algorithms to continuously optimize hyperparameters of ML models offline, periodically updating production models.

**When to use:** When you have multiple hyperparameters to tune (7 classifiers × multiple hyperparameters each) and want automated, efficient optimization.

**Trade-offs:**
- **Pros:** Finds better hyperparameters than grid search, 10x faster than exhaustive search, can optimize multiple objectives
- **Cons:** Non-deterministic results, requires fitness function design, needs significant compute resources

**Example:**
```python
from deap import base, creator, tools, algorithms
import numpy as np

class GeneticHyperparameterOptimizer:
    def __init__(self, classifier_type, X_train, y_train, X_val, y_val):
        self.classifier_type = classifier_type
        self.X_train = X_train
        self.y_train = y_train
        self.X_val = X_val
        self.y_val = y_val

        # Define GA components
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        creator.create("Individual", list, fitness=creator.FitnessMax)

        self.toolbox = base.Toolbox()
        self._setup_genetic_operators()

    def _setup_genetic_operators(self):
        """Define parameter space and genetic operators"""
        # Example for Random Forest
        if self.classifier_type == 'RandomForest':
            # n_estimators: 10-500
            self.toolbox.register("n_estimators",
                                 np.random.randint, 10, 501)
            # max_depth: 5-50
            self.toolbox.register("max_depth",
                                 np.random.randint, 5, 51)
            # min_samples_split: 2-20
            self.toolbox.register("min_samples_split",
                                 np.random.randint, 2, 21)

            self.toolbox.register("individual", tools.initCycle,
                                 creator.Individual,
                                 (self.toolbox.n_estimators,
                                  self.toolbox.max_depth,
                                  self.toolbox.min_samples_split), n=1)

    def fitness_function(self, individual):
        """Evaluate fitness (F1-score on validation set)"""
        n_estimators, max_depth, min_samples_split = individual

        from sklearn.ensemble import RandomForestClassifier
        clf = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            random_state=42
        )

        clf.fit(self.X_train, self.y_train)
        y_pred = clf.predict(self.X_val)

        from sklearn.metrics import f1_score
        f1 = f1_score(self.y_val, y_pred)

        return (f1,)

    def optimize(self, population_size=50, generations=20):
        """Run genetic algorithm optimization"""
        self.toolbox.register("evaluate", self.fitness_function)
        self.toolbox.register("mate", tools.cxTwoPoint)
        self.toolbox.register("mutate", tools.mutUniformInt,
                             low=[10, 5, 2], up=[500, 50, 20], indpb=0.2)
        self.toolbox.register("select", tools.selTournament, tournsize=3)

        population = [self.toolbox.individual()
                     for _ in range(population_size)]

        # Evolution
        for gen in range(generations):
            offspring = algorithms.varAnd(population, self.toolbox,
                                         cxpb=0.5, mutpb=0.2)
            fits = list(map(self.toolbox.evaluate, offspring))
            for fit, ind in zip(fits, offspring):
                ind.fitness.values = fit
            population = self.toolbox.select(offspring, k=len(population))

        # Return best individual
        best = tools.selBest(population, k=1)[0]
        return {
            'n_estimators': best[0],
            'max_depth': best[1],
            'min_samples_split': best[2],
            'fitness': best.fitness.values[0]
        }
```

### Pattern 4: Soft Voting with Confidence Weighting

**What:** Aggregate classifier predictions using soft voting (probability-based) with weights based on historical classifier performance.

**When to use:** When classifiers have different strengths and you want to favor more reliable classifiers while still considering all inputs.

**Trade-offs:**
- **Pros:** More nuanced than hard voting, adapts to classifier performance, produces calibrated confidence scores
- **Cons:** Requires classifiers to output probabilities, weights need tuning/updating

**Example:**
```python
class SoftVotingAggregator:
    def __init__(self, classifier_weights=None):
        """
        classifier_weights: dict mapping classifier name to weight
        Higher weight = more trust in that classifier
        """
        self.classifier_weights = classifier_weights or {
            'random_forest': 1.2,      # Historically best performer
            'gradient_boosting': 1.1,
            'svm': 1.0,
            'mlp': 0.9,
            'logistic_regression': 0.8,
            'naive_bayes': 0.7,
            'decision_tree': 0.6,      # Historically weakest
            'rule_based': 1.0,
            'bayesian': 0.9,
            'visual': 0.8              # Only applies when image present
        }

    def aggregate(self, predictions):
        """
        predictions: dict of {classifier_name: {'class': 0/1, 'proba': float}}
        Returns: final prediction with confidence
        """
        weighted_proba_sum = 0
        total_weight = 0

        for clf_name, pred in predictions.items():
            weight = self.classifier_weights.get(clf_name, 1.0)
            proba = pred['proba']  # Probability of phishing

            weighted_proba_sum += weight * proba
            total_weight += weight

        final_proba = weighted_proba_sum / total_weight
        final_class = 1 if final_proba >= 0.5 else 0

        # Confidence: how far from decision boundary (0.5)
        confidence = abs(final_proba - 0.5) * 2  # Scale to [0, 1]

        return {
            'class': final_class,
            'probability': final_proba,
            'confidence': confidence,
            'label': 'phishing' if final_class == 1 else 'legitimate'
        }
```

## Data Flow

### Detection Request Flow

```
[User Input: Email/SMS/URL/Text/Image]
    ↓
[Input Validation & Sanitization]
    ↓
[Content-Type Routing] → [Email Handler]
                       → [SMS Handler]
                       → [URL Handler]
                       → [Image Handler]
    ↓
[Feature Extraction Pipeline]
    ├─→ [URL Features: 15+ features]
    ├─→ [Email Features: headers, body, attachments]
    ├─→ [Text Features: TF-IDF, sentiment, entities]
    ├─→ [OCR Features: text from images]
    └─→ [Visual Features: image analysis, fake logos]
    ↓
[Feature Cache: Store for reuse]
    ↓
[Parallel Classification]
    ├─→ [ML Ensemble] → [7 Classifiers]
    ├─→ [Rule-Based System] → [Heuristics + Blacklists]
    ├─→ [Bayesian System] → [P(phishing|features)]
    └─→ [Visual Classifier] → [CNN predictions]
    ↓
[Aggregation Engine]
    ├─→ [Collect all predictions]
    ├─→ [Calculate disagreement score]
    └─→ [Apply soft voting with weights]
    ↓
[Result Generation]
    ├─→ [Final prediction: phishing/legitimate]
    ├─→ [Confidence score]
    ├─→ [Conflict indicators]
    └─→ [Individual classifier results]
    ↓
[Logging & Storage]
    ├─→ [Results history DB]
    └─→ [Metrics for monitoring]
    ↓
[Response to User]
    ├─→ [REST API JSON response]
    └─→ [Web UI visualization]
```

### Training Pipeline Flow

```
[Raw Dataset]
    ↓
[Data Preprocessing]
    ├─→ [Remove HTML tags, punctuation]
    ├─→ [Handle missing values]
    ├─→ [Normalize features]
    └─→ [Train-validation-test split (70-15-15)]
    ↓
[Feature Engineering]
    ├─→ [Extract URL features]
    ├─→ [TF-IDF vectorization]
    ├─→ [PCA for dimensionality reduction (optional)]
    └─→ [Feature selection (SelectKBest)]
    ↓
[Genetic Algorithm Optimization] (Parallel)
    ├─→ [Optimize Random Forest hyperparams]
    ├─→ [Optimize SVM hyperparams]
    ├─→ [Optimize MLP hyperparams]
    ├─→ [Optimize Gradient Boosting hyperparams]
    ├─→ [Optimize Logistic Regression hyperparams]
    ├─→ [Optimize Naive Bayes hyperparams]
    └─→ [Optimize Decision Tree hyperparams]
    ↓
[Model Training with Optimal Hyperparams]
    ├─→ [Train 7 ML classifiers]
    ├─→ [Train CNN for visual analysis]
    └─→ [Configure rule-based system]
    ↓
[Model Evaluation]
    ├─→ [Accuracy, Precision, Recall, F1-score]
    ├─→ [Confusion matrix]
    ├─→ [ROC-AUC]
    └─→ [Cross-validation]
    ↓
[Model Persistence]
    ├─→ [Serialize models (joblib/pickle)]
    └─→ [Save to data/models/]
    ↓
[Deploy to Production]
    ├─→ [Load models into inference engine]
    └─→ [Update API service]
```

### Key Data Flows

1. **Real-time Detection Flow:** Optimized for low latency (<500ms). Features extracted once, classifiers run in parallel, results aggregated and returned immediately.

2. **Batch Processing Flow:** For processing large email datasets. Inputs queued, feature extraction batched, classification parallelized across workers, results written to database.

3. **Retraining Flow:** Periodic (weekly/monthly) retraining using new labeled data. GA optimization runs offline, new models validated against test set, deployed only if performance improves.

4. **Monitoring Flow:** Real-time metrics collection (prediction latency, classification distribution, confidence scores) → Prometheus → Grafana dashboards → Alerts on anomalies.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **0-1k requests/day** | Single-server monolith. All components in one Python process. SQLite for storage. Suitable for demonstration and MVP. |
| **1k-100k requests/day** | Separate API server and training pipeline. Redis for feature caching. PostgreSQL for results storage. Docker Compose for orchestration. Horizontal scaling of API with load balancer. |
| **100k-1M requests/day** | Microservices architecture. Separate services for feature extraction, ML inference, rule-based detection. Message queue (RabbitMQ/Kafka) for async processing. Kubernetes for orchestration. Model serving with TensorFlow Serving or TorchServe. Distributed feature cache. |
| **1M+ requests/day** | Full distributed system. API gateway with rate limiting. Separate microservices per classifier. Distributed feature extraction with Spark. Model serving cluster with auto-scaling. Distributed cache (Redis Cluster). Time-series DB for metrics (InfluxDB). CDN for static content. |

### Scaling Priorities

1. **First bottleneck: Feature extraction (especially OCR)**
   - **Symptom:** High latency on image-based inputs
   - **Solution:**
     - Async processing with task queue (Celery + Redis)
     - Cache OCR results aggressively
     - Use GPU-accelerated OCR (EasyOCR with CUDA)
     - Consider cloud OCR APIs (Google Vision, AWS Textract) for scalability

2. **Second bottleneck: ML model inference**
   - **Symptom:** High CPU usage, slow response times
   - **Solution:**
     - Load models once at startup (avoid repeated loading)
     - Use optimized inference (ONNX Runtime, TensorRT)
     - Batch predictions when possible
     - Cache predictions for identical inputs
     - Consider model quantization to reduce size/latency

3. **Third bottleneck: Database writes**
   - **Symptom:** Slow result storage, connection pool exhaustion
   - **Solution:**
     - Async database writes (don't block response)
     - Bulk inserts instead of individual writes
     - Use connection pooling
     - Consider NoSQL (MongoDB) for flexible schema and faster writes

## Anti-Patterns

### Anti-Pattern 1: Training-Inference Skew

**What people do:** Use different feature extraction code for training and inference, or different preprocessing steps.

**Why it's wrong:** Models trained on features with one preprocessing will fail when inference uses different preprocessing. Causes dramatic accuracy drops in production.

**Do this instead:**
- Share feature extraction code between training and inference
- Create a FeatureExtractor class used by both pipelines
- Save preprocessing parameters (e.g., TF-IDF vocabulary, scalers) with trained models
- Unit test that training and inference features match

```python
# WRONG: Different feature extraction
# In training:
features = extract_features_v1(data)
# In inference:
features = extract_features_v2(data)  # Oops! Different logic

# RIGHT: Shared feature extractor
class FeatureExtractor:
    def __init__(self, config):
        self.config = config
        self.tfidf = TfidfVectorizer(**config['tfidf_params'])

    def fit(self, training_data):
        """Call during training"""
        self.tfidf.fit(training_data)

    def transform(self, data):
        """Call during both training and inference"""
        return self.tfidf.transform(data)

    def save(self, path):
        joblib.dump(self, path)

    @classmethod
    def load(cls, path):
        return joblib.load(path)

# Use same instance in training and inference
```

### Anti-Pattern 2: Naive Hard Voting Without Confidence

**What people do:** Use simple majority voting (5 out of 7 classifiers say phishing → phishing) without considering prediction confidence.

**Why it's wrong:** Ignores valuable information. A classifier predicting 0.51 phishing vs 0.99 phishing have very different confidence levels, but hard voting treats them equally.

**Do this instead:** Use soft voting with probabilities and weight by classifier reliability.

```python
# WRONG: Hard voting loses information
votes = [clf.predict(X)[0] for clf in classifiers]
final = 1 if sum(votes) > len(votes)/2 else 0

# RIGHT: Soft voting with probabilities
probas = [clf.predict_proba(X)[0][1] for clf in classifiers]
weights = [1.2, 1.0, 0.9, 1.1, 0.8, 0.7, 0.6]  # Based on validation performance
weighted_avg = sum(p*w for p,w in zip(probas, weights)) / sum(weights)
final = 1 if weighted_avg > 0.5 else 0
confidence = abs(weighted_avg - 0.5) * 2
```

### Anti-Pattern 3: Ignoring Classifier Disagreement

**What people do:** Only return final aggregated prediction without exposing individual classifier results.

**Why it's wrong:** High disagreement often indicates edge cases or adversarial attacks. This is valuable signal that should influence confidence scores and potentially trigger manual review.

**Do this instead:** Calculate and expose disagreement metrics. Flag high-disagreement cases for review.

```python
# WRONG: Only return final prediction
return {'prediction': 'phishing', 'confidence': 0.85}

# RIGHT: Include disagreement information
individual_predictions = {
    'rf': 'phishing',
    'svm': 'legitimate',  # Disagrees!
    'mlp': 'phishing',
    'gb': 'phishing',
    'lr': 'legitimate',   # Disagrees!
    'nb': 'phishing',
    'dt': 'phishing'
}

disagreement_score = calculate_entropy(individual_predictions)

return {
    'prediction': 'phishing',
    'confidence': 0.85,
    'disagreement': disagreement_score,
    'requires_review': disagreement_score > 0.6,  # High disagreement
    'individual_predictions': individual_predictions
}
```

### Anti-Pattern 4: Synchronous OCR Blocking Request

**What people do:** Process OCR inline during API request, causing 3-5 second response times.

**Why it's wrong:** Users expect fast responses (<1 second). OCR is slow, especially on high-resolution images. This creates terrible UX and limits throughput.

**Do this instead:** Async processing with immediate response and callback/polling.

```python
# WRONG: Synchronous OCR blocks response
@app.post("/detect")
def detect(file: UploadFile):
    text = ocr_engine.extract_text(file)  # Takes 3-5 seconds!
    features = extract_features(text)
    result = classifier.predict(features)
    return result

# RIGHT: Async OCR with task queue
from celery import Celery
celery_app = Celery('tasks', broker='redis://localhost:6379')

@celery_app.task
def process_image_async(file_path, request_id):
    text = ocr_engine.extract_text(file_path)
    features = extract_features(text)
    result = classifier.predict(features)
    store_result(request_id, result)

@app.post("/detect")
def detect(file: UploadFile):
    request_id = generate_uuid()
    file_path = save_upload(file)
    process_image_async.delay(file_path, request_id)
    return {
        'request_id': request_id,
        'status': 'processing',
        'polling_url': f'/results/{request_id}'
    }

@app.get("/results/{request_id}")
def get_result(request_id: str):
    result = fetch_result(request_id)
    if result:
        return {'status': 'complete', 'result': result}
    else:
        return {'status': 'processing'}
```

### Anti-Pattern 5: Loading Models on Every Request

**What people do:** Load trained models from disk for each prediction request.

**Why it's wrong:** Model loading is expensive (100-500ms for large models). Kills performance and wastes resources.

**Do this instead:** Load models once at application startup, keep in memory.

```python
# WRONG: Load on every request
@app.post("/detect")
def detect(data: dict):
    model = joblib.load('models/random_forest.pkl')  # Slow!
    prediction = model.predict(data)
    return prediction

# RIGHT: Load once at startup
class ModelManager:
    def __init__(self):
        self.models = {}
        self._load_models()

    def _load_models(self):
        """Load all models at startup"""
        model_files = {
            'rf': 'models/random_forest.pkl',
            'svm': 'models/svm.pkl',
            'mlp': 'models/mlp.pkl',
            'gb': 'models/gradient_boosting.pkl',
            'lr': 'models/logistic_regression.pkl',
            'nb': 'models/naive_bayes.pkl',
            'dt': 'models/decision_tree.pkl'
        }
        for name, path in model_files.items():
            self.models[name] = joblib.load(path)

    def predict(self, data):
        predictions = {}
        for name, model in self.models.items():
            predictions[name] = model.predict_proba(data)[0]
        return predictions

# Initialize once at app startup
model_manager = ModelManager()

@app.post("/detect")
def detect(data: dict):
    prediction = model_manager.predict(data)  # Fast!
    return prediction
```

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **Cloud OCR APIs** | REST API with retry logic | Use for production if Tesseract insufficient. AWS Textract, Google Cloud Vision API, Azure Computer Vision |
| **WHOIS/Domain Info** | REST API with caching | Rate-limited. Cache domain info for 24 hours. Use python-whois or domain-analysis APIs |
| **URL Reputation Services** | REST API (VirusTotal, URLScan) | Check URL against known phishing databases. Cache results. Respect rate limits |
| **Email Validation** | REST API or local library | Validate sender addresses, check SPF/DKIM. Use email-validator library or email reputation APIs |
| **TF-IDF Vectorizer** | Fitted scikit-learn transformer | Save fitted vectorizer with model. Load during inference to ensure same vocabulary |
| **Blacklist/Whitelist Databases** | PostgreSQL or Redis | Fast lookup for known phishing domains or legitimate senders |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| **API ↔ Feature Extraction** | Direct function calls (monolith) or REST/gRPC (microservices) | In microservices: feature extraction service returns JSON feature vector |
| **Feature Extraction ↔ Classifiers** | In-memory data structures (numpy arrays, pandas DataFrames) | Features passed as numerical arrays to all classifiers |
| **Classifiers ↔ Aggregation** | Dictionary of predictions | Each classifier returns {'class': int, 'proba': float} |
| **API ↔ Storage** | Async database writes | Use async ORM (SQLAlchemy async) or message queue for non-blocking writes |
| **Training Pipeline ↔ API** | Shared filesystem or object storage (S3) | New models saved to shared location, API reloads models on deployment |
| **Web UI ↔ REST API** | HTTP REST calls (fetch/axios) | Web UI is stateless frontend calling backend API |

## Build Order Recommendations

Based on component dependencies, suggested implementation order:

### Phase 1: Core Pipeline (MVP)
1. **Data ingestion** - Input handlers for URL and text
2. **Basic feature extraction** - URL features (15+), text features (TF-IDF)
3. **Single ML classifier** - Start with Random Forest (typically best performer)
4. **Simple prediction API** - FastAPI endpoint that returns prediction

**Goal:** End-to-end detection for URLs and text with one classifier.

### Phase 2: ML Ensemble
1. **Add remaining 6 classifiers** - SVM, MLP, Gradient Boosting, Logistic Regression, Naive Bayes, Decision Tree
2. **Implement soft voting aggregation** - Combine 7 classifier predictions
3. **Training pipeline** - Scripts to train all models on same dataset

**Goal:** 7-classifier ML ensemble with voting.

### Phase 3: Genetic Algorithm Optimization
1. **GA framework** - Setup DEAP or custom GA implementation
2. **Fitness function** - F1-score on validation set
3. **Hyperparameter optimization** - Run GA for each classifier
4. **Model retraining** - Train with optimized hyperparameters

**Goal:** Optimized hyperparameters for all 7 classifiers.

### Phase 4: Alternative Paradigms
1. **Rule-based expert system** - Implement heuristics and domain rules
2. **Bayesian probabilistic system** - Implement Naive Bayes variant or Bayesian network
3. **Multi-paradigm aggregation** - Update voting to include rule-based and Bayesian

**Goal:** Integration of ML, rule-based, and probabilistic methods.

### Phase 5: Email & SMS Support
1. **Email parser** - Extract headers, body, attachments
2. **SMS parser** - Handle SMS-specific features
3. **Email feature extraction** - Header features, attachment analysis
4. **Update classifiers** - Retrain with email/SMS features

**Goal:** Support for email and SMS inputs beyond just URLs.

### Phase 6: Visual Analysis & OCR
1. **OCR integration** - Tesseract or EasyOCR for text extraction from images
2. **Visual feature extraction** - Logo detection, layout analysis
3. **CNN classifier** - Train CNN for visual phishing detection
4. **Image input handler** - Support image uploads via API

**Goal:** OCR and visual analysis for image-based phishing.

### Phase 7: Web Application
1. **Web UI** - Streamlit or Flask frontend for demonstrations
2. **Result visualization** - Display individual classifier results, confidence, disagreement
3. **Dashboard** - Metrics visualization (detection rate, latency, accuracy)

**Goal:** User-friendly demonstration interface.

### Phase 8: Production Hardening
1. **Async processing** - Celery task queue for OCR and batch processing
2. **Caching** - Redis for feature and result caching
3. **Monitoring** - Prometheus metrics, logging, alerting
4. **Containerization** - Docker, Docker Compose, or Kubernetes

**Goal:** Production-ready, scalable deployment.

## Sources

**Architecture & Components:**
- [Phishing Detection System Architecture (ResearchGate)](https://www.researchgate.net/figure/Phishing-Detection-System-Architecture-or-PDSA_fig1_318382582)
- [AI-Powered Phishing Detection System (IGI Global)](https://www.igi-global.com/chapter/ai-powered-phishing-detection-system/390827)
- [PhishingRTDS: Real-Time Detection System (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0167404824001445)
- [Every SOC Analyst's Essential Guide (CyberPress 2026)](https://cyberpress.org/every-soc-analysts-essential-guide-to-fast-phishing-detection-in-2026/)

**Machine Learning Pipelines:**
- [Phishing Attacks Detection ML-Based Approach (arXiv)](https://arxiv.org/pdf/2201.10752)
- [Advancing Phishing Email Detection Deep Learning (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11013960/)
- [Machine Learning and Neural Networks Systematic Review (MDPI Electronics)](https://www.mdpi.com/2079-9292/14/18/3744)
- [Improving Phishing Email Detection with Adaptive Optimization (Nature Scientific Reports)](https://www.nature.com/articles/s41598-025-20668-5)

**Ensemble Methods:**
- [Encoder-Based Multimodal Ensemble Learning (Springer)](https://link.springer.com/chapter/10.1007/978-3-031-94455-0_16)
- [Hybrid Super Learner Ensemble for Mobile Devices (Nature Scientific Reports)](https://www.nature.com/articles/s41598-025-02009-8)
- [Phishing Attacks Detection Using Ensemble ML (ScienceDirect)](https://www.sciencedirect.com/org/science/article/pii/S1546221824004764)
- [Enhancing Detection through Ensemble Learning (MDPI)](https://www.mdpi.com/2076-3417/13/15/8756)

**Feature Extraction:**
- [Modeling Hybrid Feature-Based Detection (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8935623/)
- [LLM-Based Multimodal Feature Extraction (MDPI Electronics)](https://www.mdpi.com/2079-9292/15/2/368)
- [Explainable Feature Selection Framework (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S2666764924000419)

**Data Flow & Training:**
- [Predictive Model for Phishing Detection (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S1319157819304902)
- [Deep Learning-Based Phishing Detection CNN LSTM (MDPI Electronics)](https://www.mdpi.com/2079-9292/12/1/232)
- [Phishing Email Detection Using ML GitHub](https://github.com/Click2Hack/Phishing-Email-Detection-Using-Machine-Learning)

**Ensemble Voting:**
- [Effective Ensemble Approach for Preventing Attacks (MDPI Future Internet)](https://www.mdpi.com/1999-5903/16/11/414)
- [Phishing Attacks Detection Using Ensemble ML Algorithms (ResearchGate)](https://www.researchgate.net/publication/382094121_Phishing_Attacks_Detection_Using_Ensemble_Machine_Learning_Algorithms)
- [Phishing Website Prediction Using Classifiers (Cybersecurity Journal)](https://cybersecurity.springeropen.com/articles/10.1186/s42400-022-00126-9)

**Rule-Based & Bayesian:**
- [Novel Multi-Layer Heuristic Model (ACM)](https://dl.acm.org/doi/10.1145/3078564.3078580)
- [New Rule-Based Phishing Detection Method (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0957417416000385)
- [Intelligent Rule-Based Phishing Classification (ResearchGate)](https://www.researchgate.net/publication/261636543_Intelligent_Rule_based_Phishing_Websites_Classification)

**OCR & Visual Analysis:**
- [SMS Scam Detection with OCR (MDPI Sensors)](https://www.mdpi.com/1424-8220/24/18/6084)
- [Multi-Modal Protection Stops QR Code Phishing (IronScales)](https://ironscales.com/blog/how-multi-modal-protection-stops-qr-code-phishing)
- [Fresh Phish: Image-Based Phishing (INKY)](https://www.inky.com/en/blog/clever-image-based-phishing-and-phone-scam-is-outwitting-threat-detectors)
- [Text Detection in Phishing Protection (VISUA)](https://visua.com/text-detection-in-phishing-protection)

**API & Deployment:**
- [Rapid Deployment of Phishing Detection Pipelines (DEV Community)](https://dev.to/mohammad_waseem_c31f3a26f/rapid-deployment-of-phishing-detection-pipelines-in-a-devops-environment-under-tight-deadlines-2hd9)
- [Detecting Phishing Patterns in Microservices (DEV Community)](https://dev.to/mohammad_waseem_c31f3a26f/detecting-phishing-patterns-in-microservices-with-javascript-a-senior-architects-approach-1e0k)

**Genetic Algorithm Optimization:**
- [Gentun: Hyperparameter Tuning with GA (GitHub)](https://github.com/gmontamat/gentun)
- [Optimizing ML Models with GA-Based Hyperparameter Tuning (Medium)](https://medium.com/@burak96egeli/optimizing-machine-learning-models-with-genetic-algorithm-based-hyperparameter-tuning-76d6f15fde6c)
- [Hyperparameter Optimization with Genetic Algorithms Tutorial (Towards Data Science)](https://towardsdatascience.com/hyperparameter-optimization-with-genetic-algorithms-a-hands-on-tutorial-ef17e337eaad/)
- [Improved Hyperparameter Optimization Framework (Nature Scientific Reports)](https://www.nature.com/articles/s41598-023-32027-3)

---
*Architecture research for: Integrated Phishing Detection System*
*Researched: 2026-02-09*
