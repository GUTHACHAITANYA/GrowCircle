"""
Negotiation Offer and Counter-Offer database model.
Supports multi-turn bargaining with explicit read-back confirmations.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.buyer import BuyerProfile
    from backend.app.models.deal import Deal
    from backend.app.models.listing import Listing


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("listings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    buyer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("buyer_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    buyer_need_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    offered_price_kg: Mapped[float] = mapped_column(Float, nullable=False)
    quantity_kg: Mapped[float] = mapped_column(Float, nullable=False)

    # Counter-offer tracking
    counter_price_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    counter_by: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # 'farmer' or 'buyer'

    # State: pending, countered, accepted, rejected, expired
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    listing: Mapped["Listing"] = relationship("Listing", back_populates="offers")
    buyer: Mapped["BuyerProfile"] = relationship("BuyerProfile", back_populates="offers")
    deal: Mapped["Deal | None"] = relationship("Deal", back_populates="offer", uselist=False)
