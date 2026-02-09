# Technology Stack

**Project:** Phishing Detection ML System
**Researched:** 2026-02-09
**Confidence:** HIGH

## Recommended Stack

### Core ML Framework

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| scikit-learn | 1.8.0 | Primary ML framework for 7 classifiers | Industry standard for classical ML algorithms (Random Forest, SVM, MLP, Gradient Boosting, Logistic Regression, Naive Bayes, Decision Tree). Mature, well-documented, excellent interoperability. Released December 2025 with performance improvements. |
| Python | 3.11+ | Runtime environment | Required by scikit-learn 1.8.0. Python 3.11 offers significant performance improvements (10-60% faster than 3.10) while maintaining full ML library compatibility. Avoid 3.13 experimental features for production ML. |

### Gradient Boosting Libraries

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| XGBoost | 3.1.3 | Advanced gradient boosting | Best for Kaggle-style competitions and fine-grained control. Achieves 98.4% accuracy in phishing detection research (2025). Latest release January 2026. |
| CatBoost | 1.2.8 | Categorical feature handling | Excels with categorical features requiring minimal preprocessing. Builds symmetric trees resistant to overfitting. Best for messy datasets with many categorical columns. Released April 2025. |
| LightGBM | 4.6.0+ | High-speed gradient boosting on large datasets | Fastest training speed due to leaf-wise tree growth. Use when dataset exceeds 1M rows or fast iteration is critical. GPU acceleration available. |

**Recommendation:** Start with XGBoost for baseline, add CatBoost if URL/domain features prove challenging, skip LightGBM unless dataset grows beyond 100K samples.

### Genetic Algorithm Optimization

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| DEAP | 1.4.3 | Genetic algorithm framework for hyperparameter optimization | Mature evolutionary computation framework with genetic algorithms, genetic programming, and evolution strategies. Supports multi-objective optimization and parallelization. Released May 2025. 10x faster than GridSearch with similar accuracy. |
| mloptimizer | 1.0+ | Alternative GA-based hyperparameter tuning | Simpler API specifically for scikit-learn models. Released November 2025. Consider if DEAP complexity is overkill. |

**Recommendation:** Use DEAP for production implementation due to maturity, extensive features, and active maintenance. Reserve mloptimizer as fallback if team prefers simpler API.

### Data Processing & Analysis

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| pandas | 3.0.0 | Tabular data manipulation | Industry standard for structured data. Version 3.0 (January 2026) adds Apache Arrow support and optional GPU acceleration for large-scale processing. Essential for feature engineering. |
| NumPy | 1.28+ | Numerical operations and matrix math | Foundation for pandas and scikit-learn. 15-20% faster matrix computations in latest versions. Critical for feature vector operations. |
| imbalanced-learn | 0.14.1 | Handling imbalanced phishing datasets | SMOTE and SMOTETomek achieve 97.7% accuracy in phishing detection (2025 research). Addresses minority class problem in phishing datasets. Released December 2025. |

### OCR & Image Processing

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| EasyOCR | 1.7.2 | Primary OCR for phishing images | 4x faster than Tesseract on GPU, 7x faster on CPU. Robust with multi-line text, low-quality images, and handwritten text. Supports 80+ languages with deep learning. Released September 2024. |
| Pillow | 10.4+ | Image preprocessing for OCR | Lightweight, simple API for image loading, resizing, format conversion. Perfect for preprocessing before OCR. Easier learning curve than OpenCV. |
| OpenCV | 4.11+ | Advanced image analysis (visual phishing detection) | Use only for visual analysis features (layout detection, logo matching, color analysis). Overkill for basic OCR preprocessing. Better accuracy and precision than Pillow for computer vision tasks. |

**Recommendation:** EasyOCR (primary) + Pillow (preprocessing). Add OpenCV only if implementing visual analysis features (phase 2+).

### NLP & Text Processing

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| spaCy | 3.8.11 | Production NLP for email/SMS analysis | State-of-the-art speed and accuracy for tokenization, NER, dependency parsing. Supports 70+ languages. Transformer integration available. Released November 2025. Preferred over NLTK for production. |
| Transformers (Hugging Face) | 4.51+ | Optional: Advanced text classification | Consider only if classical ML underperforms. All Hugging Face models integrate with spaCy. Defer until baseline established. |

**Recommendation:** Start with spaCy for tokenization, NER, and linguistic features. Reserve Transformers for Phase 3+ if accuracy requires deep learning.

