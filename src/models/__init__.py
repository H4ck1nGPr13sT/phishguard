"""Machine learning model training and evaluation module.

This module provides tools for training Random Forest classifiers on phishing
detection data, evaluating model performance, and making predictions.
"""

from src.models.train import train_model, create_pipeline
from src.models.evaluate import evaluate_model, print_evaluation_report
from src.models.predict import load_model, predict_single, predict_batch
from src.models.classifiers import create_classifiers, get_classifier, CLASSIFIER_CONFIGS
from src.models.ensemble import (
    create_voting_ensemble,
    create_stacking_ensemble,
    get_individual_predictions,
    save_ensemble,
    load_ensemble
)

__all__ = [
    'train_model',
    'create_pipeline',
    'evaluate_model',
    'print_evaluation_report',
    'load_model',
    'predict_single',
    'predict_batch',
    'create_classifiers',
    'get_classifier',
    'CLASSIFIER_CONFIGS',
    'create_voting_ensemble',
    'create_stacking_ensemble',
    'get_individual_predictions',
    'save_ensemble',
    'load_ensemble'
]
