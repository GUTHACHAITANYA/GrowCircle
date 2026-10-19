"""
GrowCircle LightGBM Global Multi-Horizon Forecaster with Quantiles (Phase ML-1).
Trains direct multi-horizon models (h in {1, 3, 7, 14} days) with quantile regressors
for 10th, 50th (median), and 90th percentiles to generate calibrated prediction intervals.
Uses the 27 point-in-time features from Phase ML-0.
"""

from __future__ import annotations

import logging
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import joblib
import lightgbm as lgb
import pandas as pd

from ml.features.feature_pipeline import FeatureEngineer

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path("ml/models/artifacts")
HORIZONS = [1, 3, 7, 14]
QUANTILES = [0.10, 0.50, 0.90]

CROP_TO_INT = {"banana": 0, "tomato": 1, "onion": 2, "potato": 3}
MANDI_TO_INT = {
    "ap-guntur-01": 0,
    "ap-madanapalle-01": 1,
    "ap-vijayawada-01": 2,
    "ap-kurnool-01": 3,
    "ap-anantapur-01": 4,
    "ap-tirupati-01": 5,
}

FEATURE_COLS = [
    "crop_cat",
    "mandi_cat",
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


class LightGBMPriceForecaster:
    """Direct multi-horizon quantile forecaster using LightGBM."""

    def __init__(self, version: str = "lightgbm_global_v1") -> None:
        self.version = version
        self.fe = FeatureEngineer()
        # Storage: models[horizon][quantile] -> lgb.Booster / LGBMRegressor
        self.models: dict[int, dict[float, lgb.LGBMRegressor]] = {}

    def extract_features_vector(
        self,
        history_df: pd.DataFrame,
        mandi_id: str,
        crop_id: str,
        as_of: date,
    ) -> pd.DataFrame:
        """Extracts and formats a single row feature vector for model input."""
        raw_feats = self.fe.compute_features(history_df, mandi_id, crop_id, as_of)
        raw_feats["crop_cat"] = CROP_TO_INT.get(crop_id, 0)
        raw_feats["mandi_cat"] = MANDI_TO_INT.get(mandi_id, 0)

        row = {col: raw_feats.get(col, 0.0) for col in FEATURE_COLS}
        return pd.DataFrame([row])

    def build_training_matrix(
        self,
        df: pd.DataFrame,
        eligible_series: list[tuple[str, str]],
        train_end_date: date,
        start_date: date = date(2024, 2, 1),
        step_days: int = 2,
    ) -> dict[int, tuple[pd.DataFrame, pd.Series]]:
        """
        Builds direct multi-horizon training datasets: X and y for each horizon h.
        Guarantees zero future leakage by generating features strictly point-in-time as_of t,
        and targets y_{t+h}.
        """
        df_clean = df[~df["is_outlier"]].copy() if "is_outlier" in df.columns else df.copy()
        df_clean["price_date"] = pd.to_datetime(df_clean["price_date"]).dt.date

        # Pre-index price dates for speed
        price_lookup: dict[tuple[str, str, date], float] = {
            (row["mandi_id"], row["crop_id"], row["price_date"]): float(row["modal_price_kg"])
            for _, row in df_clean.iterrows()
        }

        horizon_data: dict[int, list[dict[str, Any]]] = {h: [] for h in HORIZONS}

        for mandi_id, crop_id in eligible_series:
            cur = start_date
            while cur <= train_end_date:
                # Extract features as of cur (strictly using < cur)
                try:
                    f_row = self.fe.compute_features(df_clean, mandi_id, crop_id, cur)
                    f_row["crop_cat"] = CROP_TO_INT.get(crop_id, 0)
                    f_row["mandi_cat"] = MANDI_TO_INT.get(mandi_id, 0)

                    for h in HORIZONS:
                        target_d = cur + timedelta(days=h)
                        target_key = (mandi_id, crop_id, target_d)
                        if target_key in price_lookup:
                            rec = {col: f_row.get(col, 0.0) for col in FEATURE_COLS}
                            rec["target"] = price_lookup[target_key]
                            horizon_data[h].append(rec)
                except Exception as e:
                    logger.debug(f"Feature build step error: {e}")

                cur += timedelta(days=step_days)

        output: dict[int, tuple[pd.DataFrame, pd.Series]] = {}
        for h, recs in horizon_data.items():
            if recs:
                hdf = pd.DataFrame(recs)
                X = hdf[FEATURE_COLS]
                y = hdf["target"]
                output[h] = (X, y)
            else:
                output[h] = (pd.DataFrame(columns=FEATURE_COLS), pd.Series(dtype=float))

        return output

    def fit(
        self,
        training_matrices: dict[int, tuple[pd.DataFrame, pd.Series]],
    ) -> None:
        """
        Trains LightGBM quantile regressors for each horizon h and quantile q in {0.10, 0.50, 0.90}.
        """
        for h, (X, y) in training_matrices.items():
            if len(X) < 20:
                logger.warning(f"Insufficient training rows ({len(X)}) for horizon {h}d. Skipping.")
                continue

            self.models[h] = {}
            for q in QUANTILES:
                # Quantile loss objective
                reg = lgb.LGBMRegressor(
                    objective="quantile",
                    alpha=q,
                    n_estimators=120,
                    learning_rate=0.04,
                    num_leaves=18,
                    min_child_samples=12,
                    subsample=0.85,
                    colsample_bytree=0.85,
                    random_state=42,
                    verbosity=-1,
                )
                reg.fit(X, y)
                self.models[h][q] = reg
                logger.debug(f"Fitted LightGBM h={h}d q={q} with {len(X)} samples.")

    def predict_with_intervals(
        self,
        history_df: pd.DataFrame,
        mandi_id: str,
        crop_id: str,
        as_of: date,
        horizon_days: int,
    ) -> dict[str, Any]:
        """
        Generates calibrated quantile forecasts: median (p50) and [p10, p90] interval.
        Enforces monotonicity: p10 <= p50 <= p90.
        """
        # If model for horizon not trained, map to nearest available horizon
        available_horizons = sorted(self.models.keys())
        if not available_horizons:
            # Fallback
            from ml.models.baselines import NaiveForecaster
            last_p = NaiveForecaster().predict(history_df, mandi_id, crop_id, as_of, horizon_days)
            return {
                "median": last_p,
                "range_10_90": [round(last_p * 0.9, 2), round(last_p * 1.1, 2)],
                "model_version": "fallback_naive",
            }

        # Nearest horizon matching
        h_matched = min(available_horizons, key=lambda x: abs(x - horizon_days))
        h_models = self.models[h_matched]

        # Extract features
        X_vec = self.extract_features_vector(history_df, mandi_id, crop_id, as_of)

        p10 = float(h_models[0.10].predict(X_vec)[0])
        p50 = float(h_models[0.50].predict(X_vec)[0])
        p90 = float(h_models[0.90].predict(X_vec)[0])

        # Enforce quantile monotonicity
        p10 = max(1.0, round(p10, 2))
        p50 = max(p10, round(p50, 2))
        p90 = max(p50, round(p90, 2))

        return {
            "median": p50,
            "range_10_90": [p10, p90],
            "model_version": self.version,
            "horizon_trained": h_matched,
        }

    def save_artifacts(self, directory: Path = ARTIFACTS_DIR) -> None:
        """Serializes trained LightGBM models."""
        directory.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.models, directory / f"{self.version}.joblib")
        logger.info(f"Saved LightGBM models to {directory / self.version}.joblib")

    def load_artifacts(self, directory: Path = ARTIFACTS_DIR) -> bool:
        """Loads trained models from disk if present."""
        path = directory / f"{self.version}.joblib"
        if path.exists():
            try:
                self.models = joblib.load(path)
                return True
            except Exception as e:
                logger.warning(f"Error loading model artifacts: {e}")
        return False