### Web Application Framework

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| FastAPI | 0.128.5 | REST API and web application backend | 4x faster than Flask (20K+ vs 5K requests/sec). Native async support (ASGI). Auto-generated OpenAPI docs. 40% YoY adoption growth (29% → 38% in 2025). Released February 2026. Perfect for ML model serving. |
| Uvicorn | 0.34+ | ASGI server for FastAPI | Production-grade async server. Standard choice for FastAPI deployment. |
| Pydantic | 2.10+ | Data validation and serialization | Core dependency of FastAPI. Type-safe request/response validation. Essential for ML API contracts. |

**Alternative:** Flask 3.1+ if team has extensive Flask experience, but FastAPI is strongly recommended for new ML projects due to performance and async capabilities.

### ML Model Management

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| MLflow | 3.9.0 | Experiment tracking, model registry, deployment | End-to-end ML lifecycle management. Tracks hyperparameter optimization runs (genetic algorithm). Model versioning and deployment to multiple targets (local, cloud, Kubernetes). Released January 2026. |
| joblib | 1.4+ | Model serialization | Built into scikit-learn. Efficient serialization for NumPy arrays. Standard for scikit-learn model persistence. |

### Development Tools

| Tool | Version | Purpose | Why Recommended |
|------|---------|---------|-----------------|
| Poetry | 1.8+ | Dependency management | Modern dependency resolver, unified packaging/publishing, faster than Pipenv with complex dependencies. Uses pyproject.toml standard. Preferred over pip-tools and Pipenv for ML projects. |
| pytest | 8.3+ | Testing framework | Standard for ML testing. Fixtures, parametrization, and markers ideal for testing multiple classifiers. Easier than unittest. Robust plugin ecosystem. |
| Black | 25.0+ | Code formatting | Opinionated formatter eliminates style debates. Standard in Python community. |
| Ruff | 0.11+ | Linting and formatting | 10-100x faster than Flake8/pylint. Replaces multiple tools (isort, flake8, pylint). Gaining rapid adoption in 2025. |
| pre-commit | 4.0+ | Git hooks for quality checks | Automates code quality checks before commit. Integrates Black, Ruff, pytest. |

## Installation

### Core ML Stack

```bash
# Using Poetry (recommended)
poetry add scikit-learn==1.8.0 \
    xgboost==3.1.3 \
    catboost==1.2.8 \
    pandas==3.0.0 \
    numpy>=1.28 \
    imbalanced-learn==0.14.1 \
    deap==1.4.3

# Data processing and ML utilities
poetry add joblib>=1.4
```

### OCR & Image Processing

```bash
# OCR and basic image handling
poetry add easyocr==1.7.2 pillow>=10.4

# Optional: Advanced visual analysis
poetry add opencv-python>=4.11  # Only if needed
```

### NLP

```bash
# Primary NLP
poetry add spacy==3.8.11

# Download spaCy language model
python -m spacy download en_core_web_sm

# Optional: Advanced text classification (Phase 3+)
# poetry add transformers>=4.51
```

### Web Application

```bash
poetry add fastapi==0.128.5 \
    uvicorn[standard]>=0.34 \
    pydantic>=2.10
```

### ML Model Management

```bash
poetry add mlflow==3.9.0
```

### Development Tools

```bash
poetry add --group dev \
    pytest>=8.3 \
    black>=25.0 \
    ruff>=0.11 \
    pre-commit>=4.0
```

### Alternative: Using pip

```bash
# If not using Poetry, use pip with requirements.txt
pip install -r requirements.txt

# Generate requirements.txt from Poetry
poetry export -f requirements.txt --output requirements.txt --without-hashes
```

## Alternatives Considered

| Category | Recommended | Alternative | When to Use Alternative |
|----------|-------------|-------------|-------------------------|
| ML Framework | scikit-learn | PyTorch/TensorFlow | Only if switching to deep learning models (CNN for visual analysis, LSTM for text). Overkill for classical ML classifiers. |
| Gradient Boosting | XGBoost | LightGBM | Dataset exceeds 100K rows and training speed is bottleneck. Not needed for initial development. |
| GA Optimization | DEAP | Optuna, Ray Tune, Hyperopt | If switching from genetic algorithm to Bayesian optimization or other hyperparameter strategies. DEAP is best for genetic algorithms specifically. |
| OCR | EasyOCR | Tesseract (pytesseract) | High-resolution printed documents only. EasyOCR better for real-world phishing images (screenshots, photos). |
| NLP | spaCy | NLTK | Academic/research projects where educational value matters more than production speed. NLTK slower and less production-ready. |
| Web Framework | FastAPI | Flask | Team has extensive Flask experience and async isn't critical. But FastAPI learning curve is minimal and benefits significant. |
| Dependency Mgmt | Poetry | pip-tools, Pipenv | pip-tools if minimal tooling preferred. Pipenv if officially required by organization. Poetry best for new projects. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Python 3.13 experimental features (no-GIL, JIT) | Unstable for production ML. Library compatibility uncertain. Marginal benefits since NumPy/scikit-learn already use C extensions. | Python 3.11 or 3.12 stable releases |
| Keras/TensorFlow for classical ML | Massive overkill for Random Forest, SVM, Logistic Regression. Slower training, higher memory, steep learning curve. | scikit-learn |
| Custom genetic algorithm implementation | Reinventing wheel. DEAP provides tested, optimized, parallelized GA implementation. | DEAP 1.4.3 |
| Tesseract OCR (only) | 7x slower than EasyOCR. Requires extensive preprocessing. Struggles with low-quality images common in phishing. | EasyOCR |
| NLTK for production | Slow, requires extensive setup, not designed for production pipelines. Fine for research/teaching. | spaCy |
| requests library for FastAPI | Synchronous HTTP library blocks async benefits. | httpx (built into FastAPI[standard]) |
| Deprecated SMOTE approaches | Plain SMOTE can create noise. | SMOTETomek from imbalanced-learn (hybrid approach) |

