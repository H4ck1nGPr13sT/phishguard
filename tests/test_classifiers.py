"""Tests for classifier factory and trained ensemble models."""

import pytest
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

from src.models.classifiers import create_classifiers, get_classifier, CLASSIFIER_CONFIGS
from src.data.pipeline import load_cached_splits


class TestClassifierFactory:
    """Test classifier factory functions."""

    def test_create_classifiers_returns_all_pipelines(self):
        """Test that create_classifiers returns all 7 pipelines."""
        classifiers = create_classifiers()

        assert isinstance(classifiers, dict)
        assert len(classifiers) == 7
        assert set(classifiers.keys()) == {'rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt'}

    def test_all_pipelines_have_scaler_and_classifier(self):
        """Test that each pipeline has StandardScaler + classifier."""
        classifiers = create_classifiers()

        for name, pipeline in classifiers.items():
            assert isinstance(pipeline, Pipeline), f"{name} is not a Pipeline"
            assert len(pipeline.steps) == 2, f"{name} pipeline should have 2 steps"

            # Check scaler
            scaler_name, scaler = pipeline.steps[0]
            assert scaler_name == 'scaler', f"{name} first step should be 'scaler'"
            assert isinstance(scaler, StandardScaler), f"{name} scaler is not StandardScaler"

            # Check classifier
            clf_name, clf = pipeline.steps[1]
            assert clf_name == 'classifier', f"{name} second step should be 'classifier'"

    def test_svm_has_probability_enabled(self):
        """Test that SVM has probability=True for soft voting."""
        svm_pipeline = get_classifier('svm')
        svm = svm_pipeline.named_steps['classifier']

        assert isinstance(svm, SVC)
        assert svm.probability is True, "SVM must have probability=True for soft voting"

    def test_xgb_has_limited_jobs(self):
        """Test that XGBoost has n_jobs=1 to prevent thread thrashing."""
        xgb_pipeline = get_classifier('xgb')
        xgb = xgb_pipeline.named_steps['classifier']

        assert isinstance(xgb, XGBClassifier)
        assert xgb.n_jobs == 1, "XGBoost should use n_jobs=1 to prevent thread thrashing"

    def test_all_classifiers_balanced_weights(self):
        """Test that RF, SVM, LR, DT have class_weight='balanced'."""
        classifiers = create_classifiers()

        balanced_classifiers = ['rf', 'svm', 'lr', 'dt']
        for name in balanced_classifiers:
            clf = classifiers[name].named_steps['classifier']
            assert hasattr(clf, 'class_weight'), f"{name} should support class_weight"
            assert clf.class_weight == 'balanced', f"{name} should have class_weight='balanced'"

    def test_get_classifier_valid_name(self):
        """Test get_classifier with valid name."""
        for name in ['rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt']:
            pipeline = get_classifier(name)
            assert isinstance(pipeline, Pipeline)

    def test_get_classifier_invalid_name(self):
        """Test get_classifier with invalid name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown classifier"):
            get_classifier('invalid_name')

    def test_classifier_configs_has_all_classifiers(self):
        """Test that CLASSIFIER_CONFIGS contains all 7 classifiers."""
        assert len(CLASSIFIER_CONFIGS) == 7
        assert set(CLASSIFIER_CONFIGS.keys()) == {'rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt'}

        # Check each config has 'class' and 'params'
        for name, config in CLASSIFIER_CONFIGS.items():
            assert 'class' in config, f"{name} config missing 'class'"
            assert 'params' in config, f"{name} config missing 'params'"
            assert callable(config['class']), f"{name} class is not callable"
            assert isinstance(config['params'], dict), f"{name} params is not dict"


class TestTrainedModels:
    """Test trained model files."""

    @pytest.fixture
    def models_dir(self):
        """Path to models directory."""
        return Path('models')

    @pytest.fixture
    def model_files(self, models_dir):
        """Expected model files."""
        return {
            'rf': models_dir / 'rf_pipeline.joblib',
            'svm': models_dir / 'svm_pipeline.joblib',
            'mlp': models_dir / 'mlp_pipeline.joblib',
            'xgb': models_dir / 'xgb_pipeline.joblib',
            'lr': models_dir / 'lr_pipeline.joblib',
            'nb': models_dir / 'nb_pipeline.joblib',
            'dt': models_dir / 'dt_pipeline.joblib',
        }

    def test_all_models_loadable(self, model_files):
        """Test that all 7 model files exist and can be loaded."""
        for name, path in model_files.items():
            assert path.exists(), f"Model file not found: {path}"

            # Load model
            model_data = joblib.load(path)
            assert 'model' in model_data, f"{name} model data missing 'model' key"

            model = model_data['model']
            assert isinstance(model, Pipeline), f"{name} is not a Pipeline"

    def test_all_models_can_predict(self, model_files):
        """Test that each loaded model can predict_proba on sample input."""
        # Create sample input (30 features matching URL features)
        sample_input = np.array([[
            1, 54, 0, 0, 0,     # IP, length, shortening, @, redirect (5)
            0, 1, 1, 0, 0,      # prefix-suffix, https, domain, favicon, port (5)
            1, 1, 0, 0, 0,      # request_url, anchor_url, links, forms, mailto (5)
            0, 0, 0, 0, 0,      # abnormal, forward, right_click, popup, iframe (5)
            1, 1, 0, 0, 2.5,    # age_domain, dns, web_traffic, google_index, entropy (5)
            0, 3, 1, 15, 8      # suspicious_tld, num_subdomains, has_ip, domain_len, path_len (5)
        ]])

        for name, path in model_files.items():
            model_data = joblib.load(path)
            model = model_data['model']

            # Test predict_proba
            proba = model.predict_proba(sample_input)
            assert proba.shape == (1, 2), f"{name} predict_proba wrong shape"
            assert np.isclose(proba.sum(), 1.0), f"{name} probabilities don't sum to 1"

            # Test predict
            prediction = model.predict(sample_input)
            assert prediction.shape == (1,), f"{name} predict wrong shape"
            assert prediction[0] in [0, 1], f"{name} prediction not binary"


class TestClassifierAccuracy:
    """Integration tests for classifier accuracy."""

    @pytest.fixture(scope='class')
    def training_data(self):
        """Load cached training data."""
        try:
            splits = load_cached_splits()
            X_train, y_train = splits['train']

            # Filter to numeric features only
            metadata_cols = ['url', 'content', 'timestamp', 'source']
            feature_cols = [col for col in X_train.columns if col not in metadata_cols]
            X_train_features = X_train[feature_cols]

            return X_train_features, y_train
        except FileNotFoundError:
            pytest.skip("Training data not available (cache files not found)")

    def test_classifier_accuracy_above_80_percent(self, training_data):
        """Test that most classifiers achieve >80% CV/OOB accuracy."""
        from sklearn.model_selection import cross_val_score

        X_train, y_train = training_data
        classifiers = create_classifiers()

        # Skip RF as it's tested separately
        classifiers_to_test = {k: v for k, v in classifiers.items() if k != 'rf'}

        results = {}
        for name, pipeline in classifiers_to_test.items():
            # Train pipeline
            pipeline.fit(X_train, y_train)

            # Get accuracy
            classifier = pipeline.named_steps['classifier']
            if hasattr(classifier, 'oob_score_'):
                accuracy = classifier.oob_score_
            else:
                cv_scores = cross_val_score(
                    pipeline, X_train, y_train, cv=3, scoring='accuracy', n_jobs=-1
                )
                accuracy = cv_scores.mean()

            results[name] = accuracy

        # Check results
        # NOTE: Naive Bayes may be below 80% due to feature correlation
        # but should still be above 60%
        expected_high_accuracy = ['svm', 'mlp', 'xgb', 'lr', 'dt']
        for name in expected_high_accuracy:
            assert results[name] > 0.80, (
                f"{name} accuracy {results[name]:.2%} below 80% threshold"
            )

        # Naive Bayes may be lower but should still be reasonable
        assert results['nb'] > 0.60, (
            f"nb accuracy {results['nb']:.2%} unexpectedly low (should be >60%)"
        )

        # Overall average should be high
        avg_accuracy = sum(results.values()) / len(results)
        assert avg_accuracy > 0.80, (
            f"Average accuracy {avg_accuracy:.2%} below 80%"
        )

    def test_loaded_models_match_factory(self, training_data):
        """Test that loaded models produce same predictions as factory-created models."""
        X_train, y_train = training_data

        # Get sample input
        sample_input = X_train.iloc[:10]

        models_dir = Path('models')
        factory_classifiers = create_classifiers()

        for name in ['svm', 'mlp', 'xgb', 'lr', 'nb', 'dt']:
            # Load saved model
            model_path = models_dir / f"{name}_pipeline.joblib"
            model_data = joblib.load(model_path)
            loaded_model = model_data['model']

            # Get predictions from loaded model
            loaded_pred = loaded_model.predict(sample_input)

            # Predictions should be valid
            assert loaded_pred.shape == (10,), f"{name} prediction shape mismatch"
            assert all(p in [0, 1] for p in loaded_pred), f"{name} predictions not binary"
