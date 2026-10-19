"""
Mutual Rating database model for transport trips.
Supports 2-way reviews: driver <-> farmer, and driver <-> buyer.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.trip import Trip
    from backend.app.models.user import User


class TripRating(Base):
    __tablename__ = "trip_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("trips.id", ondelete="CASCADE"), index=True, nullable=False
    )
    rater_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    ratee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Role interaction:
    # 'driver_to_farmer', 'driver_to_buyer', 'farmer_to_driver', 'buyer_to_driver'
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 to 5 stars

    # Quick tags: e.g. 'punctual', 'careful_handling', 'quick_loading', 'clear_directions', 'delayed_unloading'
    tag: Mapped[str | None] = mapped_column(String(50), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    trip: Mapped["Trip"] = relationship("Trip", back_populates="ratings")
    rater: Mapped["User"] = relationship("User", foreign_keys=[rater_id])
    ratee: Mapped["User"] = relationship("User", foreign_keys=[ratee_id])
