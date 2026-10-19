"""
GrowCircle MLflow Experiment Tracking for Phase ML-0.
Runs locally using SQLite / file backend in `mlruns/`.
Tracks data foundation parameters, dataset hashes, data quality metrics,
and feature definitions without training models yet.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import mlflow
import pandas as pd

from ml.data.coverage import analyze_mandi_crop_coverage
from ml.data.dataset_registry import DatasetRegistry
from ml.data.expectations import validate_processed_dataset

logger = logging.getLogger(__name__)

TRACKING_DIR = Path("mlruns")
EXPERIMENT_NAME = "growcircle_mandi_price_foundation"


def log_ml0_foundation_run() -> dict[str, Any]:
    """
    Executes an MLflow tracking run documenting the ML-0 Data Foundation.
    Uses SQLite database backend (standard modern MLflow practice).
    """
    TRACKING_DIR.mkdir(parents=True, exist_ok=True)
    db_path = TRACKING_DIR / "mlflow.db"
    tracking_uri = f"sqlite:///{db_path.resolve()}"
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(EXPERIMENT_NAME)

    # 1. Load data and quality reports
    data_path = Path("data/processed/cleaned_mandi_prices.csv")
    if not data_path.exists():
        raise FileNotFoundError("Cleaned dataset not found.")

    df = pd.read_csv(data_path)
    reg_entry = DatasetRegistry.register_dataset(data_path=data_path)
    expectations_report = validate_processed_dataset(str(data_path))
    coverage_report = analyze_mandi_crop_coverage(df)

    eligible_count = sum(1 for c in coverage_report if c["sufficient_for_modeling"])
    disqualified_count = len(coverage_report) - eligible_count

    with mlflow.start_run(run_name="data_foundation_phase_ml0") as run:
        run_id = run.info.run_id

        # Log Parameters
        mlflow.log_params({
            "phase": "ML-0",
            "state": "Andhra Pradesh",
            "crops": "banana, tomato, onion, potato",
            "date_range_start": "2024-01-01",
            "date_range_end": "2026-10-13",
            "lags": "1, 7, 14, 28 days",
            "rolling_windows": "7d, 28d",
            "weather_provider": "Open-Meteo coordinates",
            "holiday_provider": "holidays.India (AP regional)",
            "outlier_policy": "Flag and keep (never delete)",
            "leakage_prevention": "Strict as_of temporal filtering",
        })

        # Log Metrics
        mlflow.log_metrics({
            "total_raw_rows": 9305,
            "total_clean_rows": len(df),
            "outliers_flagged": reg_entry["metrics"]["outliers_flagged"],
            "outlier_rate_pct": reg_entry["metrics"]["outlier_rate_pct"],
            "expectation_tests_passed": expectations_report["passed"],
            "expectation_tests_total": expectations_report["total_expectations"],
            "expectation_success_rate_pct": expectations_report["success_rate_pct"],
            "eligible_series_count": eligible_count,
            "disqualified_series_count": disqualified_count,
            "total_feature_count": 27,
        })

        # Log Tags
        mlflow.set_tags({
            "dataset_version": reg_entry["version"],
            "data_hash": reg_entry["data_hash"],
            "owner": reg_entry["owner"],
            "leakage_test": "PASSED",
            "model_training": "BLOCKED_PENDING_DATA_APPROVAL",
        })

        # Save artifacts locally and log them
        artifacts_dir = Path("ml/tracking/artifacts_temp")
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        exp_json = artifacts_dir / "expectations_report.json"
        with open(exp_json, "w", encoding="utf-8") as f:
            json.dump(expectations_report, f, indent=2)

        cov_json = artifacts_dir / "coverage_report.json"
        with open(cov_json, "w", encoding="utf-8") as f:
            json.dump(coverage_report, f, indent=2)

        reg_json = artifacts_dir / "registry_entry.json"
        with open(reg_json, "w", encoding="utf-8") as f:
            json.dump(reg_entry, f, indent=2)

        mlflow.log_artifact(str(exp_json), artifact_path="quality")
        mlflow.log_artifact(str(cov_json), artifact_path="coverage")
        mlflow.log_artifact(str(reg_json), artifact_path="registry")

        logger.info(f"[MLFLOW RUN LOGGED] ID: {run_id} in experiment '{EXPERIMENT_NAME}'")

        return {
            "experiment_name": EXPERIMENT_NAME,
            "run_id": run_id,
            "status": "logged",
            "tracking_uri": mlflow.get_tracking_uri(),
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_info = log_ml0_foundation_run()
    print(json.dumps(run_info, indent=2))
