"""
Pydantic schemas for Phase 4: Transport.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


# Transporter schemas
class TransporterCreate(BaseModel):
    user_id: int
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., pattern=r"^\+?[0-9]{10,15}$")
    license_number: str = Field(..., min_length=5, max_length=50)
    license_expiry: date
    license_photo_url: str
    rc_number: str = Field(..., min_length=5, max_length=50)
    rc_expiry: date
    rc_photo_url: str
    insurance_expiry: date
    insurance_photo_url: str | None = None
    fitness_expiry: date
    fitness_photo_url: str | None = None
    vehicle_type: str = Field(..., pattern=r"^(goods_auto|mini_truck|large_truck)$")
    vehicle_model: str = Field(..., min_length=2, max_length=50)
    capacity_kg: int = Field(..., gt=0)
    service_area_districts: list[str] = Field(default_factory=list)
    current_latitude: float = Field(..., ge=-90.0, le=90.0)
    current_longitude: float = Field(..., ge=-180.0, le=180.0)


class TransporterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    phone: str
    vehicle_type: str
    vehicle_model: str
    capacity_kg: int
    service_area_districts: list[str]
    current_latitude: float
    current_longitude: float
    is_verified: bool
    available_today: bool
    reliability_rating: float
    trips_completed: int
    license_expiry: date
    rc_expiry: date
    insurance_expiry: date
    fitness_expiry: date
    is_compliant: bool
    expired_documents: list[str]
    decrypted_license_number: str | None = None
    decrypted_rc_number: str | None = None


class AvailabilityToggleRequest(BaseModel):
    available_today: bool


# Driver Suggestions & Guide Rate
class DriverSuggestionItem(BaseModel):
    transporter_id: int
    name: str
    phone: str
    vehicle_type: str
    vehicle_model: str
    capacity_kg: int
    distance_to_pickup_km: float
    reliability_rating: float
    trips_completed: int


class DriverSuggestionResponse(BaseModel):
    load_weight_kg: float
    matched_vehicle_type: str
    vehicle_description: str
    trip_distance_km: float
    guide_rate: float
    rate_label: str
    disclaimer: str
    suggested_drivers: list[DriverSuggestionItem]
    total_available_compliant_drivers: int


# Trip Schemas
class TripCreateRequest(BaseModel):
    transporter_id: int
    deal_ids: list[int]
    vehicle_type: str
    total_weight_kg: float
    distance_km: float
    guide_rate: float
    pickup_latitude: float
    pickup_longitude: float
    dropoff_latitude: float
    dropoff_longitude: float
    pickup_address: str | None = None
    dropoff_address: str | None = None
    actual_freight_agreed: float | None = None
    is_pooled: bool = False


class TripResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transporter_id: int
    deal_id: int | None
    deal_ids: list[int]
    status: str
    vehicle_type: str
    total_weight_kg: float
    distance_km: float
    guide_rate: float
    actual_freight_agreed: float | None
    pickup_otp: str
    delivery_otp: str
    pickup_confirmed_at: datetime | None
    delivery_confirmed_at: datetime | None
    delivery_photo_url: str | None
    buyer_dispute_reason: str | None
    buyer_dispute_photo_url: str | None
    pickup_latitude: float
    pickup_longitude: float
    dropoff_latitude: float
    dropoff_longitude: float
    is_pooled: bool
    created_at: datetime


class VerifyPickupOtpRequest(BaseModel):
    pickup_otp: str = Field(..., min_length=4, max_length=6)


class VerifyDeliveryOtpRequest(BaseModel):
    delivery_otp: str = Field(..., min_length=4, max_length=6)
    delivery_photo_url: str = Field(..., min_length=5)


class BuyerDisputeRequest(BaseModel):
    dispute_reason: str = Field(..., min_length=5)
    dispute_photo_url: str = Field(..., min_length=5)


class DisputeResolveRequest(BaseModel):
    resolution_notes: str = Field(..., min_length=5)
    final_status: str = Field(default="delivered", pattern=r"^(delivered|cancelled)$")


# Mutual Rating Schemas
class TripRatingCreate(BaseModel):
    trip_id: int
    ratee_id: int
    role: str = Field(
        ...,
        pattern=r"^(driver_to_farmer|driver_to_buyer|farmer_to_driver|buyer_to_driver)$",
    )
    score: int = Field(..., ge=1, le=5)
    tag: str | None = None
    comment: str | None = None


class TripRatingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_id: int
    rater_id: int
    ratee_id: int
    role: str
    score: int
    tag: str | None
    comment: str | None
    created_at: datetime


# Pooling Schemas
class PoolingDealItem(BaseModel):
    deal_id: int
    buyer_id: int
    farmer_name: str = "Farmer"
    quantity_kg: float
    pickup_lat: float
    pickup_lng: float
    pickup_address: str | None = None
    dropoff_lat: float
    dropoff_lng: float
    dropoff_address: str | None = None


class PoolingPlanRequest(BaseModel):
    deals: list[PoolingDealItem]
    max_pickup_cluster_km: float = 15.0


class PoolingPickupStop(BaseModel):
    deal_id: int
    farmer_name: str
    latitude: float
    longitude: float
    quantity_kg: float


class PoolingPlanItem(BaseModel):
    is_pooled: bool
    deal_ids: list[int]
    total_weight_kg: float
    vehicle_type: str
    pickup_stops: list[PoolingPickupStop]
    dropoff_address: str
    total_distance_km: float
    combined_guide_rate: float
    individual_fares_sum: float
    estimated_savings: float


class PoolingPlanResponse(BaseModel):
    plans: list[PoolingPlanItem]
    total_pooled_plans: int
