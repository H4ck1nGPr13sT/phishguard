#!/usr/bin/env python3
"""Retrain all classifiers using real URL data from OpenPhish + legitimate URLs.

This script addresses the feature mismatch issue where models were trained on
UCI ML pre-encoded features but inference uses our custom extracted features.

Solution: Extract features from real URLs, train on those features.
"""

import logging
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Legitimate URLs - well-known safe domains
LEGITIMATE_URLS = [
    # Major tech companies
    "https://www.google.com",
    "https://www.google.com/search?q=weather",
    "https://www.google.com/maps",
    "https://mail.google.com",
    "https://drive.google.com",
    "https://www.youtube.com",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.facebook.com",
    "https://www.facebook.com/marketplace",
    "https://www.instagram.com",
    "https://www.twitter.com",
    "https://x.com",
    "https://www.linkedin.com",
    "https://www.linkedin.com/jobs",
    "https://www.microsoft.com",
    "https://www.office.com",
    "https://outlook.live.com",
    "https://www.apple.com",
    "https://www.icloud.com",
    "https://www.amazon.com",
    "https://www.amazon.com/dp/B08N5WRWNW",
    "https://aws.amazon.com",
    "https://www.netflix.com",
    "https://www.spotify.com",
    "https://www.reddit.com",
    "https://www.reddit.com/r/programming",
    "https://www.wikipedia.org",
    "https://en.wikipedia.org/wiki/Phishing",
    "https://www.github.com",
    "https://github.com/openai/gpt-4",
    "https://stackoverflow.com",
    "https://stackoverflow.com/questions",

    # Banks and financial (legitimate)
    "https://www.chase.com",
    "https://www.bankofamerica.com",
    "https://www.wellsfargo.com",
    "https://www.paypal.com",
    "https://www.venmo.com",
    "https://www.stripe.com",

    # E-commerce
    "https://www.ebay.com",
    "https://www.walmart.com",
    "https://www.target.com",
    "https://www.bestbuy.com",
    "https://www.etsy.com",
    "https://www.aliexpress.com",

    # News and media
    "https://www.nytimes.com",
    "https://www.cnn.com",
    "https://www.bbc.com",
    "https://www.reuters.com",
    "https://www.theguardian.com",

    # Educational
    "https://www.coursera.org",
    "https://www.udemy.com",
    "https://www.edx.org",
    "https://www.khanacademy.org",
    "https://www.mit.edu",
    "https://www.stanford.edu",
    "https://www.harvard.edu",

    # Government
    "https://www.usa.gov",
    "https://www.irs.gov",
    "https://www.ssa.gov",
    "https://www.cdc.gov",

    # Cloud services
    "https://www.dropbox.com",
    "https://www.box.com",
    "https://www.zoom.us",
    "https://www.slack.com",
    "https://www.notion.so",
    "https://www.figma.com",
    "https://www.canva.com",

    # Software/tools
    "https://www.adobe.com",
    "https://www.autodesk.com",
    "https://www.salesforce.com",
    "https://www.atlassian.com",
    "https://www.jetbrains.com",
    "https://code.visualstudio.com",

    # Travel
    "https://www.booking.com",
    "https://www.airbnb.com",
    "https://www.expedia.com",
    "https://www.tripadvisor.com",
    "https://www.united.com",
    "https://www.delta.com",

    # Food delivery
    "https://www.doordash.com",
    "https://www.ubereats.com",
    "https://www.grubhub.com",

    # Health
    "https://www.webmd.com",
    "https://www.mayoclinic.org",
    "https://www.healthline.com",

    # More tech
    "https://www.oracle.com",
    "https://www.ibm.com",
    "https://www.cisco.com",
    "https://www.intel.com",
    "https://www.nvidia.com",
    "https://www.amd.com",

    # Entertainment
    "https://www.twitch.tv",
    "https://www.hulu.com",
    "https://www.disneyplus.com",
    "https://www.hbomax.com",
    "https://www.primevideo.com",

    # Social/communication
    "https://www.whatsapp.com",
    "https://www.telegram.org",
    "https://www.discord.com",
    "https://www.signal.org",

    # Search engines
    "https://www.bing.com",
    "https://www.duckduckgo.com",
    "https://www.yahoo.com",

    # Polish sites (user's locale)
    "https://www.allegro.pl",
    "https://www.olx.pl",
    "https://www.wp.pl",
    "https://www.onet.pl",
    "https://www.interia.pl",
    "https://www.pkobp.pl",
    "https://www.mbank.pl",
    "https://www.ing.pl",

    # Additional legitimate with various patterns
    "https://support.google.com/accounts",
    "https://help.netflix.com",
    "https://developer.mozilla.org",
    "https://docs.python.org/3/",
    "https://numpy.org/doc/stable/",
    "https://pandas.pydata.org",
    "https://scikit-learn.org",
    "https://pytorch.org",
    "https://www.tensorflow.org",
    "https://huggingface.co",

    # URLs with query params (legitimate)
    "https://www.google.com/search?q=machine+learning&hl=en",
    "https://www.amazon.com/s?k=laptop&ref=nb_sb_noss",
    "https://www.youtube.com/results?search_query=python+tutorial",
    "https://www.linkedin.com/search/results/people/?keywords=data%20scientist",
]


