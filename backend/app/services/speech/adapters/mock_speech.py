"""
Mock implementations of STT and TTS providers for tests, local dev, and offline fallback.
Generates valid minimal WAV files with correct RIFF headers.
"""

import struct

from backend.app.services.speech.base import (
    AudioSynthesisResult,
    SpeechToTextProvider,
    TextToSpeechProvider,
    TranscriptionResult,
)


def create_minimal_wav_bytes(duration_sec: float = 1.0, sample_rate: int = 8000) -> bytes:
    """
    Generates a valid, minimal PCM WAV audio header and silence payload.
    Ensures media players and test validators accept the resulting byte stream.
    """
    num_samples = int(duration_sec * sample_rate)
    num_channels = 1
    bytes_per_sample = 2  # 16-bit
    data_size = num_samples * num_channels * bytes_per_sample

    header = bytearray()
    header.extend(b"RIFF")
    header.extend(struct.pack("<I", 36 + data_size))  # Chunk size
    header.extend(b"WAVE")
    header.extend(b"fmt ")
    header.extend(struct.pack("<I", 16))  # Subchunk1Size (16 for PCM)
    header.extend(struct.pack("<H", 1))  # AudioFormat (1 for PCM)
    header.extend(struct.pack("<H", num_channels))
    header.extend(struct.pack("<I", sample_rate))
    header.extend(struct.pack("<I", sample_rate * num_channels * bytes_per_sample))
    header.extend(struct.pack("<H", num_channels * bytes_per_sample))
    header.extend(struct.pack("<H", 16))  # BitsPerSample
    header.extend(b"data")
    header.extend(struct.pack("<I", data_size))

    # Silence payload
    silence = b"\x00" * data_size
    return bytes(header + silence)


class MockSTTProvider(SpeechToTextProvider):
    """
    Deterministic mock STT provider for CI tests and local emulation.
    """

    def __init__(self, fixed_transcription: str | None = None, fixed_language: str = "te") -> None:
        self.fixed_transcription = fixed_transcription
        self.fixed_language = fixed_language
        self.call_history: list[dict] = []

    async def transcribe(
        self, audio_bytes: bytes, language: str | None = None
    ) -> TranscriptionResult:
        self.call_history.append({"bytes_len": len(audio_bytes), "language_hint": language})

        detected_lang = language or self.fixed_language

        if self.fixed_transcription is not None:
            text = self.fixed_transcription
        elif detected_lang == "te":
            text = "అరటిపండు ధర ఎంత గుంటూరు"
        elif detected_lang == "hi":
            text = "केले का भाव कितना है गुंटूर"
        elif detected_lang == "gu":
            text = "કેળાનો ભાવ શું છે ગુંટૂર"
        else:
            text = "what is banana price in guntur"

        return TranscriptionResult(
            text=text,
            detected_language=detected_lang,
            confidence=0.98,
            provider="mock-stt",
        )


class MockTTSProvider(TextToSpeechProvider):
    """
    Deterministic mock TTS provider that produces valid WAV audio bytes.
    """

    def __init__(self) -> None:
        self.call_history: list[dict] = []

    async def synthesize(self, text: str, language: str = "te") -> AudioSynthesisResult:
        word_count = max(1, len(text.split()))
        estimated_duration = min(58.0, round(word_count * 0.45, 2))  # Keeps under 1 minute

        self.call_history.append(
            {
                "text": text,
                "language": language,
                "word_count": word_count,
                "duration": estimated_duration,
            }
        )

        audio_bytes = create_minimal_wav_bytes(duration_sec=estimated_duration)
        return AudioSynthesisResult(
            audio_bytes=audio_bytes,
            format="wav",
            duration_seconds=estimated_duration,
            provider="mock-tts",
        )
