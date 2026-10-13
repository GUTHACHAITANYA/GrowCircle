"""
Mandi (Market Yard) database model with PostGIS spatial geometry.
"""

from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.price import Price


class SpatialPoint(TypeDecorator):
    """
    Transparent spatial point type:
    - On PostgreSQL: Full PostGIS Geometry('POINT', 4326)
    - On SQLite (isolated test runner): String representation so tests run without SpatiaLite C-binaries
    """

    impl = Geometry
    cache_ok = True

    def load_dialect_impl(self, dialect: object) -> object:
        if dialect is None or getattr(dialect, "name", "") == "sqlite":
            return (
                dialect.type_descriptor(String())
                if hasattr(dialect, "type_descriptor")
                else String()
            )
        return dialect.type_descriptor(Geometry(geometry_type="POINT", srid=4326))  # type: ignore[no-any-return]


class Mandi(Base):
    __tablename__ = "mandis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # e.g. 'Andhra Pradesh'
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)

    # PostGIS Point geometry: SRID 4326 (WGS 84 GPS standard)
    location = mapped_column(SpatialPoint(), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    prices: Mapped[list["Price"]] = relationship(
        "Price", back_populates="mandi", cascade="all, delete-orphan"
    )
