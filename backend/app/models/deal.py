"""
Deal database model.
Created upon mutual acceptance of an offer.
Explicit non-custodial: GrowCircle holds zero financial custody.
"""

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.buyer import BuyerProfile
    from backend.app.models.listing import Listing
    from backend.app.models.offer import Offer
    from backend.app.models.rating import Rating
    from backend.app.models.user import User


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    offer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("offers.id", ondelete="RESTRICT"), unique=True, index=True
    )
    listing_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("listings.id", ondelete="RESTRICT"), index=True
    )
    buyer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("buyer_profiles.id", ondelete="RESTRICT"), index=True
    )
    farmer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )

    agreed_price_kg: Mapped[float] = mapped_column(Float, nullable=False)
    quantity_kg: Mapped[float] = mapped_column(Float, nullable=False)

    # Reference value only - No payment processing or custody
    total_reference_value: Mapped[float] = mapped_column(Float, nullable=False)

    # Deal state: confirmed -> pickup_pending -> completed / cancelled
    status: Mapped[str] = mapped_column(
        String(20), default="confirmed", nullable=False, index=True
    )

    # 4-digit pickup handover OTP
    pickup_otp: Mapped[str] = mapped_column(String(6), nullable=False)

    deal_date: Mapped[date] = mapped_column(Date, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
    offer: Mapped["Offer"] = relationship("Offer", back_populates="deal")
    listing: Mapped["Listing"] = relationship("Listing", back_populates="deals")
    buyer: Mapped["BuyerProfile"] = relationship("BuyerProfile", back_populates="deals")
    farmer: Mapped["User"] = relationship("User", foreign_keys=[farmer_id])
    ratings: Mapped[list["Rating"]] = relationship(
        "Rating", back_populates="deal", cascade="all, delete-orphan"
    )
