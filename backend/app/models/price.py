"""
Mandi crop price database model with converted units and unique constraints.
"""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.crop import Crop
    from backend.app.models.mandi import Mandi


class Price(Base):
    __tablename__ = "prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mandi_id: Mapped[int] = mapped_column(
        ForeignKey("mandis.id", ondelete="CASCADE"), nullable=False, index=True
    )
    crop_id: Mapped[str] = mapped_column(
        ForeignKey("crops.id", ondelete="CASCADE"), nullable=False, index=True
    )

    variety: Mapped[str] = mapped_column(String(100), default="Other", nullable=False)
    grade: Mapped[str] = mapped_column(String(50), default="FAQ", nullable=False)
    price_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Prices in ₹ / quintal (raw Agmarknet unit: 1 quintal = 100 kg)
    min_price_quintal: Mapped[float] = mapped_column(Float, nullable=False)
    max_price_quintal: Mapped[float] = mapped_column(Float, nullable=False)
    modal_price_quintal: Mapped[float] = mapped_column(Float, nullable=False)

    # Converted units for users and buyers
    min_price_kg: Mapped[float] = mapped_column(Float, nullable=False)
    max_price_kg: Mapped[float] = mapped_column(Float, nullable=False)
    modal_price_kg: Mapped[float] = mapped_column(Float, nullable=False)
    modal_price_ton: Mapped[float] = mapped_column(Float, nullable=False)

    # Daily arrival volume in metric tonnes
    arrival_tonnes: Mapped[float] = mapped_column(Float, default=0.0)

    # Data origin
    source: Mapped[str] = mapped_column(String(50), default="data.gov.in", nullable=False)

    # Relationships
    mandi: Mapped["Mandi"] = relationship("Mandi", back_populates="prices")
    crop: Mapped["Crop"] = relationship("Crop", back_populates="prices")

    __table_args__ = (
        UniqueConstraint(
            "mandi_id",
            "crop_id",
            "variety",
            "grade",
            "price_date",
            name="uq_mandi_crop_variety_grade_date",
        ),
    )
