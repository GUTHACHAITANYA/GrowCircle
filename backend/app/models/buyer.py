"""
Buyer and Institution Profile model.
Stores business details, DPDP Act encrypted verification proof, and reliability score.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.mandi import SpatialPoint

if TYPE_CHECKING:
    from backend.app.models.buyer_need import BuyerNeed
    from backend.app.models.deal import Deal
    from backend.app.models.offer import Offer
    from backend.app.models.user import User


class BuyerProfile(Base):
    __tablename__ = "buyer_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    business_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    business_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # hostel, hotel, college, school, retail_shop, wholesaler, canteen

    # Verification workflow: pending -> verified / rejected
    verification_status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True
    )

    # DPDP Act compliance: Documents encrypted at rest via symmetric Fernet encryption
    encrypted_gst_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_document_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by_admin_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Reputation score (1.0 to 5.0)
    reliability_score: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    deals_completed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Location
    address: Mapped[str] = mapped_column(String(300), nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(100), default="Andhra Pradesh", nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    location: Mapped[Any] = mapped_column(SpatialPoint, nullable=True)

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
    user: Mapped["User"] = relationship("User", lazy="joined")
    needs: Mapped[list["BuyerNeed"]] = relationship(
        "BuyerNeed", back_populates="buyer", cascade="all, delete-orphan"
    )
    offers: Mapped[list["Offer"]] = relationship("Offer", back_populates="buyer")
    deals: Mapped[list["Deal"]] = relationship("Deal", back_populates="buyer")
