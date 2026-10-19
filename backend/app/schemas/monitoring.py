"""
Pydantic schemas for ML-7 Post-Launch Monitoring, Drift Detection, and Safe Releases.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReportWrongAnswerRequest(BaseModel):
    user_id: str | int = Field(default=1, description="Caller / user ID reporting incorrect response")
    channel: str = Field(default="ivr", description="Reporting channel: ivr, whatsapp, web")
    category: str = Field(
        default="price_error",
        description="Error category: price_error, forecast_error, vision_error, agent_voice_error, logistics_error",
    )
    query_text: str = Field(..., description="Original user prompt / question")
    model_response: str = Field(..., description="The response that user flagged as incorrect")
    farmer_correction: str | None = Field(default=None, description="Optional user correction or ground truth")


class ReviewFeedbackRequest(BaseModel):
    action: str = Field(..., description="'promote_to_eval' or 'dismiss'")
    reviewer_notes: str | None = Field(default=None, description="Notes from reviewing engineer/agronomist")


class DeployReleaseRequest(BaseModel):
    candidate_version: str = Field(..., description="Target model candidate version (e.g. v1.1-canary)")
    mode: str = Field(default="canary", description="'shadow' or 'canary'")
    canary_percentage: int = Field(default=10, ge=1, le=50, description="Percentage of traffic if canary mode")
    data_hash: str | None = Field(default=None, description="SHA-256 hash of training dataset")


class RollbackRequest(BaseModel):
    reason: str = Field(default="Manual operator rollback", description="Reason for triggering rollback to baseline")


class AcknowledgeAlertRequest(BaseModel):
    alert_id: str = Field(..., description="ID of alert to mark acknowledged")


class RecordCallCostRequest(BaseModel):
    duration_seconds: float = Field(default=60.0)
    stt_audio_seconds: float = Field(default=15.0)
    tts_audio_seconds: float = Field(default=30.0)
    llm_prompt_tokens: int = Field(default=250)
    llm_completion_tokens: int = Field(default=100)