def load_phishing_urls(path: Path) -> list:
    """Load phishing URLs from OpenPhish feed file."""
    with open(path) as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return urls


def extract_features_batch(urls: list, labels: list) -> pd.DataFrame:
    """Extract features from URLs in batch."""
    from src.features.extractors import extract_url_features

    records = []
    failed = 0

    for url, label in zip(urls, labels):
        try:
            features = extract_url_features(url)
            features['label'] = label
            features['url'] = url
            records.append(features)
        except Exception as e:
            failed += 1
            logger.warning(f"Failed to extract features from {url[:50]}...: {e}")

    if failed > 0:
        logger.warning(f"Failed to extract features from {failed}/{len(urls)} URLs")

    return pd.DataFrame(records)


def train_classifiers(X_train: np.ndarray, y_train: np.ndarray, output_dir: Path) -> dict:
    """Train all 7 classifiers on the new feature data."""
    from src.models.classifiers import create_classifiers
    from sklearn.model_selection import cross_val_score

    output_dir.mkdir(parents=True, exist_ok=True)

    classifiers = create_classifiers()
    metrics = {}

    for name, pipeline in classifiers.items():
        logger.info(f"Training {name}...")
        start = time.time()

        # Train
        pipeline.fit(X_train, y_train)

        # Evaluate with cross-validation
        cv_scores = cross_val_score(pipeline, X_train, y_train, cv=5)
        train_acc = pipeline.score(X_train, y_train)

        duration = time.time() - start

        metrics[name] = {
            'train_accuracy': train_acc,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std(),
            'duration': duration
        }

        # Save model
        model_path = output_dir / f"{name}_pipeline.joblib"
        joblib.dump(pipeline, model_path, compress=3, protocol=5)

        logger.info(f"  {name}: CV={cv_scores.mean():.4f} (+/- {cv_scores.std():.4f}) in {duration:.1f}s")

    return metrics


def train_ensembles(X_train: np.ndarray, y_train: np.ndarray, output_dir: Path) -> dict:
    """Train ensemble models on the new feature data."""
    from src.models.classifiers import create_classifiers
    from src.models.ensemble import create_voting_ensemble, create_stacking_ensemble

    ensemble_dir = output_dir / "ensemble"
    ensemble_dir.mkdir(parents=True, exist_ok=True)

    # Get fresh classifiers for ensemble (they'll be fitted by ensemble)
    classifiers = create_classifiers()
    estimators = [(name, clf) for name, clf in classifiers.items()]

    metrics = {}

    # Soft voting
    logger.info("Training soft voting ensemble...")
    start = time.time()
    voting_soft = create_voting_ensemble(estimators, voting='soft')
    voting_soft.fit(X_train, y_train)
    soft_acc = voting_soft.score(X_train, y_train)
    joblib.dump(voting_soft, ensemble_dir / "voting_soft.joblib", compress=3, protocol=5)
    metrics['voting_soft'] = {'accuracy': soft_acc, 'duration': time.time() - start}
    logger.info(f"  Soft voting: {soft_acc:.4f}")

    # Hard voting
    logger.info("Training hard voting ensemble...")
    start = time.time()
    classifiers = create_classifiers()
    estimators = [(name, clf) for name, clf in classifiers.items()]
    voting_hard = create_voting_ensemble(estimators, voting='hard')
    voting_hard.fit(X_train, y_train)
    hard_acc = voting_hard.score(X_train, y_train)
    joblib.dump(voting_hard, ensemble_dir / "voting_hard.joblib", compress=3, protocol=5)
    metrics['voting_hard'] = {'accuracy': hard_acc, 'duration': time.time() - start}
    logger.info(f"  Hard voting: {hard_acc:.4f}")

    # Stacking
    logger.info("Training stacking ensemble (this takes longer due to 5-fold CV)...")
    start = time.time()
    classifiers = create_classifiers()
    estimators = [(name, clf) for name, clf in classifiers.items()]
    stacking = create_stacking_ensemble(estimators)
    stacking.fit(X_train, y_train)
    stack_acc = stacking.score(X_train, y_train)
    joblib.dump(stacking, ensemble_dir / "stacking.joblib", compress=3, protocol=5)
    metrics['stacking'] = {'accuracy': stack_acc, 'duration': time.time() - start}
    logger.info(f"  Stacking: {stack_acc:.4f}")

    return metrics


