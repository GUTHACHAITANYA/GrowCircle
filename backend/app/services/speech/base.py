"""
Base protocols and interfaces for Speech-to-Text (STT) and Text-to-Speech (TTS).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    text: str
    detected_language: str
    confidence: float
    provider: str


@dataclass
class AudioSynthesisResult:
    audio_bytes: bytes
    format: str  # 'wav', 'mp3', 'ogg'
    duration_seconds: float
    provider: str


class SpeechToTextProvider(ABC):
    """Abstract interface for speech transcription services."""

    @abstractmethod
    async def transcribe(
        self, audio_bytes: bytes, language: str | None = None
    ) -> TranscriptionResult:
        """Transcribes incoming audio payload into text."""


class TextToSpeechProvider(ABC):
    """Abstract interface for text-to-speech synthesis services."""

    @abstractmethod
    async def synthesize(self, text: str, language: str = "te") -> AudioSynthesisResult:
        """Synthesizes given text into spoken audio bytes."""
