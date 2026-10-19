"""
Transporter and Driver database model for Phase 4: Transport.
Supports Goods Autos, Mini-Trucks, and Larger Trucks with automatic document expiry checks.
"""

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.trip import Trip
    from backend.app.models.user import User


class Transporter(Base):
    __tablename__ = "transporters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Driving Licence (Encrypted at rest under DPDP Act)
    license_number: Mapped[str] = mapped_column(Text, nullable=False)
    license_expiry: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    license_photo_url: Mapped[str] = mapped_column(String(255), nullable=False)

    # Registration Certificate (RC) (Encrypted at rest under DPDP Act)
    rc_number: Mapped[str] = mapped_column(Text, nullable=False)
    rc_expiry: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    rc_photo_url: Mapped[str] = mapped_column(String(255), nullable=False)

    # Insurance & Fitness
    insurance_expiry: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    insurance_photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fitness_expiry: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    fitness_photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Vehicle Specifications
    # vehicle_type: 'goods_auto' (<500kg), 'mini_truck' (500kg-1500kg), 'large_truck' (>1500kg)
    vehicle_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    vehicle_model: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "Piaggio Ape", "Tata Ace"
    capacity_kg: Mapped[int] = mapped_column(Integer, nullable=False)

    # Service Area & Coordinates
    # service_area_districts: ["Guntur", "Krishna", "NTR"]
    service_area_districts: Mapped[list[str]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=list)
    current_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    current_longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # Verification & Availability
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    available_today: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Reliability and Stats
    reliability_rating: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    trips_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

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
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    trips: Mapped[list["Trip"]] = relationship("Trip", back_populates="transporter")

    def is_active_and_compliant(self, check_date: date | None = None) -> bool:
        """
        Automatic expiry check:
        Hides drivers if ANY document (Licence, RC, Insurance, Fitness) is expired,
        or if driver is unverified or has turned off 'available_today'.
        """
        ref_date = check_date or date.today()
        if not self.is_verified:
            return False
        if not self.available_today:
            return False
        if self.license_expiry < ref_date:
            return False
        if self.rc_expiry < ref_date:
            return False
        if self.insurance_expiry < ref_date:
            return False
        if self.fitness_expiry < ref_date:
            return False
        return True

    def get_expired_documents(self, check_date: date | None = None) -> list[str]:
        """Returns a list of expired document names."""
        ref_date = check_date or date.today()
        expired: list[str] = []
        if self.license_expiry < ref_date:
            expired.append("driving_license")
        if self.rc_expiry < ref_date:
            expired.append("registration_certificate")
        if self.insurance_expiry < ref_date:
            expired.append("insurance")
        if self.fitness_expiry < ref_date:
            expired.append("fitness")
        return expired

    def get_decrypted_license(self) -> str:
        from backend.app.services.security import decrypt_document_data

        return decrypt_document_data(self.license_number)

    def get_decrypted_rc(self) -> str:
        from backend.app.services.security import decrypt_document_data

        return decrypt_document_data(self.rc_number)

