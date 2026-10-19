"""
Consumer price alert model for WhatsApp and Telegram notifications.
No login required for consumer subscriptions.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base

if TYPE_CHECKING:
    pass


class PriceAlert(Base):
    """
    Consumer alerts for commodity prices via WhatsApp or Telegram.
    Allows families and buyers to track affordability thresholds.
    """

    __tablename__ = "price_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_phone: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    channel: Mapped[str] = mapped_column(String(20), default="whatsapp", nullable=False)  # 'whatsapp', 'telegram'
    telegram_chat_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    crop_id: Mapped[str] = mapped_column(String(50), ForeignKey("crops.id"), nullable=False)
    district: Mapped[str] = mapped_column(String(100), default="Guntur", nullable=False)
    alert_type: Mapped[str] = mapped_column(
        String(50), default="below_price", nullable=False
    )  # 'below_price', 'above_price', 'weekly_digest'
    target_price_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
