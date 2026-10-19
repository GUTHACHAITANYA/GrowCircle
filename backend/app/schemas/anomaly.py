"""
Pydantic Schemas for Anomaly Review Queue and Outage Monitoring (Phase ML-2).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AnomalyReviewItem(BaseModel):
    id: int = Field(..., examples=[1])
    entity_type: str = Field(..., examples=["price"])
    entity_id: str = Field(..., examples=["1042"])
    crop_id: str | None = Field(None, examples=["tomato"])
    mandi_id: str | None = Field(None, examples=["ap-madanapalle-01"])
    reason_code: str = Field(..., examples=["RULE_UNIT_ERROR"])
    severity: str = Field(..., examples=["CRITICAL"])
    status: str = Field(..., examples=["pending_review"])
    metrics_payload: dict[str, Any] = Field(default_factory=dict)
    auto_cleared_reason: str | None = Field(None)
    reviewed_by: int | None = Field(None, examples=[1])
    reviewed_at: datetime | None = Field(None)
    review_notes: str | None = Field(None, examples=["Verified clerical typo"])
    created_at: datetime
    updated_at: datetime


class AnomalyReviewActionRequest(BaseModel):
    action: Literal["approve", "reject"] = Field(..., examples=["approve"])
    notes: str | None = Field(None, examples=["Approved after manual phone check with mandi secretary."])
    admin_id: int | None = Field(1, examples=[1])


class AnomalyStatsResponse(BaseModel):
    total_pending: int = Field(..., examples=[12])
    total_approved: int = Field(..., examples=[45])
    total_rejected: int = Field(..., examples=[18])
    total_auto_cleared: int = Field(..., examples=[32])
    by_severity: dict[str, int] = Field(
        ...,
        examples=[{"CRITICAL": 5, "HIGH": 7, "MEDIUM": 12, "LOW": 8}],
    )
    by_entity_type: dict[str, int] = Field(
        ...,
        examples=[{"price": 10, "offer": 2, "deal": 0, "reporting_drop": 0}],
    )


class ReportingStatusResponse(BaseModel):
    target_date: str = Field(..., examples=["2026-10-13"])
    day_of_week: str = Field(..., examples=["Tuesday"])
    actual_reporting_mandis: int = Field(..., examples=[19])
    expected_reporting_mandis: float = Field(..., examples=[18.5])
    drop_ratio: float = Field(..., examples=[1.027])
    drop_zscore: float = Field(..., examples=[-0.25])
    status: str = Field(..., examples=["HEALTHY"])
    is_outage_alert: bool = Field(..., examples=[False])
    alert_message: str = Field(..., examples=["Reporting volume healthy (19 active vs expected 18.5)."])
