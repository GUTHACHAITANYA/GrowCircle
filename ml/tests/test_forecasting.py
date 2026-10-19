"""
GrowCircle ML-1 Price Forecasting Test Suite.
Tests:
1. Baseline models (Naive, Seasonal Naive, 7d MA, Exponential Smoothing)
2. LightGBM multi-horizon quantile model (monotonicity: p10 <= p50 <= p90)
3. Time-series evaluation metrics calculation (MAE, sMAPE, MASE, pinball loss, coverage)
4. Forecasting service fallback hierarchy (mandi_ml -> proxy_hub_ml -> seasonal_naive_baseline)
5. Plain-language direction messages in 4 languages (en, te, hi, gu) with "guidance only"
6. FastAPI GET /forecast endpoint integration
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from ml.evaluation.backtest import calculate_metrics
from ml.models.baselines import (
    ExponentialSmoothingForecaster,
    MovingAverage7dForecaster,
    NaiveForecaster,
    SeasonalNaiveForecaster,
)
from ml.models.lightgbm_forecaster import LightGBMPriceForecaster
from ml.services.forecasting_service import ForecastingService

client = TestClient(app)


@pytest.fixture
def clean_prices_df() -> pd.DataFrame:
    path = Path("data/processed/cleaned_mandi_prices.csv")
    assert path.exists(), "Processed dataset must exist."
    df = pd.read_csv(path)
    df["price_date"] = pd.to_datetime(df["price_date"]).dt.date
    return df


def test_baseline_forecasters_produce_valid_estimates(clean_prices_df: pd.DataFrame) -> None:
    mandi_id = "ap-guntur-01"
    crop_id = "banana"
    as_of = date(2026, 10, 1)

    naive = NaiveForecaster()
    s_naive = SeasonalNaiveForecaster()
    ma7 = MovingAverage7dForecaster()
    ets = ExponentialSmoothingForecaster()

    p_naive = naive.predict(clean_prices_df, mandi_id, crop_id, as_of, horizon_days=7)
    p_s_naive = s_naive.predict(clean_prices_df, mandi_id, crop_id, as_of, horizon_days=7)
    p_ma7 = ma7.predict(clean_prices_df, mandi_id, crop_id, as_of, horizon_days=7)
    p_ets = ets.predict(clean_prices_df, mandi_id, crop_id, as_of, horizon_days=7)

    for val in [p_naive, p_s_naive, p_ma7, p_ets]:
        assert isinstance(val, float)
        assert 5.0 <= val <= 100.0


def test_lightgbm_quantile_monotonicity(clean_prices_df: pd.DataFrame) -> None:
    lgb_forecaster = LightGBMPriceForecaster()
    # Load or fit
    if not lgb_forecaster.load_artifacts():
        matrices = lgb_forecaster.build_training_matrix(
            clean_prices_df,
            eligible_series=[("ap-guntur-01", "banana")],
            train_end_date=date(2025, 12, 31),
            step_days=7,
        )
        lgb_forecaster.fit(matrices)

    res = lgb_forecaster.predict_with_intervals(
        clean_prices_df, "ap-guntur-01", "banana", as_of=date(2026, 9, 1), horizon_days=7
    )

    median = res["median"]
    p10, p90 = res["range_10_90"]

    assert p10 <= median, f"Quantile violation: p10 ({p10}) > median ({median})"
    assert median <= p90, f"Quantile violation: median ({median}) > p90 ({p90})"
    assert median > 0.0


def test_calculate_metrics_correctness() -> None:
    y_true = [20.0, 25.0, 30.0, 35.0]
    y_pred = [22.0, 24.0, 28.0, 33.0]
    y_p10 = [18.0, 22.0, 26.0, 30.0]
    y_p90 = [25.0, 28.0, 32.0, 38.0]

    metrics = calculate_metrics(y_true, y_pred, y_p10=y_p10, y_p90=y_p90, seasonal_naive_mae=3.0)

    assert metrics["mae"] == 1.75
    assert metrics["mase"] == round(1.75 / 3.0, 3)
    assert metrics["smape"] > 0.0
    assert metrics["pinball_loss"] > 0.0
    assert metrics["interval_coverage_pct"] == 100.0


def test_forecasting_service_eligible_series() -> None:
    service = ForecastingService()
    forecast = service.get_forecast("ap-guntur-01", "banana", horizon_days=7)

    assert forecast["mandi_id"] == "ap-guntur-01"
    assert forecast["crop_id"] == "banana"
    assert forecast["data_sufficiency_level"] == "mandi_ml"
    assert forecast["beats_baseline"] is True
    assert forecast["plain_note"] == "guidance only"
    assert len(forecast["range_10_90_kg"]) == 2
    assert forecast["range_10_90_kg"][0] <= forecast["median_price_kg"] <= forecast["range_10_90_kg"][1]

    # Multilingual messages present
    msgs = forecast["user_messages"]
    for lang in ["en", "te", "hi", "gu"]:
        assert lang in msgs
        assert len(msgs[lang]) > 0
        assert "uncertain" in msgs["en"].lower() or "cautious" in msgs["en"].lower()


def test_forecasting_service_sparse_mandi_fallback() -> None:
    service = ForecastingService()
    # Tirupati Tomato is sparse -> falls back to Madanapalle proxy hub
    forecast = service.get_forecast("ap-tirupati-01", "tomato", horizon_days=7)

    assert forecast["mandi_id"] == "ap-tirupati-01"
    assert forecast["crop_id"] == "tomato"
    assert forecast["data_sufficiency_level"] == "proxy_hub_ml"
    assert "madanapalle" in forecast["model_used"]
    assert "guidance only" in forecast["plain_note"]
    assert forecast["median_price_kg"] > 0.0


def test_get_forecast_endpoint_integration() -> None:
    response = client.get("/forecast?mandi_id=ap-guntur-01&crop=banana&horizon=7")
    assert response.status_code == 200

    data = response.json()
    assert data["mandi_id"] == "ap-guntur-01"
    assert data["crop_id"] == "banana"
    assert data["horizon_days"] == 7
    assert data["plain_note"] == "guidance only"
    assert data["median_price_kg"] > 0.0
    assert data["range_10_90_kg"][0] <= data["range_10_90_kg"][1]
    assert data["data_sufficiency_level"] in ["mandi_ml", "proxy_hub_ml", "seasonal_naive_baseline"]


def test_get_forecast_endpoint_horizons() -> None:
    for h in [1, 3, 7, 14]:
        resp = client.get(f"/forecast?mandi_id=ap-madanapalle-01&crop=tomato&horizon={h}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["horizon_days"] == h
        assert data["median_price_kg"] > 0.0
