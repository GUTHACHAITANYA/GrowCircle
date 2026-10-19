"""
FastAPI Price Forecasting Endpoint (Phase ML-1).
Provides GET /forecast?mandi_id=..&crop=..&horizon=7
Returns point & calibrated interval forecasts with data sufficiency level,
model version, and plain-language guidance note.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ml.services.forecasting_service import forecast_service

logger = logging.getLogger(__name__)

router = APIRouter()


class ForecastResponse(BaseModel):
    crop_id: str = Field(..., examples=["banana"])
    mandi_id: str = Field(..., examples=["ap-guntur-01"])
    mandi_name: str = Field(..., examples=["Guntur"])
    horizon_days: int = Field(..., examples=[7])
    forecast_date: str = Field(..., examples=["2026-10-20"])
    as_of_date: str = Field(..., examples=["2026-10-13"])
    last_known_price_kg: float = Field(..., examples=[25.0])
    median_price_kg: float = Field(..., examples=[27.43])
    range_10_90_kg: list[float] = Field(..., examples=[[23.34, 28.12]])
    direction: str = Field(..., examples=["rise_slight"])
    user_messages: dict[str, str] = Field(
        ...,
        examples=[{
            "en": "Prices may rise slightly next week, uncertain.",
            "te": "ధరలు కొద్దిగా పెరిగే అవకాశం ఉంది, అనిశ్చితం.",
            "hi": "भाव में हल्की तेजी आ सकती है, अनिश्चित है।",
            "gu": "ભાવમાં થોડો વધારો થઈ શકે છે, અનિશ્ચિત છે.",
        }],
    )
    plain_note: str = Field(..., examples=["guidance only"])
    model_version: str = Field(..., examples=["lightgbm_global_v1"])
    model_used: str = Field(..., examples=["lightgbm_global_v1"])
    data_sufficiency_level: str = Field(..., examples=["mandi_ml"])
    beats_baseline: bool = Field(..., examples=[True])


@router.get("/forecast", response_model=ForecastResponse)
def get_price_forecast(
    mandi_id: str = Query(..., description="APMC Mandi identifier, e.g. 'ap-guntur-01'"),
    crop: str = Query(..., description="Crop identifier, e.g. 'banana', 'tomato', 'onion', 'potato'"),
    horizon: int = Query(7, ge=1, le=14, description="Forecast horizon in days (1, 3, 7, 14)"),
) -> dict[str, Any]:
    """
    Returns median, 10-90% range, model version, last data date, and plain-language guidance.
    If the series has insufficient history or does not beat baseline, gracefully returns baseline.
    """
    try:
        forecast = forecast_service.get_forecast(
            mandi_id=mandi_id,
            crop_id=crop,
            horizon_days=horizon,
        )
        return forecast
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Mandi price dataset not ready: {e}. Please ensure ML backfill has completed.",
        ) from e
    except Exception as e:
        logger.exception(f"Error generating forecast for {mandi_id} {crop}: {e}")
        raise HTTPException(status_code=500, detail=f"Forecast generation error: {e}") from e
