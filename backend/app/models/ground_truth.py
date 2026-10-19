"""
Ground-truth validation check model for manual phone audits with mandi secretaries / traders.
"""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class GroundTruthCheck(Base):
    __tablename__ = "ground_truth_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mandi_id: Mapped[int] = mapped_column(
        ForeignKey("mandis.id", ondelete="CASCADE"), nullable=False, index=True
    )
    crop_id: Mapped[str] = mapped_column(
        ForeignKey("crops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    variety: Mapped[str] = mapped_column(String(100), default="Other", nullable=False)
    grade: Mapped[str] = mapped_column(String(50), default="FAQ", nullable=False)
    check_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Price recorded in GrowCircle app at time of check (₹ / kg)
    price_shown_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Ground-truth price confirmed via phone call with mandi secretary / trader (₹ / kg)
    price_quoted_kg: Mapped[float] = mapped_column(Float, nullable=False)

    # Source contact identity & role (e.g. 'Secretary', 'Trader', 'Commission Agent')
    contact_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    contact_role: Mapped[str] = mapped_column(String(50), default="secretary", nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Accuracy metrics
    difference_kg: Mapped[float | None] = mapped_column(Float, nullable=True)  # (shown - quoted)
    difference_pct: Mapped[float | None] = mapped_column(Float, nullable=True)  # ((shown - quoted) / quoted) * 100

    is_price_missing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_price_late: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # price in app was >24h old

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    mandi = relationship("Mandi")
    crop = relationship("Crop")
