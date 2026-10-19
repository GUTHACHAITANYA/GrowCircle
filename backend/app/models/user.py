"""
User database model with DPDP Act consent, authentication security, and role-based access.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(
        String(10), default="te", nullable=False
    )  # Supported 23 language codes
    district: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    role: Mapped[str] = mapped_column(
        String(50), default="consumer", nullable=False
    )  # farmer, buyer, driver, consumer, admin

    # R6 Authentication & Security fields:
    session_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_admin_2fa_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    failed_otp_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # India DPDP Act compliance: Explicit user consent timestamp and management
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consent_version: Mapped[str | None] = mapped_column(String(20), default="1.0", nullable=True)
    consent_purpose: Mapped[str | None] = mapped_column(
        String(255), default="mandi_prices_and_marketplace", nullable=True
    )
    consent_withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
