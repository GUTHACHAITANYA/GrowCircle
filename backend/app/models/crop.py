"""
Crop database model.
"""

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.price import Price


class Crop(Base):
    __tablename__ = "crops"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)  # e.g. 'banana'
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    name_te: Mapped[str] = mapped_column(String(100), nullable=False)
    name_hi: Mapped[str] = mapped_column(String(100), nullable=False)
    name_gu: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str] = mapped_column(String(50), nullable=True)  # icon identifier
    category: Mapped[str] = mapped_column(String(50), default="fruit")  # 'fruit', 'vegetable'

    prices: Mapped[list["Price"]] = relationship(
        "Price", back_populates="crop", cascade="all, delete-orphan"
    )
