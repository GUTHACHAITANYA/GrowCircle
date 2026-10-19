"""
Pydantic schemas for Computer Vision Quality and Fraud Inspection (Phase ML-4).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TimestampCheckSchema(BaseModel):
    passed: bool
    exif_timestamp: str | None = None
    server_timestamp: str
    age_hours: float | None = None
    flag: str | None = None


class LocationCheckSchema(BaseModel):
    passed: bool
    exif_lat: float | None = None
    exif_lon: float | None = None
    distance_km: float | None = None
    status: str


class DuplicateCheckSchema(BaseModel):
    is_duplicate: bool
    min_hamming_distance: int
    matched_listing_id: int | None = None
    details: str


class ScreenshotCheckSchema(BaseModel):
    is_screenshot: bool
    confidence: float
    reasons: list[str] = Field(default_factory=list)


class PhotoFraudReportSchema(BaseModel):
    is_suspicious: bool
    fraud_risk_score: float
    recommendation: str  # 'PASS', 'BUYER_VERIFY', 'FLAGGED_SUSPICIOUS'
    timestamp_check: TimestampCheckSchema
    location_check: LocationCheckSchema
    duplicate_check: DuplicateCheckSchema
    screenshot_check: ScreenshotCheckSchema
    perceptual_hashes: dict[str, str]


class QualityInspectionResponseSchema(BaseModel):
    crop_id: str
    suggested_grade: str = Field(..., description="'Grade_A', 'Grade_B', 'Grade_C', or 'uncertain'")
    confidence: float = Field(..., ge=0.0, le=1.0)
    buyer_decision_needed: bool
    buyer_guidance_note: str
    ripeness_stage: int
    ripeness_name: str
    detected_defects: list[str] = Field(default_factory=list)
    grade_probabilities: dict[str, float]
    human_rule_baseline_grade: str
    fraud_report: PhotoFraudReportSchema
    latency_ms: float
    fallback_triggered: bool = False
    policy_notice: str = Field(
        default="Suggestive only; the buyer retains final inspection and acceptance authority. Farmers are never auto-rejected.",
    )


class PhotoCollectionRequestSchema(BaseModel):
    farmer_id: int
    crop_id: str
    photo_type: str = Field(..., description="'whole_lot', 'close_up', or 'opened_crate'")
    consent_given: bool
    consent_language: str = Field(default="te", description="'en', 'te', 'hi', or 'gu'")
    device_model: str = Field(default="Android Mobile")
    lighting_condition: str = Field(default="diffused_shade")
    listing_id: int | None = None


class PhotoCollectionResponseSchema(BaseModel):
    status: str
    photo_id: str
    farmer_id: int
    crop_id: str
    photo_type: str
    file_path: str
    message: str
