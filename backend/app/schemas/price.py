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
    reported_date: date
    age_label: str  # 'today', 'yesterday', 'N days ago'
    is_reported_today: bool
    min_price_kg: float
    max_price_kg: float
    modal_price_kg: float
    min_price_quintal: float
    max_price_quintal: float
    modal_price_quintal: float
    modal_price_ton: float
    original_unit: str = "quintal"
    original_modal_price: float = 0.0
    arrival_tonnes: float
    mandal: str | None = None
    canonical_name: str | None = None
    distance_km: float | None = None
    distance_label: str = "straight-line distance"
    sparkline_30d: list[float] = []
    source: str
    source_name: str
    fetched_at: datetime | None = None
    last_updated: datetime | None = None
    is_stale: bool
    provenance_text: str
    status_message: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PriceAggregateOut(BaseModel):
    state: str | None = None
    district: str | None = None
    mandal: str | None = None
    mandi: str | None = None
    crop: str
    variety: str | None = None
    reporting_mandis_count: int
    total_records: int
    median_modal_price_kg: float | None = None
    median_modal_price_quintal: float | None = None
    min_modal_price_kg: float | None = None
    max_modal_price_kg: float | None = None
    avg_arrival_tonnes: float = 0.0
    is_area_average_reliable: bool
    area_level: str  # 'state', 'district', 'mandal', 'all'
    area_name: str
    note: str
    mandal_has_mandi: bool = True
    mandal_status_message: str | None = None


class NearbyMandiOut(BaseModel):
    mandi_id: int
    mandi_name: str
    canonical_name: str | None = None
    district: str
    state: str
    mandal: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    distance_km: float
    distance_label: str = "straight-line distance"
    crop_id: str
    variety: str
    modal_price_kg: float
    modal_price_quintal: float
    price_date: str
    age_days: int = 0
    age_label: str = "Today"
    arrival_tonnes: float = 0.0
    arrivals_tonnes: float = 0.0
    is_stale: bool = False
    source_name: str = "Agmarknet"

    model_config = ConfigDict(from_attributes=True)


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
    reporting_drop_alert: bool = False
    reporting_mandis_count: int | None = None
