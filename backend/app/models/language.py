"""
Language database model representing coverage status across all 22 scheduled Indian languages plus English.
Fields include ui_ready, voice_stt_ready, voice_tts_ready, reviewed_by_native_speaker.
"""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class Language(Base):
    __tablename__ = "languages"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name_en: Mapped[str] = mapped_column(String(50), nullable=False)
    name_native: Mapped[str] = mapped_column(String(100), nullable=False)
    script: Mapped[str] = mapped_column(String(50), nullable=False)
    is_rtl: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ui_ready: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    voice_stt_ready: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    voice_tts_ready: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed_by_native_speaker: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fallback_code: Mapped[str] = mapped_column(String(10), default="en", nullable=False)


