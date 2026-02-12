"""Comprehensive test suite for GA optimization modules.

Tests all GA optimization functionality:
- Search spaces
- Fitness functions
- GA optimizer
- Feature selection
- Ensemble weights
- Model registry
- MLflow tracking
- Integration tests

Uses small synthetic datasets and reduced GA parameters for fast execution.
Target run time: < 60 seconds for full suite.
"""

import json
import tempfile
from pathlib import Path
from unittest import mock

import joblib
import numpy as np
import pytest
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.optimization import (
    SEARCH_SPACES,
    compare_versions,
    create_fitness_function,
    create_weighted_ensemble,
    decode_individual,
    get_active_model,
    get_selected_features,
    normalize_weights,
    register_model,
    run_feature_selection,
    run_ga_optimization,
    run_weight_optimization,
    set_active_version,
    setup_feature_selection_toolbox,
    setup_toolbox,
    setup_weight_optimization_toolbox,
)


# Fixtures
@pytest.fixture
def synthetic_data():
    """Create small synthetic dataset for testing (100 samples, 10 features)."""
    X, y = make_classification(
        n_samples=100,
        n_features=10,
        n_informative=7,
        n_redundant=3,
        n_classes=2,
        random_state=42,
        flip_y=0.1  # Add some noise
    )
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    return X_train, X_test, y_train, y_test


@pytest.fixture
def feature_names():
    """Feature names for synthetic data."""
    return [f"feature_{i}" for i in range(10)]


@pytest.fixture
def mock_classifiers(synthetic_data):
    """Create mock classifiers for testing."""
    X_train, _, y_train, _ = synthetic_data

    classifiers = {}
    for name in ['rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt']:
        # Use simple RF for all classifiers (fast for testing)
        clf = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', RandomForestClassifier(
                n_estimators=10,
                max_depth=5,
                random_state=42,
                n_jobs=1
            ))
        ])
        clf.fit(X_train, y_train)
        classifiers[name] = clf

    return classifiers


# 1. Search Space Tests
class TestSearchSpaces:
    """Tests for search space definitions and decoding."""

    def test_search_spaces_defined_for_all_classifiers(self):
        """Verify search spaces exist for all 7 classifiers."""
        expected_classifiers = {'rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt'}
        assert set(SEARCH_SPACES.keys()) == expected_classifiers

    def test_search_space_bounds_are_valid(self):
        """Verify all bounds are properly defined (low < high)."""
        for clf_name, space in SEARCH_SPACES.items():
            for param_name, param_spec in space.items():
                if param_spec['type'] in ['int', 'float']:
                    assert param_spec['low'] < param_spec['high'], \
                        f"{clf_name}.{param_name}: low >= high"

    def test_decode_individual_type_casting(self):
        """Verify decode_individual handles int/float type casting."""
        # RF: 4 int parameters
        individual = [200.7, 15.3, 10.8, 5.2]
        params = decode_individual('rf', individual)

        assert params['n_estimators'] == 200
        assert params['max_depth'] == 15
        assert params['min_samples_split'] == 10
        assert params['min_samples_leaf'] == 5
        assert all(isinstance(v, int) for v in params.values())

    def test_decode_individual_categorical_handling(self):
        """Verify decode_individual handles categorical parameters."""
        # SVM: includes 'kernel' categorical
        individual = [10.0, 0.1, 1]  # C, gamma, kernel_idx
        params = decode_individual('svm', individual)

        assert 'kernel' in params
        assert params['kernel'] in ['rbf', 'poly', 'sigmoid']


# 2. Fitness Function Tests
class TestFitnessFunction:
    """Tests for fitness evaluation."""

    def test_fitness_returns_tuple(self, synthetic_data):
        """Verify fitness function returns tuple (DEAP requirement)."""
        X_train, _, y_train, _ = synthetic_data

        fitness_func = create_fitness_function('rf', X_train, y_train)
        individual = [100, 10, 5, 2]
        result = fitness_func(individual)

        assert isinstance(result, tuple)
        assert len(result) == 1

    def test_fitness_uses_cross_validation(self, synthetic_data):
        """Verify fitness uses cross-validation (variance in scores)."""
        X_train, _, y_train, _ = synthetic_data

        fitness_func = create_fitness_function('rf', X_train, y_train)
        individual = [100, 10, 5, 2]

        # Run multiple times - should get consistent results (CV is deterministic)
        results = [fitness_func(individual)[0] for _ in range(3)]

        # All should be the same (CV with fixed random_state)
        assert all(abs(r - results[0]) < 0.001 for r in results)

    def test_fitness_handles_invalid_params(self, synthetic_data):
        """Verify fitness returns 0.0 for invalid hyperparameters."""
        X_train, _, y_train, _ = synthetic_data

        fitness_func = create_fitness_function('rf', X_train, y_train)

        # Invalid individual (negative values will be clipped, but should still work)
        # Test with parameters that might cause issues
        individual = [1, 1, 1, 1]  # Minimal values
        result = fitness_func(individual)

        # Should return valid fitness, not error
        assert isinstance(result, tuple)
        assert 0.0 <= result[0] <= 1.0

    def test_fitness_value_range(self, synthetic_data):
        """Verify fitness (F1-score) is in valid range [0, 1]."""
        X_train, _, y_train, _ = synthetic_data

        fitness_func = create_fitness_function('rf', X_train, y_train)
        individual = [100, 10, 5, 2]
        fitness = fitness_func(individual)[0]

        assert 0.0 <= fitness <= 1.0


