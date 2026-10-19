"""
Pydantic schemas for Crop Planning & Crash Risk Guidance (Phase ML-3).
Outputs candidate crops ranked by expected profit per acre with downside risk ranges.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CropPlanCandidateSchema(BaseModel):
    crop_id: str = Field(..., description="Crop identifier, e.g. 'banana', 'tomato', 'onion'")
    crop_name_en: str = Field(..., description="English crop name")
    category: str = Field(..., description="Crop agronomic category, e.g. 'Fruit / Perennial', 'Vegetable'")
    duration_months: int = Field(..., description="Crop cycle duration from planting to harvest in months")
    harvest_month: int = Field(..., ge=1, le=12, description="Calculated harvest month (1-12)")
    harvest_month_name: str = Field(..., description="Name of harvest month, e.g. 'November'")

    # Financial and production ranges [10th percentile, 50th percentile, 90th percentile]
    harvest_price_kg_range: list[float] = Field(
        ...,
        description="Expected harvest mandi modal price [downside p10, expected p50, upside p90] in Rs./kg",
        examples=[[12.5, 21.0, 32.0]],
    )
    yield_tonnes_acre_range: list[float] = Field(
        ...,
        description="Expected harvest yield [downside y10, expected y50, upside y90] in tonnes/acre",
        examples=[[8.0, 11.5, 14.0]],
    )
    cost_per_acre_range: list[float] = Field(
        ...,
        description="Cultivation cost range [efficient c10, median c50, peak c90] in Rs./acre",
        examples=[[42000.0, 52000.0, 64000.0]],
    )
    profit_per_acre_range: list[float] = Field(
        ...,
        description="Probabilistic net profit range [downside_10, expected_50, upside_90] in Rs./acre",
        examples=[[-12000.0, 189500.0, 384000.0]],
    )
    downside_profit_acre: float = Field(..., description="Pessimistic scenario profit in Rs./acre")
    expected_profit_acre: float = Field(..., description="Median scenario profit in Rs./acre")
    upside_profit_acre: float = Field(..., description="Optimistic scenario profit in Rs./acre")

    # Risk metrics
    crash_risk_score: int = Field(..., ge=0, le=100, description="Cobweb crowding / supply glut risk score (0-100)")
    crash_risk_level: str = Field(..., description="Risk tier: 'LOW', 'MEDIUM', 'HIGH', or 'SEVERE'")
    crowding_factor: float = Field(..., description="Cobweb supply crowding multiplier relative to historical baseline")

    rationale: str = Field(..., description="Concise rationale explaining profit outlook and downside risk factors")
    agronomic_source: str = Field(..., description="Verified agronomic source confirming district suitability")
    finance_source: str = Field(..., description="Verified scale-of-finance or diary source")
    price_source: str = Field(
        default="Agmarknet modal mandi prices (2024-2026 AP arrivals)",
        description="Source citation for harvest prices",
    )
    yield_source: str = Field(
        default="DES AP District Area & Yield Statistics (GODL licensed)",
        description="Source citation for yield norms",
    )
    cost_source: str = Field(
        default="SLBC AP Scale of Finance 2024-2026",
        description="Source citation for cultivation costs",
    )
    downside_source: str = Field(
        default="Agmarknet historical distress crash price during peak supply glut",
        description="Source citation for price-crash downside scenario",
    )
    unrealistic_warning: str | None = Field(
        default=None,
        description="Flag warning of unrealistic or peak-condition estimates",
    )
    recommended_varieties: list[str] = Field(default_factory=list, description="KVK recommended high-yield varieties")


class CropPlanResponseSchema(BaseModel):
    district: str = Field(..., description="Target Andhra Pradesh district, e.g. 'Guntur'")
    planting_month: int = Field(..., ge=1, le=12, description="Target planting month index (1-12)")
    planting_month_name: str = Field(..., description="Target planting month name, e.g. 'July'")
    farmer_id: int | None = Field(None, description="Farmer ID if personal diary was blended")
    data_sufficiency: str = Field(
        ...,
        description="'blended_farmer_diary' if personal logs used, otherwise 'regional_norms'",
    )
    ranked_candidates: list[CropPlanCandidateSchema] = Field(
        ...,
        description="3 to 5 agronomically suitable crops ranked by expected profit per acre",
    )
    plain_disclaimer: str = Field(
        ...,
        description="Mandatory disclaimer: guidance only; check with local agriculture officer or KVK",
    )
    voice_summary: dict[str, str] = Field(
        ...,
        description="Short spoken summaries (< 45s audio) in 'en', 'te', 'hi', and 'gu'",
    )
    sources_and_assumptions: list[str] = Field(
        ...,
        description="Authoritative sources (ANGRAU, KVK, SLBC, DES AP GODL license)",
    )
