"""
GrowCircle ML Data Pipeline & MLOps Tests (Phase ML-0).
Tests:
- Cleaning pipeline (unit fixes, deduplication, variety normalisation, outlier flags)
- Data expectations suite (100% pass rate)
- Coverage analysis & modeling eligibility filter
- Dataset registry convention & DVC sidecar generation
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ml.data.cleaning import CleaningPipeline
from ml.data.coverage import analyze_mandi_crop_coverage
from ml.data.dataset_registry import DatasetRegistry
from ml.data.expectations import validate_processed_dataset


def test_cleaning_pipeline_unit_fixes_and_outliers() -> None:
    raw_sample = [
        {
            "mandi_id": "ap-guntur-01",
            "crop_id": "banana",
            "variety": "Amritapani",  # Alias to normalize
            "grade": "faq",
            "arrival_date": "2025-05-10",
            "min_price": 2000,
            "max_price": 2600,
            "modal_price": 2300,
            "arrival_tonnes": 45.0,
        },
        {
            # Duplicate record with slightly higher arrivals
            "mandi_id": "ap-guntur-01",
            "crop_id": "banana",
            "variety": "Amritapani",
            "grade": "faq",
            "arrival_date": "2025-05-10",
            "min_price": 2000,
            "max_price": 2600,
            "modal_price": 2300,
            "arrival_tonnes": 50.0,
        },
        {
            # Outlier record: min > max
            "mandi_id": "ap-guntur-01",
            "crop_id": "banana",
            "variety": "Amruthapani",
            "grade": "faq",
            "arrival_date": "2025-05-11",
            "min_price": 4000,
            "max_price": 2000,
            "modal_price": 3000,
            "arrival_tonnes": 20.0,
        },
    ]

    cleaned_df, metrics = CleaningPipeline.clean_records(raw_sample)

    assert metrics["raw_rows"] == 3
    assert metrics["duplicates_removed"] == 1
    assert metrics["varieties_normalized"] >= 1
    assert metrics["outliers_flagged"] == 1
    assert len(cleaned_df) == 2  # 3 raw - 1 duplicate = 2 rows kept

    # Unit fixes check: ₹/quintal -> ₹/kg
    first_row = cleaned_df[cleaned_df["price_date"] == pd.to_datetime("2025-05-10").date()].iloc[0]
    assert first_row["modal_price_kg"] == 23.0
    assert first_row["variety"] == "Amruthapani"  # Normalized
    assert not first_row["is_outlier"]

    # Outlier check: kept and flagged
    outlier_row = cleaned_df[cleaned_df["price_date"] == pd.to_datetime("2025-05-11").date()].iloc[0]
    assert outlier_row["is_outlier"]
    assert "min_greater_than_max" in outlier_row["outlier_reason"]


def test_expectations_suite_validation() -> None:
    csv_path = "data/processed/cleaned_mandi_prices.csv"
    assert Path(csv_path).exists(), "Run cleaning first to generate processed dataset."
    report = validate_processed_dataset(csv_path)
    assert report["overall_success"] is True
    assert report["success_rate_pct"] == 100.0


def test_coverage_analysis_honest_rejections() -> None:
    csv_path = "data/processed/cleaned_mandi_prices.csv"
    assert Path(csv_path).exists()
    df = pd.read_csv(csv_path)
    cov = analyze_mandi_crop_coverage(df)

    # Assert that primary hubs are flagged ELIGIBLE
    eligible_series = [c for c in cov if c["sufficient_for_modeling"]]
    eligible_crops = {c["crop_id"] for c in eligible_series}
    assert "banana" in eligible_crops
    assert "tomato" in eligible_crops
    assert "onion" in eligible_crops
    assert "potato" in eligible_crops

    # Assert that sparse mandis with extreme gaps are honestly DISQUALIFIED
    disqualified = [c for c in cov if not c["sufficient_for_modeling"]]
    disqualified_names = {(c["crop_id"], c["mandi_name"]) for c in disqualified}
    assert ("banana", "Anantapur") in disqualified_names
    assert ("potato", "Guntur") in disqualified_names


def test_dataset_registry_and_dvc_generation() -> None:
    csv_path = Path("data/processed/cleaned_mandi_prices.csv")
    assert csv_path.exists()
    reg = DatasetRegistry.register_dataset(data_path=csv_path)

    assert reg["name"] == "ap_mandi_prices_historical"
    assert reg["version"] == "1.0.0"
    assert reg["data_hash"].startswith("sha256:")
    assert reg["metrics"]["total_rows"] > 0
    assert reg["owner"] == "GrowCircle ML Team"

    dvc_file = Path("data/processed/cleaned_mandi_prices.csv.dvc")
    assert dvc_file.exists()
    dvc_content = dvc_file.read_text(encoding="utf-8")
    assert "sha256:" in dvc_content
    assert "total_rows:" in dvc_content