def main():
    """Main retraining pipeline."""
    logger.info("=" * 80)
    logger.info("RETRAINING MODELS WITH REAL URL DATA")
    logger.info("=" * 80)

    # Paths
    cache_dir = Path("cache")
    models_dir = Path("models")
    phishing_file = cache_dir / "openphish_urls.txt"

    # 1. Load URLs
    logger.info("\n1. Loading URLs...")
    phishing_urls = load_phishing_urls(phishing_file)
    legitimate_urls = LEGITIMATE_URLS

    logger.info(f"   Phishing URLs: {len(phishing_urls)}")
    logger.info(f"   Legitimate URLs: {len(legitimate_urls)}")

    # 2. Create balanced dataset
    # Use all phishing URLs, sample legitimate to match
    n_samples = min(len(phishing_urls), len(legitimate_urls))

    # If we have more phishing than legitimate, sample phishing down
    if len(phishing_urls) > len(legitimate_urls):
        np.random.seed(42)
        phishing_urls = list(np.random.choice(phishing_urls, size=len(legitimate_urls), replace=False))
    elif len(legitimate_urls) > len(phishing_urls):
        np.random.seed(42)
        legitimate_urls = list(np.random.choice(legitimate_urls, size=len(phishing_urls), replace=False))

    all_urls = phishing_urls + legitimate_urls
    all_labels = [1] * len(phishing_urls) + [0] * len(legitimate_urls)

    logger.info(f"   Balanced dataset: {len(phishing_urls)} phishing + {len(legitimate_urls)} legitimate")

    # 3. Extract features
    logger.info("\n2. Extracting features from URLs...")
    df = extract_features_batch(all_urls, all_labels)

    logger.info(f"   Successfully extracted features from {len(df)} URLs")
    logger.info(f"   Features: {len(df.columns) - 2}")  # -2 for label and url

    # 4. Prepare training data
    feature_cols = [c for c in df.columns if c not in ['label', 'url']]
    X = df[feature_cols].values
    y = df['label'].values

    # Split for final evaluation
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    logger.info(f"\n3. Training data: {len(X_train)} samples")
    logger.info(f"   Test data: {len(X_test)} samples")

    # 5. Train classifiers
    logger.info("\n4. Training individual classifiers...")
    clf_metrics = train_classifiers(X_train, y_train, models_dir)

    # 6. Train ensembles
    logger.info("\n5. Training ensemble models...")
    ens_metrics = train_ensembles(X_train, y_train, models_dir)

    # 7. Final evaluation on test set
    logger.info("\n6. Final evaluation on test set...")

    from src.models.classifiers import create_classifiers

    # Load and evaluate each classifier
    for name in clf_metrics.keys():
        model = joblib.load(models_dir / f"{name}_pipeline.joblib")
        test_acc = model.score(X_test, y_test)
        clf_metrics[name]['test_accuracy'] = test_acc
        logger.info(f"   {name}: {test_acc:.4f}")

    # Load and evaluate ensembles
    for name in ens_metrics.keys():
        model = joblib.load(models_dir / "ensemble" / f"{name}.joblib")
        test_acc = model.score(X_test, y_test)
        ens_metrics[name]['test_accuracy'] = test_acc
        logger.info(f"   {name}: {test_acc:.4f}")

    # 8. Summary
    logger.info("\n" + "=" * 80)
    logger.info("RETRAINING COMPLETE")
    logger.info("=" * 80)
    logger.info("\nIndividual Classifiers (Test Accuracy):")
    for name, m in sorted(clf_metrics.items(), key=lambda x: x[1].get('test_accuracy', 0), reverse=True):
        logger.info(f"  {name:6}: {m.get('test_accuracy', 0):.4f}")

    logger.info("\nEnsemble Models (Test Accuracy):")
    for name, m in sorted(ens_metrics.items(), key=lambda x: x[1].get('test_accuracy', 0), reverse=True):
        logger.info(f"  {name:12}: {m.get('test_accuracy', 0):.4f}")

    # Save training cache for reference
    cache_data = {
        'X_train': X_train,
        'y_train': y_train,
        'X_test': X_test,
        'y_test': y_test,
        'feature_names': feature_cols,
        'clf_metrics': clf_metrics,
        'ens_metrics': ens_metrics,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    joblib.dump(cache_data, cache_dir / "url_training_data.joblib", compress=3)
    logger.info(f"\nTraining data cached to {cache_dir / 'url_training_data.joblib'}")

    return clf_metrics, ens_metrics


if __name__ == "__main__":
    main()
