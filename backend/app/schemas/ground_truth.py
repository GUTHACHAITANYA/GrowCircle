"""
Pydantic schemas for ground-truth phone checks and validation reports.
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GroundTruthCheckCreate(BaseModel):
    mandi_id: int
    crop_id: str = "banana"
    variety: str = "Other"
    grade: str = "FAQ"
    check_date: date
    price_shown_kg: float | None = None
    price_quoted_kg: float = Field(..., gt=0, description="Price quoted via phone in ₹ / kg")
    contact_name: str | None = None
    contact_role: str = "secretary"  # 'secretary', 'commission_agent', 'trader', 'farmer'
    contact_phone: str | None = None
    notes: str | None = None


class GroundTruthCheckOut(BaseModel):
    id: int
    mandi_id: int
    mandi_name: str
    crop_id: str
    variety: str
    grade: str
    check_date: date
    price_shown_kg: float | None
    price_quoted_kg: float
    difference_kg: float | None
    difference_pct: float | None
    is_price_missing: bool
    is_price_late: bool
    contact_name: str | None
    contact_role: str
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MandiAccuracyMetric(BaseModel):
    mandi_name: str
    checks_count: int
    avg_diff_pct: float
    missing_count: int
    late_count: int


class GroundTruthReportOut(BaseModel):
    total_checks: int
    avg_diff_kg: float
    avg_diff_pct: float
    missing_price_count: int
    missing_price_rate_pct: float
    late_price_count: int
    late_price_rate_pct: float
    verified_match_rate_pct: float  # Percentage of checks within ±5%
    mandi_breakdown: list[MandiAccuracyMetric]
