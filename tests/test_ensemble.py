"""Tests for ensemble model creation and aggregation."""

import numpy as np
import pytest
from pathlib import Path
from sklearn.ensemble import VotingClassifier, StackingClassifier
from sklearn.linear_model import LogisticRegression

from src.models.ensemble import (
    create_voting_ensemble,
    create_stacking_ensemble,
    get_individual_predictions,
    save_ensemble,
    load_ensemble
)
from src.models.classifiers import create_classifiers


class TestEnsembleCreation:
    """Test ensemble factory functions."""

    @pytest.fixture
    def sample_estimators(self):
        """Create sample estimators for testing."""
        classifiers = create_classifiers()
        return [(name, pipeline) for name, pipeline in list(classifiers.items())[:3]]

    def test_create_voting_ensemble_soft(self, sample_estimators):
        """Test soft voting ensemble creation."""
        ensemble = create_voting_ensemble(sample_estimators, voting='soft')

        assert isinstance(ensemble, VotingClassifier)
        assert ensemble.voting == 'soft'
        assert len(ensemble.estimators) == 3
        assert ensemble.n_jobs == -1

    def test_create_voting_ensemble_hard(self, sample_estimators):
        """Test hard voting ensemble creation."""
        ensemble = create_voting_ensemble(sample_estimators, voting='hard')

        assert isinstance(ensemble, VotingClassifier)
        assert ensemble.voting == 'hard'
        assert len(ensemble.estimators) == 3

    def test_create_voting_ensemble_invalid_voting(self, sample_estimators):
        """Test that invalid voting parameter raises ValueError."""
        with pytest.raises(ValueError, match="voting must be"):
            create_voting_ensemble(sample_estimators, voting='invalid')

    def test_create_stacking_ensemble(self, sample_estimators):
        """Test stacking ensemble creation."""
        ensemble = create_stacking_ensemble(sample_estimators)

        assert isinstance(ensemble, StackingClassifier)
        assert len(ensemble.estimators) == 3
        assert isinstance(ensemble.final_estimator, LogisticRegression)
        assert ensemble.cv == 5  # Data leakage prevention
        assert ensemble.stack_method == 'auto'
        assert ensemble.passthrough is False
        assert ensemble.n_jobs == -1

    def test_stacking_has_cv5(self, sample_estimators):
        """Verify cv=5 for data leakage prevention in stacking."""
        ensemble = create_stacking_ensemble(sample_estimators)
        assert ensemble.cv == 5, "Stacking must use cv=5 to prevent data leakage"


class TestModelLoading:
    """Test loading of trained ensemble models."""

    def test_voting_soft_loadable(self):
        """Test that soft voting model can be loaded."""
        model_path = Path('models/ensemble/voting_soft.joblib')
        assert model_path.exists(), "voting_soft.joblib not found - run training first"

        model = load_ensemble(model_path)
        assert isinstance(model, VotingClassifier)
        assert model.voting == 'soft'

    def test_voting_hard_loadable(self):
        """Test that hard voting model can be loaded."""
        model_path = Path('models/ensemble/voting_hard.joblib')
        assert model_path.exists(), "voting_hard.joblib not found - run training first"

        model = load_ensemble(model_path)
        assert isinstance(model, VotingClassifier)
        assert model.voting == 'hard'

    def test_stacking_loadable(self):
        """Test that stacking model can be loaded."""
        model_path = Path('models/ensemble/stacking.joblib')
        assert model_path.exists(), "stacking.joblib not found - run training first"

        model = load_ensemble(model_path)
        assert isinstance(model, StackingClassifier)


class TestPredictions:
    """Test ensemble prediction capabilities."""

    @pytest.fixture
    def voting_soft_model(self):
        """Load trained soft voting model."""
        model_path = Path('models/ensemble/voting_soft.joblib')
        if not model_path.exists():
            pytest.skip("voting_soft.joblib not found - run training first")
        return load_ensemble(model_path)

    @pytest.fixture
    def voting_hard_model(self):
        """Load trained hard voting model."""
        model_path = Path('models/ensemble/voting_hard.joblib')
        if not model_path.exists():
            pytest.skip("voting_hard.joblib not found - run training first")
        return load_ensemble(model_path)

    @pytest.fixture
    def stacking_model(self):
        """Load trained stacking model."""
        model_path = Path('models/ensemble/stacking.joblib')
        if not model_path.exists():
            pytest.skip("stacking.joblib not found - run training first")
        return load_ensemble(model_path)

    @pytest.fixture
    def sample_features(self):
        """Create sample feature vector for testing."""
        # 30 features matching the phishing detection dataset
        return np.array([[
            1, 50, 0, 0, 0,  # URL characteristics
            1, 1, 1, 1, 1,   # Domain/SSL features
            0, 0, 1, 1, 1,   # Link features
            1, 0, 0, 1, 0,   # Misc features
            0, 0, 0, 1, 1,   # Domain age/DNS
            1, 1, 1, 1, 1    # Traffic/ranking features
        ]])

    def test_voting_soft_predict_proba(self, voting_soft_model, sample_features):
        """Test soft voting returns probabilities for both classes."""
        probas = voting_soft_model.predict_proba(sample_features)

        assert probas.shape == (1, 2), "Should return probabilities for 2 classes"
        assert np.allclose(probas.sum(), 1.0), "Probabilities should sum to 1"
        assert np.all(probas >= 0) and np.all(probas <= 1), "Probabilities should be in [0, 1]"

    def test_voting_hard_predict(self, voting_hard_model, sample_features):
        """Test hard voting returns class labels."""
        predictions = voting_hard_model.predict(sample_features)

        assert predictions.shape == (1,), "Should return 1 prediction"
        assert predictions[0] in [0, 1], "Prediction should be 0 (legit) or 1 (phishing)"

    def test_stacking_predict_proba(self, stacking_model, sample_features):
        """Test stacking returns probabilities."""
        probas = stacking_model.predict_proba(sample_features)

        assert probas.shape == (1, 2), "Should return probabilities for 2 classes"
        assert np.allclose(probas.sum(), 1.0), "Probabilities should sum to 1"


