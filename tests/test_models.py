"""Tests for model training, evaluation, and prediction modules."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.models.train import create_pipeline, train_model
from src.models.evaluate import evaluate_model, print_evaluation_report
from src.models.predict import save_model, load_model, predict_single, predict_batch


class TestPipelineCreation:
    """Tests for create_pipeline()."""

    def test_create_pipeline_returns_pipeline(self):
        """Test that create_pipeline() returns sklearn Pipeline."""
        pipeline = create_pipeline()
        assert isinstance(pipeline, Pipeline)

    def test_pipeline_has_two_steps(self):
        """Test Pipeline has exactly 2 steps (scaler and classifier)."""
        pipeline = create_pipeline()
        assert len(pipeline.steps) == 2

    def test_pipeline_has_scaler_first(self):
        """Test Pipeline has StandardScaler as first step."""
        pipeline = create_pipeline()
        assert pipeline.steps[0][0] == 'scaler'
        assert isinstance(pipeline.steps[0][1], StandardScaler)

    def test_pipeline_has_random_forest_second(self):
        """Test Pipeline has RandomForestClassifier as second step."""
        pipeline = create_pipeline()
        assert pipeline.steps[1][0] == 'classifier'
        assert isinstance(pipeline.steps[1][1], RandomForestClassifier)

    def test_random_forest_has_balanced_class_weight(self):
        """Test RF classifier has class_weight='balanced'."""
        pipeline = create_pipeline()
        classifier = pipeline.named_steps['classifier']
        assert classifier.class_weight == 'balanced'

    def test_random_forest_has_200_estimators(self):
        """Test RF classifier has n_estimators=200."""
        pipeline = create_pipeline()
        classifier = pipeline.named_steps['classifier']
        assert classifier.n_estimators == 200


class TestModelPersistence:
    """Tests for save_model() and load_model()."""

    def test_save_model_creates_file(self):
        """Test save_model() creates .joblib file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / 'test_model.joblib'
            pipeline = create_pipeline()

            # Fit on dummy data
            X = pd.DataFrame(np.random.randn(100, 5))
            y = pd.Series(np.random.randint(0, 2, 100))
            pipeline.fit(X, y)

            save_model(pipeline, model_path)
            assert model_path.exists()

    def test_load_model_returns_pipeline(self):
        """Test load_model() returns same model type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / 'test_model.joblib'
            original_pipeline = create_pipeline()

            # Fit and save
            X = pd.DataFrame(np.random.randn(100, 5))
            y = pd.Series(np.random.randint(0, 2, 100))
            original_pipeline.fit(X, y)
            save_model(original_pipeline, model_path)

            # Load and check
            loaded_pipeline = load_model(model_path, check_version=False)
            assert isinstance(loaded_pipeline, Pipeline)
            assert len(loaded_pipeline.steps) == 2

    def test_saved_model_contains_sklearn_version(self):
        """Test saved model contains sklearn_version metadata."""
        import joblib
        import sklearn

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / 'test_model.joblib'
            pipeline = create_pipeline()

            X = pd.DataFrame(np.random.randn(100, 5))
            y = pd.Series(np.random.randint(0, 2, 100))
            pipeline.fit(X, y)
            save_model(pipeline, model_path)

            # Load raw data and check
            model_data = joblib.load(model_path)
            assert 'sklearn_version' in model_data
            assert model_data['sklearn_version'] == sklearn.__version__

    def test_version_mismatch_warning(self, caplog):
        """Test version mismatch produces warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / 'test_model.joblib'
            pipeline = create_pipeline()

            X = pd.DataFrame(np.random.randn(100, 5))
            y = pd.Series(np.random.randint(0, 2, 100))
            pipeline.fit(X, y)
            save_model(pipeline, model_path, metadata={'sklearn_version': '0.0.0'})

            # Mock the version check
            import joblib
            model_data = joblib.load(model_path)
            model_data['sklearn_version'] = '0.0.0'
            joblib.dump(model_data, model_path, compress=3, protocol=5)

            # Load with version check
            import logging
            with caplog.at_level(logging.WARNING):
                load_model(model_path, check_version=True)

            # Check warning was logged (check after context exits)
            warning_messages = [record.getMessage() for record in caplog.records if record.levelname == 'WARNING']
            assert any('sklearn' in msg.lower() or 'version' in msg.lower() for msg in warning_messages), f"No version warning found in: {warning_messages}"


class TestPrediction:
    """Tests for predict_single() and predict_batch()."""

    @pytest.fixture
    def trained_model(self):
        """Create a trained model for testing."""
        pipeline = create_pipeline()
        X = pd.DataFrame(np.random.randn(200, 5), columns=['f1', 'f2', 'f3', 'f4', 'f5'])
        y = pd.Series(np.random.randint(0, 2, 200))
        pipeline.fit(X, y)
        return pipeline

    def test_predict_single_returns_dict(self, trained_model):
        """Test predict_single() returns dict with required keys."""
        features = {'f1': 0.5, 'f2': -0.3, 'f3': 1.2, 'f4': 0.0, 'f5': -0.8}
        result = predict_single(trained_model, features)

        assert isinstance(result, dict)
        assert 'phishing_probability' in result
        assert 'prediction' in result
        assert 'confidence' in result

    def test_phishing_probability_in_valid_range(self, trained_model):
        """Test phishing_probability is between 0.0 and 1.0."""
        features = {'f1': 0.5, 'f2': -0.3, 'f3': 1.2, 'f4': 0.0, 'f5': -0.8}
        result = predict_single(trained_model, features)

        assert 0.0 <= result['phishing_probability'] <= 1.0

    def test_prediction_is_valid_class(self, trained_model):
        """Test prediction is 'phishing' or 'legitimate'."""
        features = {'f1': 0.5, 'f2': -0.3, 'f3': 1.2, 'f4': 0.0, 'f5': -0.8}
        result = predict_single(trained_model, features)

        assert result['prediction'] in ['phishing', 'legitimate']

    def test_predict_batch_handles_multiple_inputs(self, trained_model):
        """Test predict_batch() handles multiple inputs."""
        features_list = [
            {'f1': 0.5, 'f2': -0.3, 'f3': 1.2, 'f4': 0.0, 'f5': -0.8},
            {'f1': -0.5, 'f2': 0.3, 'f3': -1.2, 'f4': 0.5, 'f5': 0.8},
            {'f1': 1.0, 'f2': 1.0, 'f3': 1.0, 'f4': 1.0, 'f5': 1.0}
        ]

        results = predict_batch(trained_model, features_list)

        assert len(results) == 3
        assert all('phishing_probability' in r for r in results)
        assert all('prediction' in r for r in results)


