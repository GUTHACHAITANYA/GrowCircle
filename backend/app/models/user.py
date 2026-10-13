"""
User database model with DPDP Act consent and role-based access.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    language: Mapped[str] = mapped_column(
        String(10), default="te", nullable=False
    )  # 'en', 'te', 'hi', 'gu'
    district: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    role: Mapped[str] = mapped_column(
        String(50), default="consumer", nullable=False
    )  # farmer, buyer, driver, consumer, admin

    # India DPDP Act compliance: Explicit user consent timestamp
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
