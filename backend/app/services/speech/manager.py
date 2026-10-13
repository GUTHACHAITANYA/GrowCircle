"""
Speech Manager: Orchestrates STT/TTS providers with graceful fallbacks,
audio caching per crop/district/date, and intent/entity extraction.
"""

import logging
from datetime import UTC, datetime

from backend.app.core.config import settings
from backend.app.services.speech.adapters.bhashini import (
    BhashiniSTTAdapter,
    BhashiniTTSAdapter,
)
from backend.app.services.speech.adapters.google_speech import (
    GoogleSTTAdapter,
    GoogleTTSAdapter,
)
from backend.app.services.speech.adapters.mock_speech import (
    MockSTTProvider,
    MockTTSProvider,
)
from backend.app.services.speech.adapters.sarvam import (
    SarvamSTTAdapter,
    SarvamTTSAdapter,
)
from backend.app.services.speech.base import (
    AudioSynthesisResult,
    SpeechToTextProvider,
    TextToSpeechProvider,
    TranscriptionResult,
)
from backend.app.services.speech.cache import AudioCache
from backend.app.services.speech.pronunciation import (
    PRERECORDED_PHRASES,
    build_mandi_prices_spoken_summary,
)

logger = logging.getLogger(__name__)


class SpeechManager:
    """
    Unified manager for speech processing, audio caching, and provider fallbacks.
    """

    def __init__(self) -> None:
        self.cache = AudioCache()
        self.mock_stt = MockSTTProvider()
        self.mock_tts = MockTTSProvider()

    def _get_stt_providers(self) -> list[SpeechToTextProvider]:
        configured = settings.STT_PROVIDER.lower().strip()
        providers: list[SpeechToTextProvider] = []

        if configured == "sarvam" and settings.SARVAM_API_KEY:
            providers.append(SarvamSTTAdapter())
        elif configured == "bhashini" and settings.BHASHINI_API_KEY:
            providers.append(BhashiniSTTAdapter())
        elif configured == "google" and settings.GOOGLE_SPEECH_API_KEY:
            providers.append(GoogleSTTAdapter())

        # Fallbacks: append other available providers then mock
        if settings.SARVAM_API_KEY and configured != "sarvam":
            providers.append(SarvamSTTAdapter())
        if settings.BHASHINI_API_KEY and configured != "bhashini":
            providers.append(BhashiniSTTAdapter())
        if settings.GOOGLE_SPEECH_API_KEY and configured != "google":
            providers.append(GoogleSTTAdapter())

        providers.append(self.mock_stt)
        return providers

    def _get_tts_providers(self) -> list[TextToSpeechProvider]:
        configured = settings.TTS_PROVIDER.lower().strip()
        providers: list[TextToSpeechProvider] = []

        if configured == "sarvam" and settings.SARVAM_API_KEY:
            providers.append(SarvamTTSAdapter())
        elif configured == "bhashini" and settings.BHASHINI_API_KEY:
            providers.append(BhashiniTTSAdapter())
        elif configured == "google" and settings.GOOGLE_SPEECH_API_KEY:
            providers.append(GoogleTTSAdapter())

        # Fallbacks
        if settings.SARVAM_API_KEY and configured != "sarvam":
            providers.append(SarvamTTSAdapter())
        if settings.BHASHINI_API_KEY and configured != "bhashini":
            providers.append(BhashiniTTSAdapter())
        if settings.GOOGLE_SPEECH_API_KEY and configured != "google":
            providers.append(GoogleTTSAdapter())

        providers.append(self.mock_tts)
        return providers

    async def transcribe(
        self, audio_bytes: bytes, language: str | None = None
    ) -> TranscriptionResult:
        """
        Attempts transcription via configured STT provider, falling back on failure.
        """
        providers = self._get_stt_providers()
        for provider in providers:
            try:
                return await provider.transcribe(audio_bytes, language=language)
            except Exception as ex:
                logger.warning(
                    "STT provider %s failed: %s. Trying next provider.",
                    provider.__class__.__name__,
                    ex,
                )

        # Guaranteed fallback
        return await self.mock_stt.transcribe(audio_bytes, language=language)

    async def synthesize(self, text: str, language: str = "te") -> AudioSynthesisResult:
        """
        Attempts synthesis via configured TTS provider, falling back on failure.
        """
        providers = self._get_tts_providers()

        for provider in providers:
            try:
                return await provider.synthesize(text, language=language)
            except Exception as ex:
                logger.warning(
                    "TTS provider %s failed: %s. Trying next provider.",
                    provider.__class__.__name__,
                    ex,
                )

        # Guaranteed fallback
        return await self.mock_tts.synthesize(text, language=language)

    async def get_or_synthesize_mandi_prices(
        self,
        mandis_data: list[dict],
        crop_id: str = "banana",
        district: str = "guntur",
        language: str = "te",
        unit: str = "kg",
        date_str: str | None = None,
    ) -> tuple[AudioSynthesisResult, str]:
        """
        Builds spoken text summary and retrieves or synthesizes audio,
        cached by crop + district + date + language + unit.
        """
        target_date = date_str or datetime.now(UTC).date().isoformat()

        # Check Cache first
        cached = self.cache.get(
            crop_id=crop_id,
            district=district,
            date_str=target_date,
            language=language,
            unit=unit,
        )
        text_summary = build_mandi_prices_spoken_summary(
            mandis_data=mandis_data,
            crop_id=crop_id,
            lang=language,
        )

        if cached:
            return cached, text_summary

        # Synthesize and store in cache
        result = await self.synthesize(text=text_summary, language=language)
        self.cache.set(
            crop_id=crop_id,
            district=district,
            date_str=target_date,
            language=language,
            result=result,
            unit=unit,
        )
        return result, text_summary

    async def get_prerecorded_phrase_audio(
        self, phrase_id: str, language: str = "te"
    ) -> AudioSynthesisResult:
        """
        Retrieves or synthesizes standard prerecorded phrase audio (e.g. welcome, menus).
        """
        cached = self.cache.get_prerecorded_phrase(phrase_id, language)
        if cached:
            return cached

        text = PRERECORDED_PHRASES.get(phrase_id, {}).get(
            language, PRERECORDED_PHRASES.get(phrase_id, {}).get("en", "")
        )
        result = await self.synthesize(text=text, language=language)
        self.cache.set_prerecorded_phrase(phrase_id, language, result)
        return result

    @staticmethod
    def extract_intent_and_entities(
        transcript: str,
    ) -> dict[str, str | None]:
        """
        Extracts crop, district, and intent from user transcription.
        Supports Telugu, Hindi, Gujarati, and English keywords.
        """
        t = transcript.lower()

        # Crop extraction
        crop_id = "banana"  # default
        if any(w in t for w in ["banana", "అరటి", "కేలా", "केला", "કેળા"]):
            crop_id = "banana"
        elif any(w in t for w in ["tomato", "టమాటా", "టమోటా", "टमाटर", "ટામેટા"]):
            crop_id = "tomato"
        elif any(w in t for w in ["onion", "ఉల్లి", "प्याज", "કાંદા", "ડુંગળી"]):
            crop_id = "onion"

        # District extraction
        district = None
        if any(w in t for w in ["guntur", "గుంటూరు", "गुंटूर", "ગુંટૂર"]):
            district = "guntur"
        elif any(w in t for w in ["vijayawada", "విజయవాడ", "विजयवाड़ा", "ntr"]):
            district = "ntr"
        elif any(w in t for w in ["tirupati", "తిరుపతి", "तिरुपति"]):
            district = "tirupati"
        elif any(w in t for w in ["kurnool", "కర్నూలు", "कर्नूल"]):
            district = "kurnool"

        # Intent extraction
        intent = "price_check"
        if any(w in t for w in ["sell", "అమ్మ", "बेचना", "વેચ"]):
            intent = "sell"
        elif any(w in t for w in ["transport", "driver", "రవాణా", "గాడి", "ट्रक", "વાહન"]):
            intent = "transport"

        return {"crop_id": crop_id, "district": district, "intent": intent}


speech_manager = SpeechManager()
