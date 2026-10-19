"""
Farmer Produce Listing database model.
Enforces fresh media capture metadata (rejecting old gallery uploads),
fixed photo checklist (whole lot, close-up, opened crate), and Grades A/B/C.
"""

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.mandi import SpatialPoint

if TYPE_CHECKING:
    from backend.app.models.crop import Crop
    from backend.app.models.deal import Deal
    from backend.app.models.offer import Offer
    from backend.app.models.user import User

GRADE_DESCRIPTIONS = {
    "A": "Export / Premium - uniform size, unblemished skin, highest firmness",
    "B": "Standard Market - good color, uniform ripeness, minor cosmetic marks",
    "C": "Processing / Economy - mixed sizes, small blemishes, highly ripened",
}

REQUIRED_PHOTO_CHECKLIST = ["whole_lot", "close_up", "opened_crate"]


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    farmer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    crop_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("crops.id"), index=True, nullable=False
    )
    variety: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity_kg: Mapped[float] = mapped_column(Float, nullable=False)

    # Grades: A, B, C with human-friendly descriptions
    grade: Mapped[str] = mapped_column(String(5), nullable=False)
    harvest_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_price_kg: Mapped[float] = mapped_column(Float, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False, index=True
    )  # active, reserved, sold, expired

    # Fresh in-app media proof & checklist validation
    # media_checklist: {"whole_lot": url, "close_up": url, "opened_crate": url}
    media_checklist: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    media_captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    media_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    media_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Location
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
    farmer: Mapped["User"] = relationship("User", lazy="joined")
    crop: Mapped["Crop"] = relationship("Crop", lazy="joined")
    offers: Mapped[list["Offer"]] = relationship(
        "Offer", back_populates="listing", cascade="all, delete-orphan"
    )
    deals: Mapped[list["Deal"]] = relationship("Deal", back_populates="listing")
