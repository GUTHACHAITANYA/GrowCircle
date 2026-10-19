"""
Feedback database model for pilot user voice and one-key feedback.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class Feedback(Base):
    __tablename__ = "feedbacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(20), default="web", nullable=False)  # web, ivr, whatsapp
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5 or DTMF 1-3
    category: Mapped[str] = mapped_column(String(50), default="general", nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    voice_audio_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
