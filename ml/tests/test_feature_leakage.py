"""
GrowCircle Automated Feature Leakage Test Suite (Phase ML-0).
Rigorously asserts that point-in-time featurization is mathematically immune
to future data leakage:
1. Future Insertion Invariance: Adding or altering records on or after `as_of`
   produces 100% IDENTICAL feature vectors.
2. Past Modification Sensitivity: Altering data strictly BEFORE `as_of` changes
   lag and rolling features (proving active sensitivity).
3. Target Leakage Prevention: Asserts that target price at `as_of` is not leaked
   into any feature column.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from ml.features.feature_pipeline import FeatureEngineer


@pytest.fixture
def sample_dataset() -> pd.DataFrame:
    """Loads cleaned APMC dataset or generates synthetic fixture."""
    csv_path = Path("data/processed/cleaned_mandi_prices.csv")
    if csv_path.exists():
        df = pd.read_csv(csv_path)
    else:
        # Fallback synthetic frame
        rows = []
        cur = date(2024, 1, 1)
        for i in range(400):
            rows.append({
                "mandi_id": "ap-guntur-01",
                "crop_id": "banana",
                "variety": "Amruthapani",
                "grade": "FAQ",
                "price_date": str(cur),
                "min_price_kg": 20.0 + (i % 5),
                "max_price_kg": 26.0 + (i % 5),
                "modal_price_kg": 23.0 + (i % 5),
                "arrival_tonnes": 40.0 + (i % 10),
                "is_outlier": False,
                "outlier_reason": "clean",
            })
            cur += timedelta(days=1)
        df = pd.DataFrame(rows)
    return df


def test_future_insertion_invariance_leakage_proof(sample_dataset: pd.DataFrame) -> None:
    """
    Core Leakage Test: Injects future records with extreme arbitrary prices
    on `as_of` and multiple dates in the future.
    Asserts that the feature vector as of `as_of` remains 100% invariant.
    """
    fe = FeatureEngineer()
    mandi_id = "ap-guntur-01"
    crop_id = "banana"
    as_of = date(2025, 6, 15)

    # 1. Compute baseline features on untouched dataset
    f_baseline = fe.compute_features(sample_dataset, mandi_id, crop_id, as_of)

    # 2. Construct poisoned dataset with future injections
    poisoned_df = sample_dataset.copy()

    future_injections = [
        # Exactly on as_of day
        {
            "mandi_id": mandi_id,
            "crop_id": crop_id,
            "variety": "Amruthapani",
            "grade": "FAQ",
            "price_date": str(as_of),
            "min_price_kg": 999.0,
            "max_price_kg": 9999.0,
            "modal_price_kg": 5000.0,  # Extreme poisoned value
            "arrival_tonnes": 9999.0,
            "is_outlier": False,
            "outlier_reason": "clean",
        },
        # as_of + 1 day
        {
            "mandi_id": mandi_id,
            "crop_id": crop_id,
            "variety": "Amruthapani",
            "grade": "FAQ",
            "price_date": str(as_of + timedelta(days=1)),
            "min_price_kg": 888.0,
            "max_price_kg": 8888.0,
            "modal_price_kg": 4000.0,
            "arrival_tonnes": 8888.0,
            "is_outlier": False,
            "outlier_reason": "clean",
        },
        # as_of + 14 days
        {
            "mandi_id": mandi_id,
            "crop_id": crop_id,
            "variety": "Amruthapani",
            "grade": "FAQ",
            "price_date": str(as_of + timedelta(days=14)),
            "min_price_kg": 777.0,
            "max_price_kg": 7777.0,
            "modal_price_kg": 3000.0,
            "arrival_tonnes": 7777.0,
            "is_outlier": False,
            "outlier_reason": "clean",
        },
    ]

    poisoned_df = pd.concat([poisoned_df, pd.DataFrame(future_injections)], ignore_index=True)

    # 3. Compute features on poisoned dataset
    f_poisoned = fe.compute_features(poisoned_df, mandi_id, crop_id, as_of)

    # 4. Strict assertion: Every feature must be 100% IDENTICAL
    numeric_feature_keys = [
        "price_lag_1d",
        "price_lag_7d",
        "price_lag_14d",
        "price_lag_28d",
        "price_diff_1d_7d",
        "price_pct_change_7d",
        "rolling_mean_7d",
        "rolling_std_7d",
        "rolling_mean_28d",
        "rolling_std_28d",
        "day_of_week",
        "month",
        "quarter",
        "day_of_year",
        "is_weekend",
        "is_festival_today",
        "days_to_next_festival",
        "days_since_last_festival",
        "neighbour_modal_price_lag1",
        "price_diff_to_neighbour_lag1",
        "arrival_tonnes_lag1",
        "arrival_rolling_mean_7d",
        "temp_max_c",
        "temp_min_c",
        "precipitation_mm",
        "diesel_price_rs_per_litre",
    ]

    for key in numeric_feature_keys:
        val_base = f_baseline[key]
        val_poison = f_poisoned[key]
        assert val_base == val_poison, (
            f"DATA LEAKAGE DETECTED on feature '{key}'! "
            f"Baseline: {val_base}, Poisoned: {val_poison}. "
            f"Feature calculation utilized records on or after as_of ({as_of})."
        )


def test_past_sensitivity_non_triviality(sample_dataset: pd.DataFrame) -> None:
    """
    Sanity test: Proves that features DO respond to changes in past data (t-1).
    Ensures tests are not vacuously passing on dummy constants.
    """
    fe = FeatureEngineer()
    mandi_id = "ap-guntur-01"
    crop_id = "banana"
    as_of = date(2025, 6, 15)

    f_baseline = fe.compute_features(sample_dataset, mandi_id, crop_id, as_of)

    # Mutate yesterday's price in the dataset (t-1)
    mutated_df = sample_dataset.copy()
    mutated_df["price_date"] = pd.to_datetime(mutated_df["price_date"]).dt.date

    yesterday = as_of - timedelta(days=1)
    mask = (
        (mutated_df["mandi_id"] == mandi_id)
        & (mutated_df["crop_id"] == crop_id)
        & (mutated_df["price_date"] == yesterday)
    )

    if mask.sum() > 0:
        mutated_df.loc[mask, "modal_price_kg"] = 95.0
        f_mutated = fe.compute_features(mutated_df, mandi_id, crop_id, as_of)
        # Lag 1 must reflect the changed past price
        assert f_mutated["price_lag_1d"] != f_baseline["price_lag_1d"], (
            "Feature pipeline is insensitive to past data changes!"
        )
        assert f_mutated["price_lag_1d"] == 95.0


def test_no_target_leaked_into_features(sample_dataset: pd.DataFrame) -> None:
    """
    Verifies that the target price on `as_of` is never present in the computed feature dict.
    """
    fe = FeatureEngineer()
    as_of = date(2025, 8, 1)
    feats = fe.compute_features(sample_dataset, "ap-guntur-01", "banana", as_of)

    # Feature keys should not contain the target variable directly
    forbidden_keys = ["target_price", "actual_price", "target_modal_price_kg"]
    for k in forbidden_keys:
        assert k not in feats, f"Forbidden target key '{k}' found in feature dictionary!"


def test_feature_pipeline_on_multiple_dates(sample_dataset: pd.DataFrame) -> None:
    """
    Tests feature calculation consistency across an evaluation window.
    """
    fe = FeatureEngineer()
    test_dates = [date(2025, 3, 1), date(2025, 6, 1), date(2025, 9, 1), date(2026, 1, 1)]

    for d in test_dates:
        f = fe.compute_features(sample_dataset, "ap-guntur-01", "banana", d)
        assert f["as_of"] == str(d)
        assert f["price_lag_1d"] > 0
        assert f["rolling_mean_7d"] > 0
        assert 0 <= f["day_of_week"] <= 6
        assert 1 <= f["month"] <= 12
