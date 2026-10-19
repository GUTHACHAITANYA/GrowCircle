"""
GrowCircle Mandi Price Forecasting Baselines (Phase ML-1).
Implements the 4 mandatory benchmark models:
1. Naive (last value: y_hat = y_t)
2. Seasonal Naive (same day of week: y_hat = y_{t+h-7})
3. 7-Day Moving Average (mean of last 7 observed prices)
4. Exponential Smoothing (Holt-Winters level + trend)
These are the numbers candidate ML models must beat.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import date, timedelta

import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

logger = logging.getLogger(__name__)


class BaseForecaster(ABC):
    """Abstract forecaster interface."""

    @abstractmethod
    def predict(
        self,
        history_df: pd.DataFrame,
        mandi_id: str,
        crop_id: str,
        as_of: date,
        horizon_days: int,
    ) -> float:
        """Generates a point forecast for (mandi, crop) at as_of + horizon_days."""


class NaiveForecaster(BaseForecaster):
    """Naive persistence baseline: predicts last known modal price."""

    def predict(
        self,
        history_df: pd.DataFrame,
        mandi_id: str,
        crop_id: str,
        as_of: date,
        horizon_days: int = 1,  # noqa: ARG002
    ) -> float:
        df_clean = history_df[~history_df["is_outlier"]] if "is_outlier" in history_df.columns else history_df
        df_clean["price_date"] = pd.to_datetime(df_clean["price_date"]).dt.date

        past = df_clean[
            (df_clean["mandi_id"] == mandi_id)
            & (df_clean["crop_id"] == crop_id)
            & (df_clean["price_date"] < as_of)
        ].sort_values("price_date")

        if past.empty:
            return 25.0  # Fallback reasonable default
        return round(float(past.iloc[-1]["modal_price_kg"]), 2)


class SeasonalNaiveForecaster(BaseForecaster):
    """Seasonal Naive baseline: predicts price from 7 days prior to target date."""

    def predict(
        self,
        history_df: pd.DataFrame,
        mandi_id: str,
        crop_id: str,
        as_of: date,
        horizon_days: int,
    ) -> float:
        df_clean = history_df[~history_df["is_outlier"]] if "is_outlier" in history_df.columns else history_df
        df_clean["price_date"] = pd.to_datetime(df_clean["price_date"]).dt.date

        target_date = as_of + timedelta(days=horizon_days)
        seasonal_target = target_date - timedelta(days=7)

        past = df_clean[
            (df_clean["mandi_id"] == mandi_id)
            & (df_clean["crop_id"] == crop_id)
            & (df_clean["price_date"] < as_of)
        ].sort_values("price_date")

        if past.empty:
            return 25.0

        date_map = dict(zip(past["price_date"], past["modal_price_kg"], strict=False))

        # 1. Exact seasonal match
        if seasonal_target in date_map:
            return round(float(date_map[seasonal_target]), 2)

        # 2. Sunday or holiday fallback: check adjacent days
        for offset in [1, -1, 2, -2]:
            cand = seasonal_target + timedelta(days=offset)
            if cand in date_map and cand < as_of:
                return round(float(date_map[cand]), 2)

        # 3. Fallback to latest known price
        return round(float(past.iloc[-1]["modal_price_kg"]), 2)


class MovingAverage7dForecaster(BaseForecaster):
    """7-Day Moving Average baseline: mean of last 7 trading observations."""

    def predict(
        self,
        history_df: pd.DataFrame,
        mandi_id: str,
        crop_id: str,
        as_of: date,
        horizon_days: int = 1,  # noqa: ARG002
    ) -> float:
        df_clean = history_df[~history_df["is_outlier"]] if "is_outlier" in history_df.columns else history_df
        df_clean["price_date"] = pd.to_datetime(df_clean["price_date"]).dt.date

        past = df_clean[
            (df_clean["mandi_id"] == mandi_id)
            & (df_clean["crop_id"] == crop_id)
            & (df_clean["price_date"] < as_of)
        ].sort_values("price_date")

        if past.empty:
            return 25.0

        last_7 = past.tail(7)["modal_price_kg"]
        return round(float(last_7.mean()), 2)


class ExponentialSmoothingForecaster(BaseForecaster):
    """Holt-Winters Exponential Smoothing baseline with linear trend."""

    def predict(
        self,
        history_df: pd.DataFrame,
        mandi_id: str,
        crop_id: str,
        as_of: date,
        horizon_days: int,
    ) -> float:
        df_clean = history_df[~history_df["is_outlier"]] if "is_outlier" in history_df.columns else history_df
        df_clean["price_date"] = pd.to_datetime(df_clean["price_date"]).dt.date

        past = df_clean[
            (df_clean["mandi_id"] == mandi_id)
            & (df_clean["crop_id"] == crop_id)
            & (df_clean["price_date"] < as_of)
        ].sort_values("price_date")

        if len(past) < 14:
            # Fallback to naive if insufficient history
            return round(float(past.iloc[-1]["modal_price_kg"]), 2) if not past.empty else 25.0

        series = past["modal_price_kg"].values[-60:]  # Recent 60 trading days
        try:
            model = ExponentialSmoothing(series, trend="add", initialization_method="estimated")
            fit_res = model.fit(smoothing_level=0.4, smoothing_trend=0.1, optimized=False)
            forecast = fit_res.forecast(horizon_days)
            pred = float(forecast[-1])
            return round(max(1.0, pred), 2)
        except Exception:
            return round(float(series[-1]), 2)
