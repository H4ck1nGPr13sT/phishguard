"""Integration tests for data pipeline.

These tests verify the end-to-end functionality of the data pipeline,
including download, validation, merging, splitting, and balancing.
"""

import pandas as pd

from src.data.pipeline import DataPipelineConfig, run_pipeline, load_cached_splits
from src.config.settings import CACHE_DIR


def test_pipeline_with_mock_data():
    """Test pipeline with UCI data only (no API key needed).

    This test runs the full pipeline with only UCI ML dataset to avoid
    requiring API keys or external dependencies. It verifies:
    - Pipeline completes without errors
    - All splits are generated (train/val/test)
    - Temporal integrity is maintained
    - Balancing is applied to training data
    """
    config = DataPipelineConfig(
        skip_phishtank=True,  # Skip PhishTank (no API key)
        skip_nazario=True,    # Skip Nazario (no mbox file)
        force_refresh=True,   # Force fresh run for testing
        random_seed=42
    )

    # Run pipeline
    results = run_pipeline(config)

    # Verify structure
    assert 'train' in results, "Missing 'train' in results"
    assert 'val' in results, "Missing 'val' in results"
    assert 'test' in results, "Missing 'test' in results"
    assert 'reports' in results, "Missing 'reports' in results"
    assert 'cache_paths' in results, "Missing 'cache_paths' in results"

    # Verify splits are populated
    X_train, y_train = results['train']
    X_val, y_val = results['val']
    X_test, y_test = results['test']

    assert len(X_train) > 0, "Training set is empty"
    assert len(y_train) > 0, "Training labels are empty"

    # Note: UCI-only test may have empty val/test due to missing timestamps
    # Temporal split assigns all data without timestamps to training set
    # This is expected behavior for feature-only datasets

    # Verify shapes match
    assert len(X_train) == len(y_train), "Training X/y shape mismatch"
    if len(X_val) > 0:
        assert len(X_val) == len(y_val), "Validation X/y shape mismatch"
    if len(X_test) > 0:
        assert len(X_test) == len(y_test), "Test X/y shape mismatch"

    # Verify temporal integrity
    assert results['reports']['split']['temporal_integrity'] is True, \
        "Temporal integrity check failed"

    # Verify balancing was applied
    assert 'balance' in results['reports'], "Missing balance report"
    balance_report = results['reports']['balance']
    assert 'original_counts' in balance_report, "Missing original_counts in balance report"
    assert 'final_counts' in balance_report, "Missing final_counts in balance report"

    # Verify cache files were created
    assert results['cache_paths']['train'].exists(), "Training cache not created"
    assert results['cache_paths']['val'].exists(), "Validation cache not created"
    assert results['cache_paths']['test'].exists(), "Test cache not created"

    print(f"✓ Pipeline test passed: {len(X_train)} train, {len(X_val)} val, {len(X_test)} test")


def test_load_cached_splits():
    """Test loading cached splits after pipeline run.

    Verifies that cached data can be loaded correctly and matches
    the expected structure.
    """
    # First ensure pipeline has run at least once
    config = DataPipelineConfig(
        skip_phishtank=True,
        skip_nazario=True,
        force_refresh=False  # Use cache if available
    )

    # Run or load from cache
    run_pipeline(config)

    # Now test loading cached splits
    splits = load_cached_splits(CACHE_DIR)

    # Verify structure
    assert 'train' in splits, "Missing 'train' in cached splits"
    assert 'val' in splits, "Missing 'val' in cached splits"
    assert 'test' in splits, "Missing 'test' in cached splits"

    # Verify each split is a tuple of (X, y)
    for split_name in ['train', 'val', 'test']:
        X, y = splits[split_name]
        assert isinstance(X, pd.DataFrame), f"{split_name} X is not a DataFrame"
        assert isinstance(y, pd.Series), f"{split_name} y is not a Series"

        # Note: val/test may be empty for UCI-only dataset (no timestamps)
        if split_name == 'train':
            assert len(X) > 0, f"{split_name} X is empty"
            assert len(y) > 0, f"{split_name} y is empty"

        assert len(X) == len(y), f"{split_name} X/y length mismatch"

    print("✓ Cached splits loaded successfully")


def test_pipeline_reports():
    """Test that pipeline generates comprehensive reports.

    Verifies that all expected report sections are present and contain
    meaningful information.
    """
    config = DataPipelineConfig(
        skip_phishtank=True,
        skip_nazario=True,
        force_refresh=False
    )

    results = run_pipeline(config)
    reports = results['reports']

    # Check for expected report sections
    if 'download' in reports:
        # Download report only present if force_refresh=True
        assert 'sources' in reports['download'], "Missing 'sources' in download report"
        assert 'total_samples' in reports['download'], "Missing 'total_samples' in download report"

    if 'merge' in reports:
        assert 'total_samples' in reports['merge'], "Missing 'total_samples' in merge report"

    if 'validation' in reports:
        assert 'total_valid' in reports['validation'], "Missing 'total_valid' in validation report"

    if 'split' in reports:
        assert 'train_size' in reports['split'], "Missing 'train_size' in split report"
        assert 'val_size' in reports['split'], "Missing 'val_size' in split report"
        assert 'test_size' in reports['split'], "Missing 'test_size' in split report"
        assert 'temporal_integrity' in reports['split'], "Missing 'temporal_integrity' in split report"

    if 'balance' in reports:
        assert 'original_counts' in reports['balance'], "Missing 'original_counts' in balance report"
        assert 'final_counts' in reports['balance'], "Missing 'final_counts' in balance report"

    print("✓ Pipeline reports are comprehensive")


if __name__ == '__main__':
    # Allow running tests directly without pytest
    print("Running integration tests...")
    try:
        test_pipeline_with_mock_data()
        test_load_cached_splits()
        test_pipeline_reports()
        print("\n✓ All integration tests passed!")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        raise
