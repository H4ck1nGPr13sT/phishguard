# PhishGuard

Multi-paradigm phishing detection system combining machine learning, genetic algorithms, rule-based expert systems, and Bayesian probabilistic analysis.

## Overview

PhishGuard integrates four analytical approaches to detect phishing attacks:
- **Machine Learning**: 7 classifiers (Random Forest, SVM, MLP, Gradient Boosting, Logistic Regression, Naive Bayes, Decision Tree)
- **Genetic Algorithms**: Hyperparameter optimization
- **Rule-Based System**: Expert knowledge encoding
- **Bayesian Analysis**: Probabilistic classification

The system analyzes emails, SMS messages, text content, and images (via OCR).

## Installation

### Requirements
- Python 3.9+
- pip

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd phishguard
   ```

2. Install dependencies:
   ```bash
   pip install -e .
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your settings:
   # - DATA_DIR: Path to store downloaded datasets
   # - CACHE_DIR: Path for processed data cache
   # - PHISHTANK_API_KEY: (Optional) PhishTank API key
   ```

## Usage

### Data Pipeline

The data pipeline downloads, validates, and preprocesses phishing datasets:

```python
from src.data.pipeline import DataPipelineConfig, run_pipeline

# Configure pipeline
config = DataPipelineConfig(
    phishtank_api_key="your_key",  # Optional
    balance_target_ratio=0.5,
    random_seed=42
)

# Run pipeline
results = run_pipeline(config)

# Access processed data
X_train, y_train = results['train']
X_val, y_val = results['val']
X_test, y_test = results['test']

# View reports
print(results['reports']['balance'])
```

### Loading Cached Data

After running the pipeline once, load cached data:

```python
from src.data.pipeline import load_cached_splits
from src.config.settings import CACHE_DIR

splits = load_cached_splits(CACHE_DIR)
X_train, y_train = splits['train']
```

## Data Sources

PhishGuard uses multiple public phishing datasets:

| Source | Type | Description |
|--------|------|-------------|
| PhishTank | URLs | Verified phishing URLs (requires API key) |
| UCI ML Repository | Features | Pre-extracted URL features |
| Nazario Corpus | Emails | Phishing email collection |

## Project Structure

```
phishguard/
├── src/
│   ├── config/          # Configuration management
│   ├── data/
│   │   ├── downloaders/ # Dataset download modules
│   │   ├── validators/  # Data validation (Pandera schemas)
│   │   └── preprocessors/ # Temporal split, balancing
│   └── utils/           # Logging, caching utilities
├── .env.example         # Environment template
├── pyproject.toml       # Project dependencies
└── README.md
```

## Key Features

### Temporal Validation
Data is split temporally (70% train, 15% validation, 15% test) to prevent data leakage. Training data is always from before validation/test data.

### Class Imbalance Handling
SMOTE + undersampling is applied only to training data with configurable target ratio.

### Reproducibility
- All random operations use configurable seed (default: 42)
- Processed datasets are cached for consistent experiments

## Academic Context

This system is developed as part of an engineering thesis on phishing detection. The multi-paradigm approach demonstrates synergy between different analytical methods, with classifier disagreement providing additional context for classification decisions.

## License

[To be determined]

## Contributing

[To be determined]
