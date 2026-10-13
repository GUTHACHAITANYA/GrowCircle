"""
Tests for Speech Engine: Pronunciation, STT/TTS Providers, Caching, and Fallback.
"""

from pathlib import Path

import pytest

from backend.app.services.speech.adapters.mock_speech import (
    MockSTTProvider,
    MockTTSProvider,
    create_minimal_wav_bytes,
)
from backend.app.services.speech.base import AudioSynthesisResult
from backend.app.services.speech.cache import AudioCache
from backend.app.services.speech.manager import SpeechManager, speech_manager
from backend.app.services.speech.pronunciation import (
    build_mandi_prices_spoken_summary,
    format_price_spoken,
    get_crop_spoken_name,
    get_mandi_spoken_name,
)


def test_minimal_wav_generation_valid_riff_header() -> None:
    """Verifies that generated audio bytes have valid RIFF and WAVE headers."""
    audio = create_minimal_wav_bytes(duration_sec=1.5, sample_rate=8000)
    assert len(audio) > 44
    assert audio[:4] == b"RIFF"
    assert audio[8:12] == b"WAVE"
    assert audio[12:16] == b"fmt "
    assert audio[36:40] == b"data"


@pytest.mark.asyncio
async def test_mock_stt_transcription() -> None:
    """Verifies STT transcription across language hints."""
    stt = MockSTTProvider()
    wav_bytes = create_minimal_wav_bytes(duration_sec=2.0)

    res_te = await stt.transcribe(wav_bytes, language="te")
    assert res_te.detected_language == "te"
    assert "అరటిపండు" in res_te.text
    assert res_te.confidence >= 0.9

    res_hi = await stt.transcribe(wav_bytes, language="hi")
    assert res_hi.detected_language == "hi"
    assert "केले" in res_hi.text

    res_en = await stt.transcribe(wav_bytes, language="en")
    assert res_en.detected_language == "en"
    assert "banana" in res_en.text


@pytest.mark.asyncio
async def test_mock_tts_synthesis() -> None:
    """Verifies TTS synthesis duration and output format."""
    tts = MockTTSProvider()
    text = "గ్రో సర్కిల్ కు స్వాగతం. అరటిపండు ధర కిలో ఇరవై ఐదు రూపాయలు."
    result = await tts.synthesize(text, language="te")

    assert result.format == "wav"
    assert result.duration_seconds > 0.0
    assert result.duration_seconds < 60.0  # Must be under 1 minute
    assert result.audio_bytes.startswith(b"RIFF")


def test_pronunciation_dictionaries() -> None:
    """Verifies phonetic localization of crops and mandis."""
    assert get_crop_spoken_name("banana", "te") == "అరటిపండు"
    assert get_crop_spoken_name("banana", "hi") == "केला"
    assert get_crop_spoken_name("banana", "gu") == "કેળા"
    assert get_crop_spoken_name("banana", "en") == "Banana"

    assert get_mandi_spoken_name("ap-guntur-01", "Guntur", "te") == "గుంటూరు మార్కెట్"
    assert get_mandi_spoken_name("ap-guntur-01", "Guntur", "hi") == "गुंटूर मंडी"
    assert get_mandi_spoken_name("ap-tenali-01", "Tenali", "te") == "తెనాలి మార్కెట్"


def test_format_price_spoken_verbal_currency() -> None:
    """Verifies conversion of float prices to spoken currency words."""
    assert format_price_spoken(25.0, "te") == "కిలో 25 రూపాయలు"
    assert format_price_spoken(25.5, "te") == "కిలో 25 రూపాయల 50 పైసలు"

    assert "रुपये" in format_price_spoken(25.0, "hi")
    assert "રૂપિયા" in format_price_spoken(25.0, "gu")
    assert "25 rupees per kilo" in format_price_spoken(25.0, "en")


def test_build_mandi_prices_spoken_summary_under_one_minute() -> None:
    """Verifies concise spoken summary generation under one minute."""
    mandis_data = [
        {
            "mandi_id": "ap-guntur-01",
            "name": "Guntur",
            "distance_km": 0.0,
            "modal_price_per_kg": 25.0,
        },
        {
            "mandi_id": "ap-tenali-01",
            "name": "Tenali",
            "distance_km": 24.5,
            "modal_price_per_kg": 24.5,
        },
        {
            "mandi_id": "ap-vijayawada-01",
            "name": "Vijayawada",
            "distance_km": 32.0,
            "modal_price_per_kg": 26.0,
        },
    ]

    summary_te = build_mandi_prices_spoken_summary(mandis_data, crop_id="banana", lang="te")
    assert "అరటిపండు" in summary_te
    assert "గుంటూరు" in summary_te
    assert "తెనాలి" in summary_te

    # Average speaking speed is 2.5 words/second. 150 words = 1 minute.
    word_count = len(summary_te.split())
    assert word_count < 80  # Well under 1 minute threshold


def test_audio_cache_roundtrip(tmp_path: Path) -> None:
    """Verifies audio cache writes and reads per crop+district+date."""
    cache = AudioCache(cache_dir=tmp_path)
    audio_bytes = create_minimal_wav_bytes(duration_sec=1.0)
    synth_res = AudioSynthesisResult(
        audio_bytes=audio_bytes,
        format="wav",
        duration_seconds=1.0,
        provider="test-tts",
    )

    # Cache should be empty initially
    assert cache.get("banana", "guntur", "2026-10-13", "te", "kg") is None

    # Set cache
    key = cache.set("banana", "guntur", "2026-10-13", "te", synth_res, "kg")
    assert key is not None

    # Retrieve from cache
    cached = cache.get("banana", "guntur", "2026-10-13", "te", "kg")
    assert cached is not None
    assert cached.audio_bytes == audio_bytes
    assert cached.format == "wav"


def test_intent_and_entity_extraction() -> None:
    """Verifies extraction of crops, districts, and intent from user speech text."""
    # Telugu query
    ext1 = speech_manager.extract_intent_and_entities("గుంటూరు లో అరటిపండు ధర ఎంత")
    assert ext1["crop_id"] == "banana"
    assert ext1["district"] == "guntur"
    assert ext1["intent"] == "price_check"

    # Hindi query
    ext2 = speech_manager.extract_intent_and_entities("मुझे केला बेचना है")
    assert ext2["crop_id"] == "banana"
    assert ext2["intent"] == "sell"

    # Transport query
    ext3 = speech_manager.extract_intent_and_entities("విజయవాడ నుండి రవాణా డ్రైవర్ కావాలి")
    assert ext3["district"] == "ntr"
    assert ext3["intent"] == "transport"


@pytest.mark.asyncio
async def test_speech_manager_graceful_fallback() -> None:
    """Verifies that speech manager falls back to mock if primary adapter fails."""
    manager = SpeechManager()
    wav_bytes = create_minimal_wav_bytes(duration_sec=1.0)

    # Transcription should succeed via fallback
    tr = await manager.transcribe(wav_bytes, language="te")
    assert tr.text is not None

    # Synthesis should succeed via fallback
    syn = await manager.synthesize("పరీక్ష సందేశం", language="te")
    assert syn.audio_bytes.startswith(b"RIFF")
