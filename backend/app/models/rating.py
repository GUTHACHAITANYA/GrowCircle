"""
Ratings and Review database model for post-deal trust building.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.deal import Deal
    from backend.app.models.user import User


class Rating(Base):
    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deal_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("deals.id", ondelete="CASCADE"), index=True, nullable=False
    )
    rater_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    ratee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    role: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # 'farmer_to_buyer' or 'buyer_to_farmer'
    score: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 to 5 stars

    # Reliability tag: 'prompt_pickup', 'quality_as_described', 'fair_deal', 'delayed_pickup'
    reliability_tag: Mapped[str | None] = mapped_column(String(50), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    deal: Mapped["Deal"] = relationship("Deal", back_populates="ratings")
    rater: Mapped["User"] = relationship("User", foreign_keys=[rater_id])
    ratee: Mapped["User"] = relationship("User", foreign_keys=[ratee_id])