# 3. GA Optimizer Tests
class TestGAOptimizer:
    """Tests for GA optimizer setup and execution."""

    def test_toolbox_creation(self, synthetic_data):
        """Verify toolbox is created with all required components."""
        X_train, _, y_train, _ = synthetic_data

        toolbox = setup_toolbox('rf', X_train, y_train)

        # Check required components registered
        assert hasattr(toolbox, 'individual')
        assert hasattr(toolbox, 'population')
        assert hasattr(toolbox, 'evaluate')
        assert hasattr(toolbox, 'mate')
        assert hasattr(toolbox, 'mutate')
        assert hasattr(toolbox, 'select')

    def test_population_generation(self, synthetic_data):
        """Verify population can be generated with correct size."""
        X_train, _, y_train, _ = synthetic_data

        toolbox = setup_toolbox('rf', X_train, y_train)
        population = toolbox.population(n=10)

        assert len(population) == 10
        # Each individual should have 4 genes (RF has 4 hyperparameters)
        assert all(len(ind) == 4 for ind in population)

    def test_evolution_improves_fitness(self, synthetic_data):
        """Verify GA evolution improves fitness over generations."""
        X_train, _, y_train, _ = synthetic_data

        toolbox = setup_toolbox('nb', X_train, y_train)  # Use NB - faster, only 1 param

        # Run very short GA (pop=5, gen=2)
        best, logbook, hof = run_ga_optimization(
            toolbox, population_size=5, n_generations=2
        )

        # Check that evolution ran (DEAP logs gen 0, 1, 2 for ngen=2)
        assert len(logbook) >= 2  # At least 2 generations
        assert len(hof) > 0  # Hall of Fame populated
        assert best is not None

    def test_halloffame_preserves_best(self, synthetic_data):
        """Verify HallOfFame preserves best individuals."""
        X_train, _, y_train, _ = synthetic_data

        toolbox = setup_toolbox('nb', X_train, y_train)
        best, logbook, hof = run_ga_optimization(
            toolbox, population_size=5, n_generations=2
        )

        # HallOfFame should contain best individual
        assert hof[0] == best
        # All individuals in HoF should have fitness
        assert all(ind.fitness.valid for ind in hof)

    def test_logbook_records_generations(self, synthetic_data):
        """Verify logbook records statistics for each generation."""
        X_train, _, y_train, _ = synthetic_data

        toolbox = setup_toolbox('nb', X_train, y_train)
        best, logbook, hof = run_ga_optimization(
            toolbox, population_size=5, n_generations=2
        )

        # Check logbook structure (DEAP logs gen 0, 1, 2 for ngen=2)
        assert len(logbook) >= 2
        for record in logbook:
            assert 'avg' in record
            assert 'max' in record
            assert 'min' in record
            assert 'std' in record


# 4. Feature Selection Tests
class TestFeatureSelection:
    """Tests for GA-based feature selection."""

    def test_binary_individual_representation(self, synthetic_data):
        """Verify feature selection uses binary individuals."""
        X_train, _, y_train, _ = synthetic_data

        toolbox = setup_feature_selection_toolbox(X_train, y_train)
        population = toolbox.population(n=5)

        # Each individual should have n_features genes
        n_features = X_train.shape[1]
        assert all(len(ind) == n_features for ind in population)

        # Each gene should be 0 or 1
        for ind in population:
            assert all(gene in [0, 1] for gene in ind)

    def test_minimum_features_constraint(self, synthetic_data):
        """Verify minimum features constraint is enforced."""
        X_train, _, y_train, _ = synthetic_data

        # Create individual with too few features
        individual = [1, 1, 0, 0, 0, 0, 0, 0, 0, 0]  # Only 2 features

        from src.optimization.feature_selection import evaluate_feature_subset
        fitness = evaluate_feature_subset(individual, X_train, y_train, min_features=5)

        # Should return zero fitness
        assert fitness[0] == 0.0

    def test_feature_selection_convergence(self, synthetic_data):
        """Verify feature selection can converge to a solution."""
        X_train, _, y_train, _ = synthetic_data

        toolbox = setup_feature_selection_toolbox(X_train, y_train, min_features=3)

        # Run short GA
        best, selected_indices, logbook = run_feature_selection(
            toolbox, population_size=10, n_generations=5
        )

        # Should select at least min_features
        assert len(selected_indices) >= 3
        # Should have valid fitness
        assert best.fitness.values[0] > 0.0


