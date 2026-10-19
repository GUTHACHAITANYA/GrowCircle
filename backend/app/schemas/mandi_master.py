"""
Pydantic schemas for Mandi Master, LGD hierarchy, geocoding review, and duplicate merging.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class MandiOut(BaseModel):
    id: int
    name: str
    canonical_name: str
    district: str
    state: str
    mandal: str | None = None
    state_id: str | None = None
    district_id: int | None = None
    mandal_id: int | None = None
    state_lgd_code: int | None = None
    district_lgd_code: int | None = None
    mandal_lgd_code: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_verified: bool
    geocode_confidence: float | None = None
    geocode_source: str | None = None
    needs_review: bool
    review_reason: str | None = None
    is_active: bool
    merged_into_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class CoordinateFixRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    mandal_name: str | None = None
    notes: str | None = None


class MandiMergeRequest(BaseModel):
    primary_mandi_id: int
    duplicate_mandi_id: int
    notes: str | None = None


class StateMandiCount(BaseModel):
    state_name: str
    state_id: str | None
    total_mandis: int
    verified_coordinates_count: int
    mandal_mapped_count: int
    needs_review_count: int


class MandiHierarchyReport(BaseModel):
    total_mandis: int
    total_verified_coordinates: int
    total_mandal_mapped: int
    total_needs_review: int
    states_breakdown: list[StateMandiCount]
    review_queue: list[MandiOut]
