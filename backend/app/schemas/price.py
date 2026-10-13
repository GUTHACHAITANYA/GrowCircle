"""
Pydantic v2 schemas for Price, Mandi, and Health endpoints.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PriceOut(BaseModel):
    mandi_id: int
    mandi_name: str
    district: str
    state: str
    crop_id: str
    crop_name_en: str
    variety: str
    grade: str
    price_date: date
    min_price_kg: float
    max_price_kg: float
    modal_price_kg: float
    min_price_quintal: float
    max_price_quintal: float
    modal_price_quintal: float
    modal_price_ton: float
    arrival_tonnes: float
    source: str
    last_updated: datetime
    is_stale: bool

    model_config = ConfigDict(from_attributes=True)


class NearbyMandiOut(BaseModel):
    mandi_id: int
    mandi_name: str
    district: str
    state: str
    latitude: float | None
    longitude: float | None
    distance_km: float
    crop_id: str
    variety: str
    modal_price_kg: float
    modal_price_quintal: float
    price_date: str
    arrival_tonnes: float
    is_stale: bool = False


class HistoryPoint(BaseModel):
    date: str
    modal_price_kg: float
    modal_price_quintal: float
    arrival_tonnes: float


class HistoryResponse(BaseModel):
    mandi_id: int
    mandi_name: str
    crop_id: str
    days: int
    history: list[HistoryPoint]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    database: str
    last_successful_fetch_time: str | None
    is_stale_alert: bool
    alert_message: str | None
