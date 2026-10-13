"""
Bhashini (National Language Translation Mission - MeitY) STT and TTS adapters.
Docs: https://bhashini.gov.in/ulca
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

BHASHINI_INFERENCE_URL = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"


class BhashiniSTTAdapter(SpeechToTextProvider):
    """
    MeitY Bhashini Speech-to-Text adapter for Indian Languages (te, hi, gu, en).
    """

    def __init__(self) -> None:
        self.user_id = settings.BHASHINI_USER_ID
        self.api_key = settings.BHASHINI_API_KEY
        self.pipeline_id = settings.BHASHINI_PIPELINE_ID

    async def transcribe(
        self, audio_bytes: bytes, language: str | None = None
    ) -> TranscriptionResult:
        if not self.api_key or not self.user_id:
            raise ValueError("Bhashini API credentials unconfigured.")

        lang = language or "te"
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        payload = {
            "pipelineTasks": [
                {
                    "taskType": "asr",
                    "config": {
                        "language": {"sourceLanguage": lang},
                        "serviceId": "bhashini/ai4bharat/conformer-multilingual-indo-aryan",
                        "audioFormat": "wav",
                    },
                }
            ],
            "inputData": {"audio": [{"audioContent": audio_b64}]},
        }

        headers = {
            "userID": self.user_id,
            "ulcaApiKey": self.api_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(BHASHINI_INFERENCE_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        transcript = data.get("pipelineResponse", [{}])[0].get("output", [{}])[0].get("source", "")

        return TranscriptionResult(
            text=transcript,
            detected_language=lang,
            confidence=0.92,
            provider="bhashini",
        )


class BhashiniTTSAdapter(TextToSpeechProvider):
    """
    MeitY Bhashini Text-to-Speech adapter for Indian Languages.
    """

    def __init__(self) -> None:
        self.user_id = settings.BHASHINI_USER_ID
        self.api_key = settings.BHASHINI_API_KEY

    async def synthesize(self, text: str, language: str = "te") -> AudioSynthesisResult:
        if not self.api_key or not self.user_id:
            raise ValueError("Bhashini API credentials unconfigured.")

        payload = {
            "pipelineTasks": [
                {
                    "taskType": "tts",
                    "config": {
                        "language": {"sourceLanguage": language},
                        "gender": "female",
                        "samplingRate": 8000,
                    },
                }
            ],
            "inputData": {"input": [{"source": text}]},
        }

        headers = {
            "userID": self.user_id,
            "ulcaApiKey": self.api_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(BHASHINI_INFERENCE_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        audio_b64 = (
            data.get("pipelineResponse", [{}])[0].get("audio", [{}])[0].get("audioContent", "")
        )
        audio_bytes = base64.b64decode(audio_b64)
        word_count = max(1, len(text.split()))

        return AudioSynthesisResult(
            audio_bytes=audio_bytes,
            format="wav",
            duration_seconds=round(word_count * 0.45, 2),
            provider="bhashini",
        )
