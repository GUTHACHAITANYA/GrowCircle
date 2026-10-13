"""
User Inquiry database model for recording intent (sell, transport, price_check)
from IVR, WhatsApp, and Web channels.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class Inquiry(Base):
    __tablename__ = "inquiries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # 'ivr', 'whatsapp', 'web'
    intent: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'sell', 'transport', 'price_check'
    crop_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="te", nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # 'pending', 'contacted', 'resolved'

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
