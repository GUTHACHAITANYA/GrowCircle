"""
Pydantic schemas for Farm Diary, economic analytics, voice read-back, and exports.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class FarmSeasonCreate(BaseModel):
    season_name: str = Field(..., max_length=100, description="e.g. Kharif Banana 2026")
    crop_id: str = Field(..., description="Crop identifier, e.g. 'banana'")
    area_acres: float = Field(..., gt=0, description="Cultivated land area in acres")
    soil_type: str | None = Field(None, description="e.g. Black cotton, Red loamy")
    planting_date: date = Field(..., description="Date of planting or transplantation")
    harvest_date: date | None = Field(None, description="Expected or actual harvest date")
    expected_yield_kg: float = Field(0.0, ge=0, description="Estimated total harvest in kg")
    district: str = Field("Guntur", description="Farm location district")


class FarmSeasonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    farmer_id: int
    season_name: str
    crop_id: str
    area_acres: float
    soil_type: str | None
    planting_date: date
    harvest_date: date | None
    expected_yield_kg: float
    district: str
    created_at: datetime


class FarmDiaryEntryCreate(BaseModel):
    entry_type: str = Field(..., description="'cost', 'yield_log', or 'sale_revenue'")
    category: str = Field(
        ...,
        description="'seeds', 'fertilizer', 'labour', 'irrigation', 'machinery', 'transport', 'sale', or 'other'",
    )
    amount_inr: float = Field(0.0, ge=0, description="Expense or revenue amount in INR")
    quantity_kg: float = Field(0.0, ge=0, description="Harvested or sold quantity in kg")
    unit_price_inr: float = Field(0.0, ge=0, description="Price per kg if sale revenue")
    entry_date: date = Field(default_factory=date.today, description="Date of expenditure or event")
    notes: str | None = Field(None, max_length=500, description="Optional notes or merchant details")
    voice_raw_text: str | None = Field(None, description="Original voice transcription if voice entry")
    readback_confirmed: bool = Field(True, description="Whether entry was verified via read-back")


class FarmDiaryEntryVoiceInput(BaseModel):
    voice_audio_base64: str | None = Field(None, description="Raw audio data")
    voice_transcript_text: str = Field(
        ..., description="Spoken input text, e.g. 'Spent 8000 on labour for weeding yesterday'"
    )
    entry_date: date = Field(default_factory=date.today)


class VoiceConfirmationReadBack(BaseModel):
    transcription: str
    parsed_entry: FarmDiaryEntryCreate
    readback_text_en: str
    readback_text_te: str
    readback_text_hi: str
    readback_text_gu: str
    confirmation_token: str


class FarmDiaryEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    season_id: int
    entry_type: str
    category: str
    amount_inr: float
    quantity_kg: float
    unit_price_inr: float
    entry_date: date
    notes: str | None
    voice_raw_text: str | None
    readback_confirmed: bool
    created_at: datetime


class MandiComparison(BaseModel):
    farmer_actual_price_per_kg: float
    mandi_average_price_per_kg: float
    price_premium_inr: float
    price_premium_percent: float
    comparison_summary: str


class SeasonFinancialMetrics(BaseModel):
    season_id: int
    season_name: str
    crop_id: str
    area_acres: float
    total_cost_inr: float
    cost_breakdown: dict[str, float]
    total_yield_kg: float
    total_revenue_inr: float
    total_sold_kg: float
    net_profit_loss_inr: float
    profit_loss_per_acre_inr: float
    break_even_price_per_kg: float
    mandi_comparison: MandiComparison
