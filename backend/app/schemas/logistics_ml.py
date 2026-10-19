"""
Pydantic schemas for Smart Matching & Logistics API.
Phase ML-5: Smarter Matching and Logistics.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# --- Buyer-Farmer Ranking Schemas ---
class RankingCandidateItem(BaseModel):
    candidate_id: str | int
    farmer_name: str
    crop: str
    distance_km: float = Field(..., ge=0.0)
    quantity_kg: float = Field(..., gt=0.0)
    requested_qty_kg: float = Field(..., gt=0.0)
    farmer_grade: str = "A"
    buyer_grade_req: str = "A"
    price_per_kg: float = Field(..., gt=0.0)
    mandi_modal_price: float = Field(..., gt=0.0)
    completion_rate: float = Field(default=0.90, ge=0.0, le=1.0)
    response_time_hours: float = Field(default=2.0, ge=0.0)
    rating: float = Field(default=4.5, ge=1.0, le=5.0)
    is_smallholder: bool = True
    implicit_feedback: dict[str, int] | None = None


class RankingRequest(BaseModel):
    query_id: str = Field(..., description="Unique search/query identifier for session tracking")
    buyer_id: str | int = Field(..., description="ID of buyer seeking matching crops")
    candidates: list[RankingCandidateItem] = Field(..., min_length=1)
    forced_variant: str | None = Field(default=None, description="'rules' or 'lambdarank' or None (auto A/B)")
    apply_fairness_mitigation: bool = Field(default=True, description="Boost smallholder parity if exposure < 80%")


class RankedCandidateResult(BaseModel):
    rank: int
    candidate_id: str | int
    farmer_name: str
    crop: str
    score: float
    is_smallholder: bool
    distance_km: float
    quantity_fit: float
    grade_fit: float
    price_fit_vs_mandi: float


class RankingResponse(BaseModel):
    query_id: str
    buyer_id: str | int
    variant_used: str
    ranked_candidates: list[RankedCandidateResult]
    fairness_audit: dict[str, Any]
    data_sufficiency: dict[str, Any]


# --- Fair Transport Rate Guide Schemas ---
class RateGuideRequest(BaseModel):
    distance_km: float = Field(..., gt=0.0, description="One-way trip distance in km")
    load_weight_kg: float = Field(..., gt=0.0, description="Load weight in kg")
    vehicle_type: str = Field(default="mini_truck", description="goods_auto, mini_truck, or large_truck")
    fuel_price_per_litre: float = Field(default=98.50, description="Regional diesel price in INR/L")
    road_type: str = Field(default="district_road", description="national_highway, state_highway, district_road, rural_unpaved")
    is_night: bool = Field(default=False, description="Whether trip occurs between 10 PM and 5 AM")


class RateGuideResponse(BaseModel):
    distance_km: float
    load_weight_kg: float
    vehicle_type: str
    vehicle_label: str
    fuel_price_per_litre: float
    road_type: str
    is_night: bool
    min_guide_rate: float
    estimated_guide_rate: float
    max_guide_rate: float
    rate_per_kg: float
    rate_label: str
    breakdown: dict[str, Any]
    disclaimer: str


# --- VRP Pooling Schemas ---
class PickupRequest(BaseModel):
    order_id: str
    farmer_name: str
    latitude: float
    longitude: float
    weight_kg: float = Field(..., gt=0.0)
    crop: str = "tomato"
    earliest_pickup_hour: float = 1.0
    latest_pickup_hour: float = 6.0


class DropoffRequest(BaseModel):
    destination_name: str
    latitude: float
    longitude: float
    latest_arrival_hour: float = 14.0


class VehicleRequest(BaseModel):
    vehicle_id: str
    vehicle_type: str = "mini_truck"
    capacity_kg: float = 1500.0


class PoolingRequest(BaseModel):
    pickups: list[PickupRequest] = Field(..., min_length=1)
    dropoff: DropoffRequest
    vehicles: list[VehicleRequest] | None = None
    max_search_seconds: int = 2


class PoolingResponse(BaseModel):
    success: bool
    solver: str
    total_pickups_pooled: int
    total_vehicles_used: int
    total_pooled_distance_km: float
    total_cargo_weight_kg: float
    routes: list[dict[str, Any]]
    savings: dict[str, Any]


# --- Driver Matching Schemas ---
class DriverItem(BaseModel):
    driver_id: str | int
    name: str
    phone: str
    vehicle_type: str
    vehicle_model: str
    capacity_kg: float
    current_latitude: float
    current_longitude: float
    reliability_rating: float = Field(default=4.5, ge=1.0, le=5.0)
    on_time_rate: float = Field(default=0.92, ge=0.0, le=1.0)
    trips_completed_total: int = 25
    recent_trips_count: int = 2
    is_verified: bool = True
    is_available: bool = True


class DriverMatchRequest(BaseModel):
    pickup_lat: float
    pickup_lng: float
    load_weight_kg: float
    drivers: list[DriverItem] = Field(..., min_length=1)
    apply_fairness_leveling: bool = True
    limit: int = 5


class DriverMatchResponse(BaseModel):
    total_evaluated: int
    ranked_drivers: list[dict[str, Any]]
    gini_coefficient: float
    leveling_enabled: bool
