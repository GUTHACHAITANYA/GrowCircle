"""
Google Cloud Speech-to-Text and Text-to-Speech REST adapters.
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

GOOGLE_STT_URL = "https://speech.googleapis.com/v1/speech:recognize"
GOOGLE_TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"


class GoogleSTTAdapter(SpeechToTextProvider):
    """
    Google Cloud Speech-to-Text V1 REST adapter.
    """

    def __init__(self) -> None:
        self.api_key = settings.GOOGLE_SPEECH_API_KEY

    async def transcribe(
        self, audio_bytes: bytes, language: str | None = None
    ) -> TranscriptionResult:
        if not self.api_key:
            raise ValueError("Google Speech API key unconfigured.")

        lang_map = {"te": "te-IN", "hi": "hi-IN", "gu": "gu-IN", "en": "en-IN"}
        lang_code = lang_map.get(language or "te", "te-IN")

        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        payload = {
            "config": {
                "encoding": "LINEAR16",
                "sampleRateHertz": 8000,
                "languageCode": lang_code,
            },
            "audio": {"content": audio_b64},
        }

        url = f"{GOOGLE_STT_URL}?key={self.api_key}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            res_data = resp.json()

        results = res_data.get("results", [])
        transcript = ""
        confidence = 0.90
        if results and "alternatives" in results[0] and results[0]["alternatives"]:
            alt = results[0]["alternatives"][0]
            transcript = alt.get("transcript", "")
            confidence = alt.get("confidence", 0.90)

        return TranscriptionResult(
            text=transcript,
            detected_language=language or "te",
            confidence=confidence,
            provider="google",
        )


class GoogleTTSAdapter(TextToSpeechProvider):
    """
    Google Cloud Text-to-Speech REST adapter.
    """

    def __init__(self) -> None:
        self.api_key = settings.GOOGLE_SPEECH_API_KEY

    async def synthesize(self, text: str, language: str = "te") -> AudioSynthesisResult:
        if not self.api_key:
            raise ValueError("Google Speech API key unconfigured.")

        lang_map = {"te": "te-IN", "hi": "hi-IN", "gu": "gu-IN", "en": "en-IN"}
        lang_code = lang_map.get(language, "te-IN")

        payload = {
            "input": {"text": text},
            "voice": {"languageCode": lang_code, "ssmlGender": "FEMALE"},
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 8000},
        }

        url = f"{GOOGLE_TTS_URL}?key={self.api_key}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            res_data = resp.json()

        audio_b64 = res_data.get("audioContent", "")
        audio_bytes = base64.b64decode(audio_b64)
        word_count = max(1, len(text.split()))

        return AudioSynthesisResult(
            audio_bytes=audio_bytes,
            format="wav",
            duration_seconds=round(word_count * 0.45, 2),
            provider="google",
        )
