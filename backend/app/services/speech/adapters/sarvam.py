"""
Sarvam AI STT and TTS adapters for Indian regional languages.
Docs: https://docs.sarvam.ai
"""

import base64
import logging

import httpx

from backend.app.core.config import settings
from backend.app.services.speech.base import (
    AudioSynthesisResult,
    SpeechToTextProvider,
    TextToSpeechProvider,
    TranscriptionResult,
)

logger = logging.getLogger(__name__)

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"


class SarvamSTTAdapter(SpeechToTextProvider):
    """
    Sarvam AI Saaras model STT adapter.
    """

    def __init__(self) -> None:
        self.api_key = settings.SARVAM_API_KEY

    async def transcribe(
        self, audio_bytes: bytes, language: str | None = None
    ) -> TranscriptionResult:
        if not self.api_key:
            raise ValueError("Sarvam AI API key unconfigured.")

        lang_code = f"{language}-IN" if language else "te-IN"
        headers = {"api-subscription-key": self.api_key}

        files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
        data = {"model": "saaras:v1", "language_code": lang_code}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(SARVAM_STT_URL, headers=headers, files=files, data=data)
            resp.raise_for_status()
            res_data = resp.json()

        transcript = res_data.get("transcript", "")
        return TranscriptionResult(
            text=transcript,
            detected_language=language or "te",
            confidence=0.95,
            provider="sarvam",
        )


class SarvamTTSAdapter(TextToSpeechProvider):
    """
    Sarvam AI Bulbul model TTS adapter.
    """

    def __init__(self) -> None:
        self.api_key = settings.SARVAM_API_KEY

    async def synthesize(self, text: str, language: str = "te") -> AudioSynthesisResult:
        if not self.api_key:
            raise ValueError("Sarvam AI API key unconfigured.")

        lang_code = f"{language}-IN"
        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": [text],
            "target_language_code": lang_code,
            "speaker": "meera",
            "model": "bulbul:v1",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(SARVAM_TTS_URL, headers=headers, json=payload)
            resp.raise_for_status()
            res_data = resp.json()

        audio_b64 = res_data.get("audios", [""])[0]
        audio_bytes = base64.b64decode(audio_b64)
        word_count = max(1, len(text.split()))

        return AudioSynthesisResult(
            audio_bytes=audio_bytes,
            format="wav",
            duration_seconds=round(word_count * 0.45, 2),
            provider="sarvam",
        )