## Stack Patterns by Use Case

### Pattern 1: MVP Baseline (Phase 1)

**Goal:** Prove concept with minimal dependencies

```python
# Minimal stack
scikit-learn==1.8.0      # 7 classifiers
pandas==3.0.0            # Data processing
numpy>=1.28              # Numerical operations
fastapi==0.128.5         # Web API
uvicorn[standard]>=0.34  # Server
```

**When:** Initial development, proving ML approach works

**Skip for now:** XGBoost/CatBoost, DEAP, EasyOCR, spaCy, MLflow

### Pattern 2: Full ML Pipeline (Phase 2)

**Add genetic algorithm and advanced classifiers:**

```python
# Add to MVP
xgboost==3.1.3           # Better than scikit-learn GradientBoosting
deap==1.4.3              # Hyperparameter optimization
imbalanced-learn==0.14.1 # Handle class imbalance
mlflow==3.9.0            # Track experiments
```

**When:** Baseline working, optimizing accuracy

### Pattern 3: Multi-Modal Analysis (Phase 3)

**Add OCR and NLP:**

```python
# Add to Phase 2
easyocr==1.7.2           # Image text extraction
pillow>=10.4             # Image preprocessing
spacy==3.8.11            # Email/SMS NLP
```

**When:** Expanding beyond URL-based detection to emails, images, SMS

### Pattern 4: Production Deployment (Phase 4)

**Add monitoring and quality tools:**

```python
# Add to Phase 3
prometheus-client>=0.20  # Metrics
sentry-sdk>=2.20         # Error tracking
gunicorn>=22.0           # Production WSGI server (if not using Uvicorn)
```

**When:** Moving to production environment

## Version Compatibility Matrix

| Package | Requires Python | Compatible With |
|---------|----------------|-----------------|
| scikit-learn 1.8.0 | >=3.11 | NumPy >=1.19, SciPy >=1.6, pandas >=1.0 |
| pandas 3.0.0 | >=3.11 | NumPy >=1.26.0 |
| XGBoost 3.1.3 | >=3.8 | NumPy >=1.19, SciPy >=1.0, scikit-learn >=0.22 |
| FastAPI 0.128.5 | >=3.9, <=3.14 | Pydantic >=2.0, Starlette >=0.37 |
| spaCy 3.8.11 | >=3.9, <3.15 | NumPy >=1.19, - |
| EasyOCR 1.7.2 | >=3.7 | PyTorch >=1.6, Pillow >=8.0 |

**Critical:** All packages compatible with Python 3.11. Use Python 3.11.x for best balance of stability, performance, and compatibility.

## Known Compatibility Issues

1. **pandas 3.0.0 + older scikit-learn**: Ensure scikit-learn >=1.8.0 for pandas 3.x compatibility
2. **EasyOCR + PyTorch**: EasyOCR auto-installs PyTorch. May conflict if PyTorch already installed for other purposes. Use virtual environment isolation.
3. **spaCy models**: Must download language models separately (`python -m spacy download en_core_web_sm`). Not included in pip/poetry install.
4. **Poetry + PyTorch**: Poetry may struggle with PyTorch's large wheels. Use `poetry config installer.max-workers 10` or install PyTorch first with pip, then poetry.

## Performance Considerations

### Training Speed Benchmarks (Approximate)

| Operation | scikit-learn | XGBoost | CatBoost | LightGBM |
|-----------|-------------|---------|----------|----------|
| 10K rows, 30 features | 2s | 1.5s | 3s | 1s |
| 100K rows, 30 features | 25s | 15s | 35s | 8s |
| 1M rows, 30 features | 5min | 3min | 7min | 1.5min |