class TestEvaluation:
    """Tests for evaluate_model()."""

    @pytest.fixture
    def trained_model_and_data(self):
        """Create trained model and test data."""
        pipeline = create_pipeline()
        X_train = pd.DataFrame(np.random.randn(200, 5))
        y_train = pd.Series(np.random.randint(0, 2, 200))
        pipeline.fit(X_train, y_train)

        X_test = pd.DataFrame(np.random.randn(50, 5))
        y_test = pd.Series(np.random.randint(0, 2, 50))

        return pipeline, X_test, y_test

    def test_evaluate_model_returns_dict(self, trained_model_and_data):
        """Test evaluate_model() returns dict with required metrics."""
        model, X_test, y_test = trained_model_and_data
        metrics = evaluate_model(model, X_test, y_test)

        assert isinstance(metrics, dict)
        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1_score' in metrics
        assert 'roc_auc' in metrics

    def test_metrics_in_valid_ranges(self, trained_model_and_data):
        """Test metrics are in valid ranges (0-1)."""
        model, X_test, y_test = trained_model_and_data
        metrics = evaluate_model(model, X_test, y_test)

        assert 0.0 <= metrics['accuracy'] <= 1.0
        assert 0.0 <= metrics['precision'] <= 1.0
        assert 0.0 <= metrics['recall'] <= 1.0
        assert 0.0 <= metrics['f1_score'] <= 1.0
        assert 0.0 <= metrics['roc_auc'] <= 1.0

    def test_confusion_matrix_has_all_values(self, trained_model_and_data):
        """Test confusion_matrix has all four values."""
        model, X_test, y_test = trained_model_and_data
        metrics = evaluate_model(model, X_test, y_test)

        assert 'confusion_matrix' in metrics
        cm = metrics['confusion_matrix']
        assert 'true_negative' in cm
        assert 'false_positive' in cm
        assert 'false_negative' in cm
        assert 'true_positive' in cm

    def test_print_evaluation_report_runs(self, trained_model_and_data, capsys):
        """Test print_evaluation_report() executes without errors."""
        model, X_test, y_test = trained_model_and_data
        metrics = evaluate_model(model, X_test, y_test)

        # Should not raise exception
        print_evaluation_report(metrics)

        # Check output contains expected strings
        captured = capsys.readouterr()
        assert 'Accuracy' in captured.out
        assert 'Precision' in captured.out
        assert 'Confusion Matrix' in captured.out


class TestModelAccuracy:
    """Integration test: Verify trained model meets 90%+ accuracy requirement."""

    def test_trained_model_achieves_90_percent_accuracy(self):
        """Test that the trained model achieves 90%+ accuracy or OOB score."""
        from src.data.pipeline import load_cached_splits

        try:
            # Load cached data
            splits = load_cached_splits()
            X_train, y_train = splits['train']
            X_val, y_val = splits['val']
            X_test, y_test = splits['test']

            # Filter to numeric features
            metadata_cols = ['url', 'content', 'timestamp', 'source']
            feature_cols = [col for col in X_train.columns if col not in metadata_cols]

            # Load trained model
            model_path = Path('models/rf_pipeline.joblib')
            if not model_path.exists():
                pytest.skip("Trained model not found. Run train_model.py first.")

            model = load_model(model_path, check_version=False)

            # If test set is not empty, evaluate on test set
            if len(X_test) > 0:
                X_test_features = X_test[feature_cols]
                metrics = evaluate_model(model, X_test_features, y_test)

                print("\n" + "=" * 80)
                print("MODEL EVALUATION - TEST SET")
                print("=" * 80)
                print_evaluation_report(metrics)

                # Assert 90%+ accuracy
                assert metrics['accuracy'] >= 0.90, (
                    f"Model accuracy {metrics['accuracy']:.2%} is below 90% threshold"
                )
            else:
                # Use OOB score if test set is empty
                classifier = model.named_steps['classifier']
                oob_score = classifier.oob_score_

                print("\n" + "=" * 80)
                print("MODEL EVALUATION - OOB SCORE")
                print("=" * 80)
                print(f"OOB Score: {oob_score:.4f}")
                print("=" * 80)

                # Assert 90%+ OOB score
                assert oob_score >= 0.90, (
                    f"Model OOB score {oob_score:.2%} is below 90% threshold"
                )

                if oob_score >= 0.90:
                    print("✓ SUCCESS: OOB score meets 90%+ requirement")
                print("=" * 80)

        except FileNotFoundError as e:
            pytest.skip(f"Cache files not found: {e}. Run Phase 1 pipeline first.")
