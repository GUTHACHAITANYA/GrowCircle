"""
Audio caching layer per crop + district + date + language + unit,
and for static prerecorded common phrases.
"""

import hashlib
import json
from pathlib import Path

from backend.app.services.speech.base import AudioSynthesisResult

CACHE_DIR = Path("backend/data/audio_cache")


class AudioCache:
    """
    Disk-backed audio cache ensuring synthesis calls are not repeated
    for the same price broadcasts on any given day.
    """

    def __init__(self, cache_dir: Path = CACHE_DIR) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_key(
        self,
        crop_id: str,
        district: str,
        date_str: str,
        language: str,
        unit: str = "kg",
    ) -> str:
        raw = f"{crop_id.lower().strip()}_{district.lower().strip()}_{date_str}_{language.lower().strip()}_{unit.lower().strip()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(
        self,
        crop_id: str,
        district: str,
        date_str: str,
        language: str,
        unit: str = "kg",
    ) -> AudioSynthesisResult | None:
        """Retrieves cached audio if present."""
        key = self._get_key(crop_id, district, date_str, language, unit)
        audio_file = self.cache_dir / f"{key}.wav"
        meta_file = self.cache_dir / f"{key}.json"

        if audio_file.exists() and meta_file.exists():
            try:
                audio_bytes = audio_file.read_bytes()
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                return AudioSynthesisResult(
                    audio_bytes=audio_bytes,
                    format=meta.get("format", "wav"),
                    duration_seconds=meta.get("duration_seconds", 1.0),
                    provider=meta.get("provider", "cache"),
                )
            except Exception:
                return None
        return None

    def set(
        self,
        crop_id: str,
        district: str,
        date_str: str,
        language: str,
        result: AudioSynthesisResult,
        unit: str = "kg",
    ) -> str:
        """Stores synthesized audio and metadata into cache."""
        key = self._get_key(crop_id, district, date_str, language, unit)
        audio_file = self.cache_dir / f"{key}.wav"
        meta_file = self.cache_dir / f"{key}.json"

        audio_file.write_bytes(result.audio_bytes)
        meta = {
            "crop_id": crop_id,
            "district": district,
            "date": date_str,
            "language": language,
            "unit": unit,
            "format": result.format,
            "duration_seconds": result.duration_seconds,
            "provider": result.provider,
        }
        meta_file.write_text(json.dumps(meta), encoding="utf-8")
        return key

    def get_prerecorded_phrase(self, phrase_id: str, language: str) -> AudioSynthesisResult | None:
        """Retrieves prerecorded static phrase audio from cache."""
        key = f"phrase_{phrase_id}_{language}"
        hashed_key = hashlib.sha256(key.encode("utf-8")).hexdigest()
        audio_file = self.cache_dir / f"{hashed_key}.wav"
        meta_file = self.cache_dir / f"{hashed_key}.json"

        if audio_file.exists() and meta_file.exists():
            try:
                audio_bytes = audio_file.read_bytes()
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                return AudioSynthesisResult(
                    audio_bytes=audio_bytes,
                    format=meta.get("format", "wav"),
                    duration_seconds=meta.get("duration_seconds", 1.0),
                    provider="prerecorded",
                )
            except Exception:
                return None
        return None

    def set_prerecorded_phrase(
        self, phrase_id: str, language: str, result: AudioSynthesisResult
    ) -> None:
        """Stores prerecorded static phrase audio."""
        key = f"phrase_{phrase_id}_{language}"
        hashed_key = hashlib.sha256(key.encode("utf-8")).hexdigest()
        audio_file = self.cache_dir / f"{hashed_key}.wav"
        meta_file = self.cache_dir / f"{hashed_key}.json"

        audio_file.write_bytes(result.audio_bytes)
        meta = {
            "phrase_id": phrase_id,
            "language": language,
            "format": result.format,
            "duration_seconds": result.duration_seconds,
            "provider": result.provider,
        }
        meta_file.write_text(json.dumps(meta), encoding="utf-8")
