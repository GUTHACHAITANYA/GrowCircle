"""
Pydantic Schemas for Phase 3 Direct Selling:
Auth, Buyer verification, Needs, Fresh Produce Listings, Offers, Deals, Ratings, and Group Supply.
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


# --- Auth Schemas ---
class SendOtpIn(BaseModel):
    phone: str = Field(..., description="Indian 10-digit mobile number, e.g. '9848012345'")


class VerifyOtpIn(BaseModel):
    phone: str
    otp: str = Field(..., description="6-digit OTP received via SMS")
    role: str = Field("farmer", description="'farmer', 'buyer', 'institution', 'driver', 'admin'")


class AuthTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    phone: str
    role: str


# --- Buyer Profile & Verification Schemas ---
class BuyerRegisterIn(BaseModel):
    business_name: str
    business_type: str = Field(
        ..., description="hostel, hotel, college, school, retail_shop, wholesaler, canteen"
    )
    gst_number: str = Field(..., description="GSTIN or Shop & Establishment Act license number")
    document_ref: str = Field(..., description="Reference URL / ID to upload verification document")
    address: str
    district: str
    state: str = "Andhra Pradesh"
    latitude: float
    longitude: float


class BuyerProfileOut(BaseModel):
    id: int
    user_id: int
    business_name: str
    business_type: str
    verification_status: str  # pending, verified, rejected
    reliability_score: float
    deals_completed_count: int
    address: str
    district: str
    state: str
    latitude: float
    longitude: float
    verified_at: datetime | None


class AdminVerifyBuyerIn(BaseModel):
    decision: str = Field(..., description="'verified' or 'rejected'")
    notes: str | None = None


class AdminBuyerDetailOut(BuyerProfileOut):
    decrypted_gst_number: str
    decrypted_document_ref: str
    verification_notes: str | None


# --- Buyer Need Schemas ---
class BuyerNeedCreateIn(BaseModel):
    crop_id: str = "banana"
    quantity_kg: float = Field(..., gt=0)
    frequency: str = "weekly"  # daily, weekly, one_time
    preferred_grade: str = "any"  # A, B, C, any
    target_price_kg: float | None = None
    start_date: date
    district: str
    latitude: float
    longitude: float


class BuyerNeedOut(BaseModel):
    id: int
    buyer_id: int
    business_name: str
    crop_id: str
    quantity_kg: float
    frequency: str
    preferred_grade: str
    target_price_kg: float | None
    start_date: date
    status: str
    district: str
    latitude: float
    longitude: float
    created_at: datetime


# --- Listing Schemas ---
class ListingCreateIn(BaseModel):
    crop_id: str = "banana"
    variety: str
    quantity_kg: float = Field(..., gt=0)
    grade: str = Field(..., description="'A', 'B', or 'C'")
    harvest_date: date
    expected_price_kg: float = Field(..., gt=0)
    district: str
    state: str = "Andhra Pradesh"
    latitude: float
    longitude: float
    media_checklist: dict[str, str] = Field(
        ...,
        description="Fixed 3-photo checklist: {'whole_lot': url, 'close_up': url, 'opened_crate': url}",
    )
    media_captured_at: datetime = Field(
        ..., description="Timestamp of in-app camera capture (must be <= 24h old)"
    )
    media_latitude: float | None = None
    media_longitude: float | None = None


class ListingOut(BaseModel):
    id: int
    farmer_id: int
    crop_id: str
    variety: str
    quantity_kg: float
    grade: str
    grade_description: str
    harvest_date: date
    expected_price_kg: float
    status: str
    district: str
    state: str
    latitude: float
    longitude: float
    media_checklist: dict[str, str]
    media_captured_at: datetime
    created_at: datetime


# --- Offer & Bargaining Schemas ---
class OfferCreateIn(BaseModel):
    listing_id: int
    offered_price_kg: float = Field(..., gt=0)
    quantity_kg: float = Field(..., gt=0)
    buyer_need_id: int | None = None
    notes: str | None = None


class OfferActionIn(BaseModel):
    action: str = Field(..., description="'accept', 'counter', 'reject'")
    counter_price_kg: float | None = None
    confirmed_readback: bool = Field(
        True, description="Explicit confirmation of agreed terms before executing action"
    )


class OfferOut(BaseModel):
    id: int
    listing_id: int
    buyer_id: int
    buyer_name: str
    offered_price_kg: float
    quantity_kg: float
    counter_price_kg: float | None
    counter_by: str | None
    status: str
    notes: str | None
    readback_summary: str
    created_at: datetime


# --- Deal Schemas ---
class DealOut(BaseModel):
    id: int
    offer_id: int
    listing_id: int
    buyer_id: int
    buyer_name: str
    farmer_id: int
    agreed_price_kg: float
    quantity_kg: float
    total_reference_value: float
    status: str
    pickup_otp: str
    deal_date: date
    created_at: datetime
    non_custodial_notice: str = (
        "GrowCircle connects parties directly. We do not hold or process financial payments."
    )


# --- Rating Schemas ---
class RatingCreateIn(BaseModel):
    deal_id: int
    score: int = Field(..., ge=1, le=5)
    reliability_tag: str | None = Field(
        None, description="'prompt_pickup', 'quality_as_described', 'fair_deal', 'delayed_pickup'"
    )
    comment: str | None = None


class RatingOut(BaseModel):
    id: int
    deal_id: int
    rater_id: int
    ratee_id: int
    role: str
    score: int
    reliability_tag: str | None
    comment: str | None
    created_at: datetime


# --- Masked Call Schemas ---
class MaskedCallIn(BaseModel):
    deal_id: int | None = None
    callee_user_id: int


class MaskedCallOut(BaseModel):
    bridge_id: str
    status: str
    message: str


# --- Matching & Group Supply Schemas ---
class BuyerMatchOut(BaseModel):
    buyer_id: int
    business_name: str
    business_type: str
    district: str
    distance_km: float
    reliability_score: float
    has_active_need: bool
    need_quantity_kg: float | None
    match_score: float


class FarmerListingMatchOut(BaseModel):
    listing_id: int
    farmer_id: int
    variety: str
    quantity_kg: float
    grade: str
    expected_price_kg: float
    harvest_date: str
    district: str
    distance_km: float
    match_score: float
    media_checklist: dict[str, str]


class GroupSupplyOut(BaseModel):
    need_id: int
    crop_id: str
    target_quantity_kg: float
    bundled_quantity_kg: float
    is_fully_fulfilled: bool
    farmers_count: int
    weighted_average_price_kg: float
    bundled_listings: list[dict[str, Any]]
