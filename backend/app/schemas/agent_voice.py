"""
Pydantic schemas for GrowCircle Voice and Chat Agent API.
Phase ML-6: Natural Speech Voice and Chat Agent.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User spoken transcript or chat message")
    session_id: str | None = Field(default=None, description="Dialogue session ID (auto-generated if omitted)")
    user_id: str | int = Field(default=1, description="Authenticated or anonymous caller ID")
    language: str | None = Field(default=None, description="Preferred language code: 'te', 'hi', 'gu', 'en', or None (auto-detect)")


class ChatResponse(BaseModel):
    session_id: str
    reply_text: str
    language: str
    intent: str
    tool_called: str | None
    citations: list[str] = Field(default_factory=list)
    consequential_action_pending: bool = False
    grounding_check: dict[str, Any]
    turn_count: int


class VoiceAudioRequest(BaseModel):
    transcript_hint: str | None = Field(default=None, description="STT transcript hint or direct transcription")
    audio_base64: str | None = Field(default=None, description="Base64 encoded audio bytes (WAV/MP3/Opus)")
    session_id: str | None = Field(default=None, description="Telephony or WhatsApp session ID")
    user_id: str | int = Field(default=1)
    language: str = Field(default="te", description="Spoken language: 'te', 'hi', 'gu', 'en'")


class VoiceAudioResponse(BaseModel):
    session_id: str
    reply_text: str
    language: str
    audio_url: str | None = None
    intent: str
    consequential_action_pending: bool = False
    latency_ms: float


class ConfirmActionRequest(BaseModel):
    session_id: str = Field(..., description="Active session ID with pending action")
    confirm: bool = Field(..., description="True to confirm and execute, False to cancel")
    user_id: str | int = Field(default=1)


class ConsentVoiceRecordingRequest(BaseModel):
    user_id: str | int = Field(..., description="User ID granting consent")
    consent_granted: bool = Field(default=True, description="Statutory DPDP consent flag")
    consent_purpose: str = Field(default="voice_model_improvement", description="DPDP statutory processing purpose")
    preferred_language: str = Field(default="te")