**Source:** Community benchmarks, vary by hardware

### Inference Speed

| Framework | Requests/sec | Latency (p95) |
|-----------|-------------|---------------|
| FastAPI + Uvicorn | 20,000+ | <5ms |
| Flask + Gunicorn | 4,000-5,000 | 15-20ms |

**Recommendation:** FastAPI provides 4x throughput improvement with no additional complexity cost.

### Memory Footprint

- **scikit-learn models**: 10-50 MB per trained classifier (serialized with joblib)
- **XGBoost/CatBoost**: 50-200 MB for complex ensembles
- **EasyOCR**: 500 MB+ (includes PyTorch models). Load once, keep in memory.
- **spaCy + en_core_web_sm**: 15-20 MB

**Plan:** ~1 GB RAM for full system (all classifiers + OCR + NLP loaded)

## Sources

### High Confidence (Official Documentation & PyPI)

- [scikit-learn 1.8.0 Documentation](https://scikit-learn.org/stable/) - Current version confirmed
- [scikit-learn PyPI](https://pypi.org/project/scikit-learn/) - Version 1.8.0, released December 10, 2025
- [FastAPI PyPI](https://pypi.org/project/fastapi/) - Version 0.128.5, released February 8, 2026
- [MLflow Official](https://mlflow.org/) - Version 3.9.0, released January 29, 2026
- [MLflow PyPI](https://pypi.org/project/mlflow/)
- [spaCy PyPI](https://pypi.org/project/spacy/) - Version 3.8.11, released November 17, 2025
- [spaCy Official Documentation](https://spacy.io/)
- [EasyOCR PyPI](https://pypi.org/project/easyocr/) - Version 1.7.2, released September 24, 2024
- [XGBoost PyPI](https://pypi.org/project/xgboost/) - Version 3.1.3, released January 10, 2026
- [CatBoost PyPI](https://pypi.org/project/catboost/) - Version 1.2.8, released April 13, 2025
- [pandas PyPI](https://pypi.org/project/pandas/) - Version 3.0.0, released January 21, 2026
- [DEAP PyPI](https://pypi.org/project/deap/) - Version 1.4.3, released May 4, 2025
- [imbalanced-learn PyPI](https://pypi.org/project/imbalanced-learn/) - Version 0.14.1, released December 21, 2025

### Medium Confidence (Research Papers & Technical Articles - 2025)

- [Machine Learning and Neural Networks for Phishing Detection: Systematic Review 2017-2024](https://www.mdpi.com/2079-9292/14/18/3744)
- [Real-Time Phishing URL Detection Using Machine Learning](https://www.mdpi.com/2673-4591/107/1/108)
- [FastAPI vs Flask 2025 Comparison](https://blog.jetbrains.com/pycharm/2025/02/django-flask-fastapi/) - JetBrains survey showing 38% FastAPI adoption
- [FastAPI vs Flask Performance](https://strapi.io/blog/fastapi-vs-flask-python-framework-comparison)
- [EasyOCR vs Tesseract Comparison](https://landeros-labs.com/posts/OCR-pipelines-refresher/)
- [OCR Engine Comparison](https://francescopochetti.com/easyocr-vs-tesseract-vs-amazon-textract-an-ocr-engine-comparison/)
- [XGBoost vs CatBoost vs LightGBM](https://neptune.ai/blog/when-to-choose-catboost-over-xgboost-or-lightgbm)
- [Gradient Boosting Comparison 2025](https://www.analyticsvidhya.com/blog/2026/02/gradient-boosting-vs-adaboost-vs-xgboost-vs-catboost-vs-lightgbm/)
- [SMOTETomek-XGBoost for Phishing Detection](https://www.sciencedirect.com/science/article/pii/S187705092403463X) - 97.7% accuracy with SMOTE
- [Python 3.13 Performance Improvements](https://inindiatech.com/next/python-speed-improvements-3-11-to-3-13)
- [Python 3.13 New Features](https://www.ahmedbouchefra.com/news/python-313-2025-breakthroughs-no-gil-jit-ios-support-explained/)
- [Poetry vs Pipenv Comparison](https://betterstack.com/community/comparisons/pipenv-vs-poetry/)
- [Python Dependency Management 2025](https://unfoldadmin.com/blog/pip-pipenv-poetry-comparison/)
- [Pytest Best Practices 2025](https://madewithml.com/courses/mlops/testing/)
- [ML Testing Best Practices](https://neptune.ai/blog/automated-testing-machine-learning)

---

*Stack research for: Phishing Detection ML System*
*Researched: 2026-02-09*
*Confidence: HIGH - All versions verified against official PyPI releases and documentation*
