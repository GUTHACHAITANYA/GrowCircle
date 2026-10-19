"""
Buyer Requirement / Need model.
Represents recurring (weekly/daily) or one-time institutional demand.
"""

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.mandi import SpatialPoint

if TYPE_CHECKING:
    from backend.app.models.buyer import BuyerProfile
    from backend.app.models.crop import Crop


class BuyerNeed(Base):
    __tablename__ = "buyer_needs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    buyer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("buyer_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    crop_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("crops.id"), index=True, nullable=False
    )
    quantity_kg: Mapped[float] = mapped_column(Float, nullable=False)
    frequency: Mapped[str] = mapped_column(
        String(20), default="weekly", nullable=False
    )  # daily, weekly, one_time
    preferred_grade: Mapped[str] = mapped_column(
        String(10), default="any", nullable=False
    )  # A, B, C, any
    target_price_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False, index=True
    )  # active, fulfilled, cancelled

    # Spatial center (inherits or overrides buyer coordinates)
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    location: Mapped[Any] = mapped_column(SpatialPoint, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    buyer: Mapped["BuyerProfile"] = relationship("BuyerProfile", back_populates="needs")
    crop: Mapped["Crop"] = relationship("Crop", lazy="joined")
