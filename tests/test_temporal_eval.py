import os
import json
import pandas as pd
import pytest
from backend.train_pipeline import DATASET_FILE_PATH, METRICS_FILE_PATH


def test_temporal_dataset_chronological_ordering():
    """Validates that the generated training dataset is strictly sorted in chronological order."""
    assert os.path.exists(DATASET_FILE_PATH), f"Missing dataset file at {DATASET_FILE_PATH}"
    df = pd.read_csv(DATASET_FILE_PATH)
    assert len(df) >= 10000
    assert "timestamp" in df.columns

    # Verify timestamps are monotonically non-decreasing
    timestamps = pd.to_datetime(df["timestamp"])
    is_sorted = (timestamps.diff().dropna() >= pd.Timedelta(0)).all()
    assert is_sorted, "Dataset timestamps must be strictly non-decreasing to prevent temporal leakage!"


def test_temporal_metrics_and_scientific_evaluation():
    """Validates that Phase 2 temporal evaluation metrics exist and satisfy performance SLAs."""
    assert os.path.exists(METRICS_FILE_PATH), f"Missing metrics file at {METRICS_FILE_PATH}"
    with open(METRICS_FILE_PATH, "r") as f:
        metrics = json.load(f)

    assert metrics["evaluation_strategy"] == "Temporal Out-of-Time Split (70/15/15)"
    assert metrics["train_samples"] > 0
    assert metrics["val_samples"] > 0
    assert metrics["test_samples"] > 0

    lgbm = metrics["lightgbm_metrics"]
    rule = metrics["rule_based_baseline"]

    # Rigorous scientific assertions
    assert lgbm["roc_auc"] >= 0.95, f"ROC-AUC {lgbm['roc_auc']} below 0.95 threshold"
    assert lgbm["pr_auc"] >= 0.85, f"PR-AUC {lgbm['pr_auc']} below 0.85 threshold"
    assert lgbm["brier_score"] <= 0.10, f"Brier score {lgbm['brier_score']} exceeds 0.10 calibration limit"

    # Outperforming Rule-Based baseline
    assert lgbm["recall"] > rule["recall"], "LightGBM must achieve superior fraud recall compared to rule-based baseline"
    assert metrics["relative_improvements"]["recall_gain_pct"] > 0