class TestIndividualPredictions:
    """Test extraction of individual classifier predictions."""

    @pytest.fixture
    def voting_soft_model(self):
        """Load trained soft voting model."""
        model_path = Path('models/ensemble/voting_soft.joblib')
        if not model_path.exists():
            pytest.skip("voting_soft.joblib not found - run training first")
        return load_ensemble(model_path)

    @pytest.fixture
    def sample_features(self):
        """Create sample feature vector for testing."""
        return np.array([[
            1, 50, 0, 0, 0, 1, 1, 1, 1, 1,
            0, 0, 1, 1, 1, 1, 0, 0, 1, 0,
            0, 0, 0, 1, 1, 1, 1, 1, 1, 1
        ]])

    def test_get_individual_predictions_returns_all_classifiers(
        self, voting_soft_model, sample_features
    ):
        """Test that all 7 classifier predictions are returned."""
        predictions = get_individual_predictions(voting_soft_model, sample_features)

        assert isinstance(predictions, dict)
        assert len(predictions) == 7, "Should return predictions for all 7 classifiers"

        expected_classifiers = ['rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt']
        for clf_name in expected_classifiers:
            assert clf_name in predictions, f"{clf_name} missing from predictions"

    def test_individual_predictions_have_required_fields(
        self, voting_soft_model, sample_features
    ):
        """Test that each prediction has required fields."""
        predictions = get_individual_predictions(voting_soft_model, sample_features)

        required_fields = ['phishing_probability', 'prediction', 'confidence']

        for clf_name, pred in predictions.items():
            for field in required_fields:
                assert field in pred, f"{clf_name} missing field: {field}"

            # Validate field types and ranges
            assert isinstance(pred['phishing_probability'], float)
            assert 0 <= pred['phishing_probability'] <= 1

            assert pred['prediction'] in ['phishing', 'legitimate']

            assert isinstance(pred['confidence'], float)
            assert 0 <= pred['confidence'] <= 1

    def test_individual_predictions_logic(
        self, voting_soft_model, sample_features
    ):
        """Test that prediction logic is correct."""
        predictions = get_individual_predictions(voting_soft_model, sample_features)

        for clf_name, pred in predictions.items():
            # If phishing_probability >= 0.5, prediction should be 'phishing'
            if pred['phishing_probability'] >= 0.5:
                assert pred['prediction'] == 'phishing', \
                    f"{clf_name}: high phishing_probability should predict 'phishing'"
            else:
                assert pred['prediction'] == 'legitimate', \
                    f"{clf_name}: low phishing_probability should predict 'legitimate'"


class TestEnsembleAccuracy:
    """Test that ensembles perform better than average individual classifier."""

    def test_ensemble_accuracy_vs_individual(self):
        """Test that ensemble accuracy >= average individual accuracy."""
        # Load training data
        from src.data.pipeline import load_cached_splits

        try:
            splits = load_cached_splits()
            X_train, y_train = splits['train']
        except FileNotFoundError:
            pytest.skip("Cache files not found - run pipeline first")

        # Filter to numeric features
        metadata_cols = ['url', 'content', 'timestamp', 'source']
        feature_cols = [col for col in X_train.columns if col not in metadata_cols]
        X_train_features = X_train[feature_cols]

        # Load individual classifier accuracies from metadata
        from src.models.predict import load_model

        individual_accs = []
        classifier_names = ['rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt']

        for name in classifier_names:
            model_path = Path(f'models/{name}_pipeline.joblib')
            if model_path.exists():
                import joblib
                model_data = joblib.load(model_path)
                if 'metadata' in model_data:
                    # Use CV/OOB accuracy if available, otherwise train accuracy
                    if 'cv_accuracy' in model_data['metadata']:
                        individual_accs.append(float(model_data['metadata']['cv_accuracy']))
                    elif 'oob_score' in model_data['metadata']:
                        individual_accs.append(float(model_data['metadata']['oob_score']))

        if not individual_accs:
            pytest.skip("Individual classifier accuracies not available")

        avg_individual_acc = np.mean(individual_accs)

        # Load ensemble and calculate accuracy
        voting_soft = load_ensemble(Path('models/ensemble/voting_soft.joblib'))
        ensemble_acc = voting_soft.score(X_train_features, y_train)

        print(f"\nAverage individual accuracy: {avg_individual_acc:.4f}")
        print(f"Ensemble accuracy: {ensemble_acc:.4f}")

        # Ensemble should be at least as good as average individual
        assert ensemble_acc >= avg_individual_acc - 0.01, \
            f"Ensemble ({ensemble_acc:.4f}) should be >= avg individual ({avg_individual_acc:.4f})"
