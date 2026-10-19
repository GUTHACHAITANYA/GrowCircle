"""
Trip database model for Phase 4: Transport.
Tracks pickup & delivery OTPs, photo evidence, guide rates, and dispute resolution.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.deal import Deal
    from backend.app.models.transporter import Transporter
    from backend.app.models.trip_rating import TripRating


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transporter_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("transporters.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    deal_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("deals.id", ondelete="SET NULL"), index=True, nullable=True
    )

    # List of deal IDs bundled in this trip (supports multi-load pooling)
    deal_ids: Mapped[list[int]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=list)

    # Trip Status:
    # 'assigned' -> 'arrived_pickup' -> 'in_transit' -> 'delivered' / 'disputed' / 'cancelled'
    status: Mapped[str] = mapped_column(
        String(30), default="assigned", nullable=False, index=True
    )

    vehicle_type: Mapped[str] = mapped_column(String(30), nullable=False)
    total_weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)

    # Guide rate (distance x vehicle type), labelled as a guide, not a fixed price
    guide_rate: Mapped[float] = mapped_column(Float, nullable=False)
    actual_freight_agreed: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Pickup OTP (shared by farmer upon loading)
    pickup_otp: Mapped[str] = mapped_column(String(6), nullable=False)
    pickup_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Delivery OTP (shared by buyer upon receiving produce at destination)
    delivery_otp: Mapped[str] = mapped_column(String(6), nullable=False)
    delivery_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Mandatory photo of crates unloaded at buyer facility
    delivery_photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Buyer Complaint / Dispute at delivery
    buyer_dispute_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    buyer_dispute_photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dispute_resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dispute_resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Geolocation & Addresses
    pickup_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    pickup_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    pickup_address: Mapped[str | None] = mapped_column(String(255), nullable=True)

    dropoff_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    dropoff_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    dropoff_address: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_pooled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

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
    transporter: Mapped["Transporter"] = relationship("Transporter", back_populates="trips")
    deal: Mapped["Deal | None"] = relationship("Deal", foreign_keys=[deal_id])
    ratings: Mapped[list["TripRating"]] = relationship(
        "TripRating", back_populates="trip", cascade="all, delete-orphan"
    )