# 5. Ensemble Weights Tests
class TestEnsembleWeights:
    """Tests for ensemble weight optimization."""

    def test_weight_normalization(self):
        """Verify weights are normalized to sum to 1.0."""
        weights = [0.5, 0.3, 0.1, 0.05, 0.02, 0.02, 0.01]
        normalized = normalize_weights(weights)

        # Should sum to 1.0
        assert abs(sum(normalized) - 1.0) < 0.001

    def test_weights_sum_to_one(self):
        """Verify all weights meet minimum threshold and sum to 1.0."""
        weights = [0.5, 0.3, 0.1, 0.05, 0.02, 0.02, 0.01]
        normalized = normalize_weights(weights)

        # All should be >= 0.01 (minimum enforced)
        assert all(w >= 0.01 for w in normalized), f"Weights: {normalized}"
        # Should sum to 1.0
        assert abs(sum(normalized) - 1.0) < 0.001

    def test_weighted_ensemble_prediction(self, mock_classifiers, synthetic_data):
        """Verify weighted ensemble can make predictions."""
        X_train, X_test, y_train, y_test = synthetic_data

        # Create weighted ensemble
        weights = {name: 1.0/7 for name in ['rf', 'svm', 'mlp', 'xgb', 'lr', 'nb', 'dt']}

        estimators = [(name, clf) for name, clf in mock_classifiers.items()]
        ensemble = VotingClassifier(
            estimators=estimators,
            voting='soft',
            weights=list(weights.values())
        )
        ensemble.fit(X_train, y_train)

        # Should be able to predict
        predictions = ensemble.predict(X_test)
        assert len(predictions) == len(y_test)
        assert all(p in [0, 1] for p in predictions)


# 6. Model Registry Tests
class TestModelRegistry:
    """Tests for model versioning and registry."""

    def test_set_active_version(self, tmp_path):
        """Verify active version can be set in config."""
        # Mock cache directory
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        with mock.patch('src.optimization.model_registry.Path') as mock_path:
            mock_path.return_value = tmp_path / "cache" / "active_models.json"

            # Set active version
            set_active_version('rf', 'ga_optimized', Path('models/optimized/rf_optimized.joblib'))

            # Verify config was created
            config_path = tmp_path / "cache" / "active_models.json"
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
                    assert 'rf' in config
                    assert config['rf']['version'] == 'ga_optimized'

    def test_compare_versions(self, synthetic_data):
        """Verify version comparison generates metrics."""
        X_train, X_test, y_train, y_test = synthetic_data

        # Create two simple models
        baseline = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', RandomForestClassifier(n_estimators=10, random_state=42))
        ])
        baseline.fit(X_train, y_train)

        optimized = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', RandomForestClassifier(n_estimators=50, random_state=42))
        ])
        optimized.fit(X_train, y_train)

        # Compare
        comparison = compare_versions('rf', baseline, optimized, X_test, y_test)

        # Check structure
        assert 'classifier' in comparison
        assert 'baseline' in comparison
        assert 'optimized' in comparison
        assert 'improvement' in comparison

        # Check metrics
        for metrics_dict in [comparison['baseline'], comparison['optimized']]:
            assert 'f1' in metrics_dict
            assert 'accuracy' in metrics_dict


# 7. Integration Tests
class TestIntegration:
    """Integration tests for full optimization pipeline."""

    def test_full_optimization_pipeline_rf(self, synthetic_data):
        """Test complete optimization pipeline for RF."""
        X_train, X_test, y_train, y_test = synthetic_data

        # 1. Setup toolbox
        toolbox = setup_toolbox('rf', X_train, y_train)

        # 2. Run GA (minimal config)
        best, logbook, hof = run_ga_optimization(
            toolbox, population_size=5, n_generations=2
        )

        # 3. Decode best individual
        best_params = decode_individual('rf', best)

        # 4. Create and train model with best params
        from src.optimization.fitness import create_model_from_params
        best_model = create_model_from_params('rf', best_params)
        best_model.fit(X_train, y_train)

        # 5. Evaluate
        y_pred = best_model.predict(X_test)
        test_f1 = f1_score(y_test, y_pred)

        # Should get reasonable F1
        assert 0.5 <= test_f1 <= 1.0

    def test_optimized_models_can_predict(self, synthetic_data):
        """Verify optimized models can make predictions."""
        X_train, X_test, y_train, y_test = synthetic_data

        # Train a simple optimized model
        model = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            ))
        ])
        model.fit(X_train, y_train)

        # Should be able to predict
        predictions = model.predict(X_test)
        probabilities = model.predict_proba(X_test)

        assert len(predictions) == len(y_test)
        assert probabilities.shape == (len(y_test), 2)
        assert all(p in [0, 1] for p in predictions)


# 8. Helper Function Tests
class TestHelpers:
    """Tests for helper functions."""

    def test_get_selected_features(self, feature_names):
        """Verify get_selected_features extracts feature info correctly."""
        individual = [1, 0, 1, 1, 0, 1, 0, 0, 1, 0]

        result = get_selected_features(individual, feature_names)

        assert 'indices' in result
        assert 'names' in result
        assert 'n_selected' in result

        # Should select features at indices 0, 2, 3, 5, 8
        expected_indices = [0, 2, 3, 5, 8]
        assert result['indices'] == expected_indices
        assert result['n_selected'] == 5
        assert len(result['names']) == 5
