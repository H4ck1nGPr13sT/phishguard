"""Machine learning model training and evaluation module.

This module provides tools for training Random Forest classifiers on phishing
detection data, evaluating model performance, and making predictions.
"""

from src.models.train import train_model, create_pipeline
from src.models.evaluate import evaluate_model, print_evaluation_report
from src.models.predict import load_model, predict_single, predict_batch

__all__ = [
    'train_model',
    'create_pipeline',
    'evaluate_model',
    'print_evaluation_report',
    'load_model',
    'predict_single',
    'predict_batch'
]
