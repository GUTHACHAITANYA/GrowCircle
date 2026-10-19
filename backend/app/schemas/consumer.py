"""
Pydantic schemas for Consumer features: multi-crop listings, seasonality, and price alerts.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CropOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name_en: str
    name_te: str
    name_hi: str
    name_gu: str
    icon: str | None
    category: str


class SeasonalityAnalysis(BaseModel):
    crop_id: str
    district: str
    current_modal_price_kg: float
    benchmark_price_kg: float
    percentage_difference: float
    is_expensive: bool
    status: str  # 'expensive' | 'fair' | 'cheap'
    plain_language_verdict: str
    seasonality_tip: str


class PriceAlertCreate(BaseModel):
    user_phone: str = Field(..., max_length=20, description="WhatsApp phone number or phone identifier")
    channel: str = Field("whatsapp", description="'whatsapp' or 'telegram'")
    telegram_chat_id: str | None = Field(None, description="Telegram handle or chat id")
    crop_id: str = Field(..., description="Crop slug, e.g. 'banana', 'tomato'")
    district: str = Field("Guntur", description="District for price notifications")
    alert_type: str = Field("below_price", description="'below_price', 'above_price', or 'weekly_digest'")
    target_price_kg: float | None = Field(None, gt=0, description="Threshold price per kg")


class PriceAlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_phone: str
    channel: str
    telegram_chat_id: str | None
    crop_id: str
    district: str
    alert_type: str
    target_price_kg: float | None
    is_active: bool
    created_at: datetime
