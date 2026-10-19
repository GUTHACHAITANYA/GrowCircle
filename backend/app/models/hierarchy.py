"""
LGD Administrative Hierarchy models: StateMaster > DistrictMaster > MandalMaster.
Provides canonical codes and geographic bounds from Local Government Directory (LGD).
"""

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class StateMaster(Base):
    __tablename__ = "states_master"

    id: Mapped[str] = mapped_column(String(10), primary_key=True)  # e.g. 'AP', 'TS', 'KA', 'TN'
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    lgd_code: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)

    # Geographic bounding box for coordinate sanity validation
    min_lat: Mapped[float] = mapped_column(Float, nullable=False)
    max_lat: Mapped[float] = mapped_column(Float, nullable=False)
    min_lon: Mapped[float] = mapped_column(Float, nullable=False)
    max_lon: Mapped[float] = mapped_column(Float, nullable=False)

    districts: Mapped[list["DistrictMaster"]] = relationship(
        "DistrictMaster", back_populates="state", cascade="all, delete-orphan"
    )


class DistrictMaster(Base):
    __tablename__ = "districts_master"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    state_id: Mapped[str] = mapped_column(
        ForeignKey("states_master.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    lgd_code: Mapped[int | None] = mapped_column(Integer, nullable=True)

    state: Mapped["StateMaster"] = relationship("StateMaster", back_populates="districts")
    mandals: Mapped[list["MandalMaster"]] = relationship(
        "MandalMaster", back_populates="district", cascade="all, delete-orphan"
    )


class MandalMaster(Base):
    __tablename__ = "mandals_master"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    district_id: Mapped[int] = mapped_column(
        ForeignKey("districts_master.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    lgd_code: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Approximate centroid coordinates for distance mapping to nearest mandis
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    district: Mapped["DistrictMaster"] = relationship("DistrictMaster", back_populates="mandals")
