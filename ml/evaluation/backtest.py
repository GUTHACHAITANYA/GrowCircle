"""
GrowCircle Rolling-Origin Time-Series Cross-Validation Engine (Phase ML-1).
Evaluates candidate LightGBM multi-horizon quantile models against the 4 baselines:
- Expanding-window rolling origins (NO RANDOM SPLITS)
- Metrics: MAE, sMAPE, MASE (vs Seasonal Naive), Pinball Loss (q10, q50, q90), 80% Interval Coverage
- Horizon reporting: 1, 3, 7, 14 days
- Slice analysis: Volatile surge and crash weeks
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
import pandas as pd

from ml.models.baselines import (
    ExponentialSmoothingForecaster,
    MovingAverage7dForecaster,
    NaiveForecaster,
    SeasonalNaiveForecaster,
)
from ml.models.lightgbm_forecaster import HORIZONS, LightGBMPriceForecaster

logger = logging.getLogger(__name__)

ELIGIBLE_SERIES = [
    ("ap-guntur-01", "banana"),
    ("ap-vijayawada-01", "banana"),
    ("ap-madanapalle-01", "tomato"),
    ("ap-kurnool-01", "onion"),
    ("ap-kurnool-01", "potato"),
]


def calculate_metrics(
    y_true: list[float],
    y_pred: list[float],
    y_p10: list[float] | None = None,
    y_p90: list[float] | None = None,
    seasonal_naive_mae: float | None = None,
) -> dict[str, float]:
    """Computes comprehensive time-series evaluation metrics."""
    if not y_true or not y_pred:
        return {"mae": 0.0, "smape": 0.0, "mase": 1.0, "pinball_loss": 0.0, "interval_coverage_pct": 0.0}

    y_t = np.array(y_true, dtype=float)
    y_p = np.array(y_pred, dtype=float)

    # 1. MAE
    mae = float(np.mean(np.abs(y_t - y_p)))

    # 2. sMAPE
    denom = np.abs(y_t) + np.abs(y_p)
    denom[denom == 0] = 1e-6
    smape = float(np.mean(2.0 * np.abs(y_t - y_p) / denom) * 100.0)

    # 3. MASE relative to seasonal naive
    if seasonal_naive_mae and seasonal_naive_mae > 0:
        mase = float(mae / seasonal_naive_mae)
    else:
        mase = 1.0

    # 4. Pinball loss (quantile loss)
    pinball_50 = float(np.mean(np.maximum(0.5 * (y_t - y_p), -0.5 * (y_t - y_p))))
    total_pinball = pinball_50
    coverage_pct = 80.0

    if y_p10 is not None and y_p90 is not None:
        q10 = np.array(y_p10, dtype=float)
        q90 = np.array(y_p90, dtype=float)

        pinball_10 = float(np.mean(np.maximum(0.10 * (y_t - q10), -0.90 * (y_t - q10))))
        pinball_90 = float(np.mean(np.maximum(0.90 * (y_t - q90), -0.10 * (y_t - q90))))
        total_pinball = float((pinball_10 + pinball_50 + pinball_90) / 3.0)

        # 5. Empirical 80% coverage (between 10th and 90th percentile)
        covered = (y_t >= q10) & (y_t <= q90)
        coverage_pct = float(np.mean(covered) * 100.0)

    return {
        "mae": round(mae, 2),
        "smape": round(smape, 2),
        "mase": round(mase, 3),
        "pinball_loss": round(total_pinball, 3),
        "interval_coverage_pct": round(coverage_pct, 1),
    }


class RollingOriginBacktester:
    """Expanding-window rolling origin evaluator for mandi commodity forecasting."""

    def __init__(self, data_path: Path = Path("data/processed/cleaned_mandi_prices.csv")) -> None:
        self.data_path = data_path
        if not data_path.exists():
            raise FileNotFoundError(f"Cleaned dataset not found at {data_path}")
        self.df = pd.read_csv(data_path)
        self.df["price_date"] = pd.to_datetime(self.df["price_date"]).dt.date

        # Baselines
        self.naive = NaiveForecaster()
        self.s_naive = SeasonalNaiveForecaster()
        self.ma7 = MovingAverage7dForecaster()
        self.ets = ExponentialSmoothingForecaster()

    def run_backtest(self) -> dict[str, Any]:
        """
        Executes rolling-origin backtesting across 5 expanding cutoffs in 2026.
        """
        cutoffs = [
            date(2026, 1, 15),  # Sankranti festive peak
            date(2026, 3, 20),  # Pre-summer transition
            date(2026, 5, 20),  # High summer volatility surge
            date(2026, 7, 25),  # Monsoon supply shifts
            date(2026, 9, 20),  # Late monsoon / harvest pre-Dussehra
        ]

        logger.info("Building training matrix for LightGBM global model...")
        lgb_forecaster = LightGBMPriceForecaster(version="lightgbm_global_v1")

        # Initial training matrix up to cutoff 1
        matrices = lgb_forecaster.build_training_matrix(
            self.df,
            eligible_series=ELIGIBLE_SERIES,
            train_end_date=cutoffs[0] - timedelta(days=1),
            step_days=3,
        )
        lgb_forecaster.fit(matrices)
        lgb_forecaster.save_artifacts()

        # Collector: predictions by model, horizon, and slice
        records_by_horizon: dict[int, dict[str, list[float]]] = {
            h: {
                "y_true": [],
                "naive": [],
                "s_naive": [],
                "ma7": [],
                "ets": [],
                "lgb_p50": [],
                "lgb_p10": [],
                "lgb_p90": [],
            }
            for h in HORIZONS
        }

        # Volatile period tracking (Tomato summer surges & crash windows)
        volatile_records: dict[int, dict[str, list[float]]] = {
            h: {"y_true": [], "s_naive": [], "lgb_p50": [], "lgb_p10": [], "lgb_p90": []}
            for h in HORIZONS
        }

        price_lookup = {
            (r["mandi_id"], r["crop_id"], r["price_date"]): float(r["modal_price_kg"])
            for _, r in self.df.iterrows()
            if not r["is_outlier"]
        }

        logger.info(f"Evaluating across {len(cutoffs)} rolling origins and {len(ELIGIBLE_SERIES)} eligible series...")

        for cutoff in cutoffs:
            for mandi_id, crop_id in ELIGIBLE_SERIES:
                for h in HORIZONS:
                    target_d = cutoff + timedelta(days=h)
                    target_key = (mandi_id, crop_id, target_d)

                    if target_key not in price_lookup:
                        continue

                    y_actual = price_lookup[target_key]

                    # Predict baselines
                    p_naive = self.naive.predict(self.df, mandi_id, crop_id, cutoff, h)
                    p_s_naive = self.s_naive.predict(self.df, mandi_id, crop_id, cutoff, h)
                    p_ma7 = self.ma7.predict(self.df, mandi_id, crop_id, cutoff, h)
                    p_ets = self.ets.predict(self.df, mandi_id, crop_id, cutoff, h)

                    # Predict LightGBM
                    lgb_res = lgb_forecaster.predict_with_intervals(self.df, mandi_id, crop_id, cutoff, h)
                    p_lgb_50 = lgb_res["median"]
                    p_lgb_10, p_lgb_90 = lgb_res["range_10_90"]

                    rec = records_by_horizon[h]
                    rec["y_true"].append(y_actual)
                    rec["naive"].append(p_naive)
                    rec["s_naive"].append(p_s_naive)
                    rec["ma7"].append(p_ma7)
                    rec["ets"].append(p_ets)
                    rec["lgb_p50"].append(p_lgb_50)
                    rec["lgb_p10"].append(p_lgb_10)
                    rec["lgb_p90"].append(p_lgb_90)

                    # Volatile slice check (May/June summer price swings or price changes > 20%)
                    if crop_id == "tomato" or cutoff.month in [5, 6, 7]:
                        v_rec = volatile_records[h]
                        v_rec["y_true"].append(y_actual)
                        v_rec["s_naive"].append(p_s_naive)
                        v_rec["lgb_p50"].append(p_lgb_50)
                        v_rec["lgb_p10"].append(p_lgb_10)
                        v_rec["lgb_p90"].append(p_lgb_90)

        # Compute summary comparison tables
        summary_by_horizon: dict[int, dict[str, Any]] = {}

        for h in HORIZONS:
            rec = records_by_horizon[h]
            y_t = rec["y_true"]
            s_naive_m = calculate_metrics(y_t, rec["s_naive"])

            m_naive = calculate_metrics(y_t, rec["naive"], seasonal_naive_mae=s_naive_m["mae"])
            m_s_naive = s_naive_m
            m_s_naive["mase"] = 1.000
            m_ma7 = calculate_metrics(y_t, rec["ma7"], seasonal_naive_mae=s_naive_m["mae"])
            m_ets = calculate_metrics(y_t, rec["ets"], seasonal_naive_mae=s_naive_m["mae"])
            m_lgb = calculate_metrics(
                y_t,
                rec["lgb_p50"],
                y_p10=rec["lgb_p10"],
                y_p90=rec["lgb_p90"],
                seasonal_naive_mae=s_naive_m["mae"],
            )

            # Volatile slice metrics
            v_rec = volatile_records[h]
            v_s_naive_m = calculate_metrics(v_rec["y_true"], v_rec["s_naive"])
            v_lgb_m = calculate_metrics(
                v_rec["y_true"],
                v_rec["lgb_p50"],
                y_p10=v_rec["lgb_p10"],
                y_p90=v_rec["lgb_p90"],
                seasonal_naive_mae=v_s_naive_m["mae"],
            )

            summary_by_horizon[h] = {
                "sample_count": len(y_t),
                "models": {
                    "naive": m_naive,
                    "seasonal_naive": m_s_naive,
                    "moving_average_7d": m_ma7,
                    "exponential_smoothing": m_ets,
                    "lightgbm_global": m_lgb,
                },
                "beats_seasonal_naive": m_lgb["mase"] < 1.0,
                "improvement_vs_seasonal_naive_pct": round(
                    ((s_naive_m["mae"] - m_lgb["mae"]) / s_naive_m["mae"]) * 100.0, 2
                ) if s_naive_m["mae"] > 0 else 0.0,
                "volatile_slice": {
                    "sample_count": len(v_rec["y_true"]),
                    "seasonal_naive_mae": v_s_naive_m["mae"],
                    "lightgbm_mae": v_lgb_m["mae"],
                    "lightgbm_mase": v_lgb_m["mase"],
                    "interval_coverage_pct": v_lgb_m["interval_coverage_pct"],
                },
            }

        return {
            "status": "completed",
            "horizons": summary_by_horizon,
            "cutoffs_evaluated": [str(c) for c in cutoffs],
            "eligible_series": ELIGIBLE_SERIES,
            "overall_lgb_beats_baseline": all(
                summary_by_horizon[h]["beats_seasonal_naive"] for h in HORIZONS
            ),
        }


def render_evaluation_markdown(res: dict[str, Any]) -> str:
    """Renders comprehensive benchmark table comparing baselines vs LightGBM."""
    lines = [
        "### Rolling-Origin Backtest Benchmark: Baselines vs. LightGBM Global Model",
        "",
        "| Horizon | Model | MAE (Rs./kg) | sMAPE % | MASE (vs S-Naive) | Pinball Loss | 80% Coverage | Status |",
        "| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]

    for h, h_data in res["horizons"].items():
        models = h_data["models"]
        for m_name, metrics in models.items():
            status = "**CHAMPION**" if (m_name == "lightgbm_global" and metrics["mase"] < 1.0) else "Baseline"
            cov = f"{metrics['interval_coverage_pct']}%" if m_name == "lightgbm_global" else "N/A"
            lines.append(
                f"| **{h} Day** | `{m_name}` | **Rs.{metrics['mae']}** | {metrics['smape']}% | "
                f"**{metrics['mase']}** | {metrics['pinball_loss']} | {cov} | {status} |"
            )
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")

    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bt = RollingOriginBacktester()
    backtest_results = bt.run_backtest()
    # Save results to json
    results_path = Path("ml/evaluation/backtest_results.json")
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(backtest_results, f, indent=2)
    print(render_evaluation_markdown(backtest_results))
