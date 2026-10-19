"""
Mandi (Market Yard) database model with PostGIS spatial geometry.
"""

from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.hierarchy import DistrictMaster, MandalMaster, StateMaster
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

    def process_bind_param(self, value: object, dialect: object) -> object:
        if dialect is not None and getattr(dialect, "name", "") == "sqlite":
            if value is not None:
                return str(value)
        return value

    def process_result_value(self, value: object, dialect: object) -> object:
        return value


class Mandi(Base):
    __tablename__ = "mandis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    canonical_name: Mapped[str] = mapped_column(String(150), default="", nullable=False, index=True)
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    mandal: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # LGD Hierarchy Links
    state_id: Mapped[str | None] = mapped_column(
        ForeignKey("states_master.id", ondelete="SET NULL"), nullable=True, index=True
    )
    district_id: Mapped[int | None] = mapped_column(
        ForeignKey("districts_master.id", ondelete="SET NULL"), nullable=True, index=True
    )
    mandal_id: Mapped[int | None] = mapped_column(
        ForeignKey("mandals_master.id", ondelete="SET NULL"), nullable=True, index=True
    )

    state_lgd_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    district_lgd_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mandal_lgd_code: Mapped[int | None] = mapped_column(Integer, nullable=True)

    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # PostGIS Point geometry: SRID 4326 (WGS 84 GPS standard)
    location = mapped_column(SpatialPoint(), nullable=True)

    # Verification & Quality Guards
    location_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    geocode_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    geocode_source: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 'nominatim', 'lgd', 'manual', 'verified_seed'
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    review_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Duplicate resolution & status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    merged_into_id: Mapped[int | None] = mapped_column(
        ForeignKey("mandis.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    prices: Mapped[list["Price"]] = relationship(
        "Price", back_populates="mandi", cascade="all, delete-orphan"
    )
    state_rel: Mapped["StateMaster | None"] = relationship("StateMaster")
    district_rel: Mapped["DistrictMaster | None"] = relationship("DistrictMaster")
    mandal_rel: Mapped["MandalMaster | None"] = relationship("MandalMaster")
    merged_into = relationship("Mandi", remote_side=[id])
