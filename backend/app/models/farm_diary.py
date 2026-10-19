"""
Farm Diary models: FarmSeason and FarmDiaryEntry.
Tracks plot area, costs, yield logs, sale revenues, and financial performance.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    pass


class FarmSeason(Base):
    """
    Represents a cultivation cycle or plot season for a farmer.
    e.g., 2.5 acres of Banana (Amruthapani) for Kharif 2026.
    """

    __tablename__ = "farm_seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    farmer_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    season_name: Mapped[str] = mapped_column(String(100), nullable=False)
    crop_id: Mapped[str] = mapped_column(String(50), ForeignKey("crops.id"), index=True, nullable=False)
    area_acres: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    soil_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    planting_date: Mapped[date] = mapped_column(Date, nullable=False)
    harvest_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_yield_kg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    district: Mapped[str] = mapped_column(String(100), default="Guntur", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    entries: Mapped[list["FarmDiaryEntry"]] = relationship(
        "FarmDiaryEntry",
        back_populates="season",
        cascade="all, delete-orphan",
        order_by="FarmDiaryEntry.entry_date.desc()",
    )


class FarmDiaryEntry(Base):
    """
    Individual diary ledger item: input cost, yield log, or sale revenue.
    Supports voice transcription with mandatory read-back confirmation.
    """

    __tablename__ = "farm_diary_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    season_id: Mapped[int] = mapped_column(Integer, ForeignKey("farm_seasons.id"), index=True, nullable=False)
    entry_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # 'cost', 'yield_log', 'sale_revenue'
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'seeds', 'fertilizer', 'labour', 'irrigation', 'machinery', 'transport', 'sale', 'other'
    amount_inr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    quantity_kg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unit_price_inr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    voice_raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    readback_confirmed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationship back to season
    season: Mapped["FarmSeason"] = relationship("FarmSeason", back_populates="entries")
