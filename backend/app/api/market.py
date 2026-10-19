"""
FastAPI route handlers for Direct Selling:
Auth, Buyer Verification, Needs, Fresh Produce Listings, Offers, Deals, Ratings, and Masked Calls.
"""

import secrets
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.rate_limit import RateLimitRule, get_client_ip, rate_limit_check
from backend.app.db.session import get_async_db
from backend.app.models.buyer import BuyerProfile
from backend.app.models.buyer_need import BuyerNeed
from backend.app.models.deal import Deal
from backend.app.models.listing import GRADE_DESCRIPTIONS, Listing
from backend.app.models.offer import Offer
from backend.app.models.rating import Rating
from backend.app.models.user import User
from backend.app.schemas.market import (
    AdminBuyerDetailOut,
    AdminVerifyBuyerIn,
    AuthTokenOut,
    BuyerMatchOut,
    BuyerNeedCreateIn,
    BuyerNeedOut,
    BuyerProfileOut,
    BuyerRegisterIn,
    DealOut,
    FarmerListingMatchOut,
    GroupSupplyOut,
    ListingCreateIn,
    ListingOut,
    MaskedCallIn,
    MaskedCallOut,
    OfferActionIn,
    OfferCreateIn,
    OfferOut,
    RatingCreateIn,
    RatingOut,
    SendOtpIn,
    VerifyOtpIn,
)
from backend.app.services.audit_service import log_security_event
from backend.app.services.matching import MatchingService
from backend.app.services.media_validator import ListingValidator, MediaValidationError
from backend.app.services.security import (
    create_access_token,
    decrypt_document_data,
    encrypt_document_data,
    generate_and_send_phone_otp,
    get_current_user,
    get_optional_current_user,
    require_roles,
    verify_phone_otp,
)
from backend.app.services.telephony.ivr_flow import get_telephony_provider

router = APIRouter(tags=["Direct Selling & Marketplace"])


# ============================================================================
# 1. AUTHENTICATION (Phone-OTP & Roles)
# ============================================================================
@router.post("/auth/send-otp", tags=["Auth"])
async def send_otp(payload: SendOtpIn) -> dict[str, str]:
    """Generates and dispatches 6-digit verification OTP."""
    await rate_limit_check("otp", payload.phone, *RateLimitRule.OTP)
    otp = generate_and_send_phone_otp(payload.phone)
    response_payload: dict[str, str] = {"status": "otp_sent", "phone": payload.phone}
    if settings.ENVIRONMENT in ("development", "test") and settings.DEBUG:
        response_payload["sandbox_otp"] = otp
    return response_payload



@router.post("/auth/verify-otp", response_model=AuthTokenOut, tags=["Auth"])
async def verify_otp(
    payload: VerifyOtpIn,
    db: AsyncSession = Depends(get_async_db),
) -> AuthTokenOut:
    """Verifies phone OTP and returns JWT token with role claims."""
    clean_phone = payload.phone.strip().replace(" ", "").replace("+", "")
    is_valid = verify_phone_otp(clean_phone, payload.otp)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP. Please check and try again.",
        )

    user = await db.scalar(select(User).where(User.phone == clean_phone))
    if not user:
        user = User(
            phone=clean_phone,
            role=payload.role,
            language="te",
            consent_at=datetime.now(UTC),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    elif payload.role and payload.role != "farmer" and user.role != payload.role:
        # Update user role if explicitly switching during verified sign-in
        user.role = payload.role
        await db.commit()

    token = create_access_token(user_id=user.id, phone=user.phone, role=user.role)
    return AuthTokenOut(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        phone=user.phone,
        role=user.role,
    )


# ============================================================================
# 2. BUYER & INSTITUTION VERIFICATION
# ============================================================================
@router.post("/buyers/register", response_model=BuyerProfileOut, tags=["Buyers"])
async def register_buyer(
    payload: BuyerRegisterIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> BuyerProfileOut:
    """
    Registers a buyer or institutional profile.
    Encrypts GST and document references at rest (DPDP Act).
    Initial status is 'pending' until admin verification.
    """
    existing = await db.scalar(
        select(BuyerProfile).where(BuyerProfile.user_id == current_user.id)
    )
    if existing:
        raise HTTPException(status_code=400, detail="Buyer profile already exists for this account")

    enc_gst = encrypt_document_data(payload.gst_number)
    enc_doc = encrypt_document_data(payload.document_ref)

    buyer = BuyerProfile(
        user_id=current_user.id,
        business_name=payload.business_name,
        business_type=payload.business_type,
        verification_status="pending",
        encrypted_gst_number=enc_gst,
        encrypted_document_ref=enc_doc,
        address=payload.address,
        district=payload.district,
        state=payload.state,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    # Update user role
    current_user.role = "buyer"
    db.add(buyer)
    await db.commit()
    await db.refresh(buyer)

    return BuyerProfileOut(
        id=buyer.id,
        user_id=buyer.user_id,
        business_name=buyer.business_name,
        business_type=buyer.business_type,
        verification_status=buyer.verification_status,
        reliability_score=buyer.reliability_score,
        deals_completed_count=buyer.deals_completed_count,
        address=buyer.address,
        district=buyer.district,
        state=buyer.state,
        latitude=buyer.latitude,
        longitude=buyer.longitude,
        verified_at=buyer.verified_at,
    )


@router.get("/buyers/me", response_model=BuyerProfileOut, tags=["Buyers"])
async def get_my_buyer_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> BuyerProfileOut:
    """Returns the current buyer's profile."""
    buyer = await db.scalar(select(BuyerProfile).where(BuyerProfile.user_id == current_user.id))
    if not buyer:
        raise HTTPException(status_code=404, detail="No buyer profile registered for this account")

    return BuyerProfileOut(
        id=buyer.id,
        user_id=buyer.user_id,
        business_name=buyer.business_name,
        business_type=buyer.business_type,
        verification_status=buyer.verification_status,
        reliability_score=buyer.reliability_score,
        deals_completed_count=buyer.deals_completed_count,
        address=buyer.address,
        district=buyer.district,
        state=buyer.state,
        latitude=buyer.latitude,
        longitude=buyer.longitude,
        verified_at=buyer.verified_at,
    )


@router.get(
    "/admin/buyers/pending",
    response_model=list[AdminBuyerDetailOut],
    dependencies=[Depends(require_roles(["admin"]))],
    tags=["Admin"],
)
async def list_pending_buyer_verifications(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> list[AdminBuyerDetailOut]:
    """Admin queue: Lists pending buyer registrations with decrypted proofs."""
    stmt = (
        select(BuyerProfile)
        .where(BuyerProfile.verification_status == "pending")
        .order_by(BuyerProfile.created_at.asc())
    )
    result = await db.execute(stmt)
    buyers = result.scalars().all()

    # R6 Requirement 6: Audit log for document view
    if buyers:
        await log_security_event(
            db=db,
            action="DOCUMENT_VIEW",
            user_id=current_user.id,
            actor_role=current_user.role,
            client_ip=get_client_ip(request),
            target_resource="BuyerProfile",
            target_id="pending_queue",
            details=f"Admin viewed decrypted documents for {len(buyers)} pending buyer(s)",
            status="SUCCESS",
        )

    output = []
    for b in buyers:
        dec_gst = decrypt_document_data(b.encrypted_gst_number or "")
        dec_doc = decrypt_document_data(b.encrypted_document_ref or "")
        output.append(
            AdminBuyerDetailOut(
                id=b.id,
                user_id=b.user_id,
                business_name=b.business_name,
                business_type=b.business_type,
                verification_status=b.verification_status,
                reliability_score=b.reliability_score,
                deals_completed_count=b.deals_completed_count,
                address=b.address,
                district=b.district,
                state=b.state,
                latitude=b.latitude,
                longitude=b.longitude,
                verified_at=b.verified_at,
                decrypted_gst_number=dec_gst,
                decrypted_document_ref=dec_doc,
                verification_notes=b.verification_notes,
            )
        )
    return output


@router.post(
    "/admin/buyers/{buyer_id}/verify",
    response_model=BuyerProfileOut,
    dependencies=[Depends(require_roles(["admin"]))],
    tags=["Admin"],
)
async def verify_or_reject_buyer(
    buyer_id: int,
    payload: AdminVerifyBuyerIn,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> BuyerProfileOut:
    """Admin action: Approves ('verified') or rejects ('rejected') buyer registration."""
    buyer = await db.scalar(select(BuyerProfile).where(BuyerProfile.id == buyer_id))
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer profile not found")

    decision = payload.decision.lower().strip()
    if decision not in ["verified", "rejected"]:
        raise HTTPException(status_code=400, detail="Decision must be 'verified' or 'rejected'")

    buyer.verification_status = decision
    buyer.verification_notes = payload.notes
    if decision == "verified":
        buyer.verified_at = datetime.now(UTC)
        buyer.verified_by_admin_id = current_user.id

    await db.commit()
    await db.refresh(buyer)

    # R6 Requirement 6: Audit log for approval or rejection
    action = "APPROVAL" if decision == "verified" else "REJECTION"
    await log_security_event(
        db=db,
        action=action,
        user_id=current_user.id,
        actor_role=current_user.role,
        client_ip=get_client_ip(request),
        target_resource="BuyerProfile",
        target_id=str(buyer.id),
        details=f"Admin {decision} buyer #{buyer.id} ({buyer.business_name})",
        status="SUCCESS",
    )

    return BuyerProfileOut(
        id=buyer.id,
        user_id=buyer.user_id,
        business_name=buyer.business_name,
        business_type=buyer.business_type,
        verification_status=buyer.verification_status,
        reliability_score=buyer.reliability_score,
        deals_completed_count=buyer.deals_completed_count,
        address=buyer.address,
        district=buyer.district,
        state=buyer.state,
        latitude=buyer.latitude,
        longitude=buyer.longitude,
        verified_at=buyer.verified_at,
    )


# ============================================================================
# 3. BUYER NEEDS & INSTITUTIONAL DEMAND
# ============================================================================
@router.post("/needs", response_model=BuyerNeedOut, tags=["Needs"])
async def create_buyer_need(
    payload: BuyerNeedCreateIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> BuyerNeedOut:
    """Creates a weekly, daily, or one-time institutional crop need."""
    buyer = await db.scalar(select(BuyerProfile).where(BuyerProfile.user_id == current_user.id))
    if not buyer:
        raise HTTPException(status_code=403, detail="Only registered buyers can post needs")

    need = BuyerNeed(
        buyer_id=buyer.id,
        crop_id=payload.crop_id.lower().strip(),
        quantity_kg=payload.quantity_kg,
        frequency=payload.frequency,
        preferred_grade=payload.preferred_grade.upper().strip(),
        target_price_kg=payload.target_price_kg,
        start_date=payload.start_date,
        district=payload.district,
        latitude=payload.latitude,
        longitude=payload.longitude,
        status="active",
    )
    db.add(need)
    await db.commit()
    await db.refresh(need)

    return BuyerNeedOut(
        id=need.id,
        buyer_id=need.buyer_id,
        business_name=buyer.business_name,
        crop_id=need.crop_id,
        quantity_kg=need.quantity_kg,
        frequency=need.frequency,
        preferred_grade=need.preferred_grade,
        target_price_kg=need.target_price_kg,
        start_date=need.start_date,
        status=need.status,
        district=need.district,
        latitude=need.latitude,
        longitude=need.longitude,
        created_at=need.created_at,
    )


@router.get("/needs", response_model=list[BuyerNeedOut], tags=["Needs"])
async def list_buyer_needs(
    crop: str | None = None,
    district: str | None = None,
    db: AsyncSession = Depends(get_async_db),
) -> list[BuyerNeedOut]:
    """Lists active buyer requirements across institutions."""
    stmt = (
        select(BuyerNeed, BuyerProfile)
        .join(BuyerProfile, BuyerNeed.buyer_id == BuyerProfile.id)
        .where(BuyerNeed.status == "active")
    )
    if crop:
        stmt = stmt.where(BuyerNeed.crop_id == crop.lower().strip())
    if district:
        stmt = stmt.where(func.lower(BuyerNeed.district) == district.lower().strip())

    stmt = stmt.order_by(desc(BuyerNeed.created_at))
    result = await db.execute(stmt)
    rows = result.all()

    return [
        BuyerNeedOut(
            id=need.id,
            buyer_id=need.buyer_id,
            business_name=buyer.business_name,
            crop_id=need.crop_id,
            quantity_kg=need.quantity_kg,
            frequency=need.frequency,
            preferred_grade=need.preferred_grade,
            target_price_kg=need.target_price_kg,
            start_date=need.start_date,
            status=need.status,
            district=need.district,
            latitude=need.latitude,
            longitude=need.longitude,
            created_at=need.created_at,
        )
        for need, buyer in rows
    ]


@router.get(
    "/needs/{need_id}/matched-farmers",
    response_model=list[FarmerListingMatchOut],
    tags=["Matching"],
)
async def get_matched_farmers_for_need(
    need_id: int,
    db: AsyncSession = Depends(get_async_db),
) -> list[FarmerListingMatchOut]:
    """Finds and ranks individual farmer listings within 50 km for this need."""
    need = await db.scalar(select(BuyerNeed).where(BuyerNeed.id == need_id))
    if not need:
        raise HTTPException(status_code=404, detail="Buyer need not found")

    matches = await MatchingService.match_farmers_for_buyer_need(
        db=db, need=need, max_distance_km=50.0
    )
    return [FarmerListingMatchOut(**m) for m in matches]


@router.get(
    "/needs/{need_id}/group-supply",
    response_model=GroupSupplyOut,
    tags=["Matching"],
)
async def get_group_supply_aggregation(
    need_id: int,
    db: AsyncSession = Depends(get_async_db),
) -> GroupSupplyOut:
    """Aggregates supply from multiple neighboring farmers within 50 km to meet bulk demand."""
    need = await db.scalar(select(BuyerNeed).where(BuyerNeed.id == need_id))
    if not need:
        raise HTTPException(status_code=404, detail="Buyer need not found")

    bundled = await MatchingService.aggregate_group_supply(
        db=db, need=need, max_distance_km=50.0
    )
    return GroupSupplyOut(**bundled)


# ============================================================================
# 4. FARMER PRODUCE LISTINGS
# ============================================================================
@router.post("/listings", response_model=ListingOut, tags=["Listings"])
async def create_listing(
    payload: ListingCreateIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> ListingOut:
    """
    Creates a farmer produce listing.
    Strictly validates:
    - In-app photo freshness (must be captured within past 24 hours).
    - Fixed 3-photo checklist: whole_lot, close_up, opened_crate.
    - Grade: A, B, or C with human descriptions.
    """
    try:
        ListingValidator.validate_listing_payload(
            media_checklist=payload.media_checklist,
            media_captured_at=payload.media_captured_at,
            harvest_date=payload.harvest_date,
            grade=payload.grade,
            expected_price_kg=payload.expected_price_kg,
            quantity_kg=payload.quantity_kg,
        )
    except MediaValidationError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err)) from val_err

    clean_grade = payload.grade.upper().strip()
    listing = Listing(
        farmer_id=current_user.id,
        crop_id=payload.crop_id.lower().strip(),
        variety=payload.variety,
        quantity_kg=payload.quantity_kg,
        grade=clean_grade,
        harvest_date=payload.harvest_date,
        expected_price_kg=payload.expected_price_kg,
        district=payload.district,
        state=payload.state,
        latitude=payload.latitude,
        longitude=payload.longitude,
        media_checklist=payload.media_checklist,
        media_captured_at=payload.media_captured_at,
        media_latitude=payload.media_latitude,
        media_longitude=payload.media_longitude,
        status="active",
    )
    db.add(listing)
    await db.commit()
    await db.refresh(listing)

    return ListingOut(
        id=listing.id,
        farmer_id=listing.farmer_id,
        crop_id=listing.crop_id,
        variety=listing.variety,
        quantity_kg=listing.quantity_kg,
        grade=listing.grade,
        grade_description=GRADE_DESCRIPTIONS.get(listing.grade, ""),
        harvest_date=listing.harvest_date,
        expected_price_kg=listing.expected_price_kg,
        status=listing.status,
        district=listing.district,
        state=listing.state,
        latitude=listing.latitude,
        longitude=listing.longitude,
        media_checklist=listing.media_checklist,
        media_captured_at=listing.media_captured_at,
        created_at=listing.created_at,
    )


@router.get("/listings", response_model=list[ListingOut], tags=["Listings"])
async def list_listings(
    crop: str | None = None,
    district: str | None = None,
    grade: str | None = None,
    db: AsyncSession = Depends(get_async_db),
) -> list[ListingOut]:
    """Lists active farmer produce listings."""
    stmt = select(Listing).where(Listing.status == "active")
    if crop:
        stmt = stmt.where(Listing.crop_id == crop.lower().strip())
    if district:
        stmt = stmt.where(func.lower(Listing.district) == district.lower().strip())
    if grade:
        stmt = stmt.where(Listing.grade == grade.upper().strip())

    stmt = stmt.order_by(desc(Listing.created_at))
    result = await db.execute(stmt)
    listings = result.scalars().all()

    return [
        ListingOut(
            id=listing_obj.id,
            farmer_id=listing_obj.farmer_id,
            crop_id=listing_obj.crop_id,
            variety=listing_obj.variety,
            quantity_kg=listing_obj.quantity_kg,
            grade=listing_obj.grade,
            grade_description=GRADE_DESCRIPTIONS.get(listing_obj.grade, ""),
            harvest_date=listing_obj.harvest_date,
            expected_price_kg=listing_obj.expected_price_kg,
            status=listing_obj.status,
            district=listing_obj.district,
            state=listing_obj.state,
            latitude=listing_obj.latitude,
            longitude=listing_obj.longitude,
            media_checklist=listing_obj.media_checklist,
            media_captured_at=listing_obj.media_captured_at,
            created_at=listing_obj.created_at,
        )
        for listing_obj in listings
    ]


@router.get(
    "/listings/{listing_id}/matched-buyers",
    response_model=list[BuyerMatchOut],
    tags=["Matching"],
)
async def get_matched_buyers_for_listing(
    listing_id: int,
    db: AsyncSession = Depends(get_async_db),
) -> list[BuyerMatchOut]:
    """Finds nearby verified buyers ranked by distance, quantity, and reliability."""
    listing = await db.scalar(select(Listing).where(Listing.id == listing_id))
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    matches = await MatchingService.match_buyers_for_listing(
        db=db, listing=listing, max_distance_km=50.0
    )
    return [BuyerMatchOut(**m) for m in matches]


# ============================================================================
# 5. OFFERS, NEGOTIATIONS, & DEALS
# ============================================================================
@router.post("/offers", response_model=OfferOut, tags=["Offers"])
async def create_offer(
    payload: OfferCreateIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> OfferOut:
    """Buyer places an offer on a farmer's produce listing."""
    buyer = await db.scalar(select(BuyerProfile).where(BuyerProfile.user_id == current_user.id))
    if not buyer:
        raise HTTPException(status_code=403, detail="Only registered buyers can make offers")

    if buyer.verification_status != "verified":
        raise HTTPException(
            status_code=403,
            detail="Your buyer account is pending admin verification. Offers unlock once verified.",
        )

    listing = await db.scalar(select(Listing).where(Listing.id == payload.listing_id))
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.status != "active":
        raise HTTPException(status_code=400, detail="This listing is no longer active")

    offer = Offer(
        listing_id=listing.id,
        buyer_id=buyer.id,
        buyer_need_id=payload.buyer_need_id,
        offered_price_kg=payload.offered_price_kg,
        quantity_kg=payload.quantity_kg,
        notes=payload.notes,
        status="pending",
    )
    db.add(offer)
    await db.commit()
    await db.refresh(offer)

    readback = (
        f"Offer: {buyer.business_name} offered ₹{offer.offered_price_kg:.2f}/kg "
        f"for {offer.quantity_kg:.0f} kg {listing.crop_id.capitalize()}."
    )

    return OfferOut(
        id=offer.id,
        listing_id=offer.listing_id,
        buyer_id=offer.buyer_id,
        buyer_name=buyer.business_name,
        offered_price_kg=offer.offered_price_kg,
        quantity_kg=offer.quantity_kg,
        counter_price_kg=offer.counter_price_kg,
        counter_by=offer.counter_by,
        status=offer.status,
        notes=offer.notes,
        readback_summary=readback,
        created_at=offer.created_at,
    )


@router.post("/offers/{offer_id}/action", response_model=dict[str, Any], tags=["Offers"])
async def act_on_offer(
    offer_id: int,
    payload: OfferActionIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """
    Accepts, counters, or rejects an offer with explicit read-back confirmation.
    Accepting automatically confirms a Deal and issues a 4-digit pickup OTP.
    """
    stmt = (
        select(Offer, Listing, BuyerProfile)
        .join(Listing, Offer.listing_id == Listing.id)
        .join(BuyerProfile, Offer.buyer_id == BuyerProfile.id)
        .where(Offer.id == offer_id)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Offer not found")

    offer, listing, buyer = row

    if current_user.role != "admin" and current_user.id not in (listing.farmer_id, buyer.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only parties to this offer may take action.",
        )

    if not payload.confirmed_readback:
        raise HTTPException(
            status_code=400,
            detail="Read-back confirmation required before executing agreement.",
        )

    action = payload.action.lower().strip()

    # 1. COUNTER OFFER
    if action == "counter":
        if not payload.counter_price_kg or payload.counter_price_kg <= 0:
            raise HTTPException(status_code=400, detail="Valid counter price per kg required")
        offer.status = "countered"
        offer.counter_price_kg = payload.counter_price_kg
        offer.counter_by = "farmer" if current_user.id == listing.farmer_id else "buyer"
        await db.commit()
        return {
            "status": "countered",
            "offer_id": offer.id,
            "counter_price_kg": offer.counter_price_kg,
            "message": f"Counter-offer of ₹{offer.counter_price_kg:.2f}/kg recorded.",
        }

    # 2. REJECT OFFER
    elif action == "reject":
        offer.status = "rejected"
        await db.commit()
        return {"status": "rejected", "offer_id": offer.id, "message": "Offer declined."}

    # 3. ACCEPT OFFER -> CREATES DEAL
    elif action == "accept":
        agreed_price = offer.counter_price_kg or offer.offered_price_kg
        offer.status = "accepted"

        # Generate 4-digit pickup OTP
        otp = f"{secrets.randbelow(9000) + 1000}"
        ref_val = round(agreed_price * offer.quantity_kg, 2)

        deal = Deal(
            offer_id=offer.id,
            listing_id=listing.id,
            buyer_id=buyer.id,
            farmer_id=listing.farmer_id,
            agreed_price_kg=agreed_price,
            quantity_kg=offer.quantity_kg,
            total_reference_value=ref_val,
            status="confirmed",
            pickup_otp=otp,
            deal_date=datetime.now(UTC).date(),
        )

        listing.status = "reserved"
        db.add(deal)
        await db.commit()
        await db.refresh(deal)

        return {
            "status": "accepted",
            "deal_id": deal.id,
            "agreed_price_kg": deal.agreed_price_kg,
            "quantity_kg": deal.quantity_kg,
            "pickup_otp": deal.pickup_otp,
            "message": f"Deal confirmed! Handover OTP is {deal.pickup_otp}. No advance payments held by GrowCircle.",
        }

    raise HTTPException(status_code=400, detail="Invalid action: choose 'accept', 'counter', or 'reject'")


@router.get("/deals", response_model=list[DealOut], tags=["Deals"])
async def list_deals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> list[DealOut]:
    """Lists deals associated with current user (farmer or buyer)."""
    stmt = (
        select(Deal, BuyerProfile)
        .join(BuyerProfile, Deal.buyer_id == BuyerProfile.id)
        .where((Deal.farmer_id == current_user.id) | (BuyerProfile.user_id == current_user.id))
        .order_by(desc(Deal.created_at))
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        DealOut(
            id=d.id,
            offer_id=d.offer_id,
            listing_id=d.listing_id,
            buyer_id=d.buyer_id,
            buyer_name=buyer.business_name,
            farmer_id=d.farmer_id,
            agreed_price_kg=d.agreed_price_kg,
            quantity_kg=d.quantity_kg,
            total_reference_value=d.total_reference_value,
            status=d.status,
            pickup_otp=d.pickup_otp,
            deal_date=d.deal_date,
            created_at=d.created_at,
        )
        for d, buyer in rows
    ]


@router.post("/deals/{deal_id}/complete", tags=["Deals"])
async def complete_deal_handover(
    deal_id: int,
    otp: Annotated[str, Query(description="4-digit pickup OTP presented by driver/buyer")],
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """Verifies pickup OTP and marks deal as completed."""
    # Rate limit OTP brute force attempts: max 5 attempts per 5 minutes per deal
    await rate_limit_check("deal_handover_otp", f"deal_{deal_id}", 5, 300)

    deal = await db.scalar(select(Deal).where(Deal.id == deal_id))
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    buyer = await db.scalar(select(BuyerProfile).where(BuyerProfile.id == deal.buyer_id))

    if settings.ENVIRONMENT in ("production", "staging"):
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to complete deal handover",
                headers={"WWW-Authenticate": "Bearer"},
            )
        is_party = (
            current_user.id == deal.farmer_id
            or (buyer and current_user.id == buyer.user_id)
            or current_user.role in ("admin", "driver", "transporter")
        )
        if not is_party:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not authorized to complete this deal handover",
            )
    else:
        if current_user and current_user.role != "admin":
            is_party = (
                current_user.id == deal.farmer_id
                or (buyer and current_user.id == buyer.user_id)
                or current_user.role in ("driver", "transporter")
            )
            if not is_party:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You are not authorized to complete this deal handover",
                )

    if deal.pickup_otp != otp.strip():
        raise HTTPException(status_code=400, detail="Invalid pickup OTP. Handover denied.")

    deal.status = "completed"
    deal.completed_at = datetime.now(UTC)

    # Increment buyer completed deals count
    if buyer:
        buyer.deals_completed_count += 1

    await db.commit()
    return {"status": "completed", "message": "Pickup verified and deal marked complete!"}


# ============================================================================
# 6. RATINGS & MUTUAL PEER REVIEWS
# ============================================================================
@router.post("/ratings", response_model=RatingOut, tags=["Ratings"])
async def create_rating(
    payload: RatingCreateIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> RatingOut:
    """Submits mutual post-deal rating (1 to 5 stars) and updates reliability score."""
    deal = await db.scalar(select(Deal).where(Deal.id == payload.deal_id))
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    buyer = await db.scalar(select(BuyerProfile).where(BuyerProfile.id == deal.buyer_id))
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer profile not found")

    if current_user.id == deal.farmer_id:
        role = "farmer_to_buyer"
        ratee_id = buyer.user_id
    elif current_user.id == buyer.user_id:
        role = "buyer_to_farmer"
        ratee_id = deal.farmer_id
    else:
        raise HTTPException(status_code=403, detail="Only parties to the deal may rate")

    rating = Rating(
        deal_id=deal.id,
        rater_id=current_user.id,
        ratee_id=ratee_id,
        role=role,
        score=payload.score,
        reliability_tag=payload.reliability_tag,
        comment=payload.comment,
    )
    db.add(rating)

    # If rating the buyer, recalculate buyer reliability score
    if role == "farmer_to_buyer":
        # Average all buyer scores
        avg_score = await db.scalar(
            select(func.avg(Rating.score)).where(
                Rating.ratee_id == buyer.user_id,
                Rating.role == "farmer_to_buyer",
            )
        )
        if avg_score:
            buyer.reliability_score = round(float(avg_score), 1)

    await db.commit()
    await db.refresh(rating)

    return RatingOut(
        id=rating.id,
        deal_id=rating.deal_id,
        rater_id=rating.rater_id,
        ratee_id=rating.ratee_id,
        role=rating.role,
        score=rating.score,
        reliability_tag=rating.reliability_tag,
        comment=rating.comment,
        created_at=rating.created_at,
    )


# ============================================================================
# 7. MASKED CALL CONNECTION
# ============================================================================
@router.post("/telephony/masked-call", response_model=MaskedCallOut, tags=["Telephony"])
async def trigger_masked_call(
    payload: MaskedCallIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> MaskedCallOut:
    """
    Bridges a phone call between caller and counterparty via a proxy virtual DID.
    Preserves privacy under the DPDP Act.
    """
    callee = await db.scalar(select(User).where(User.id == payload.callee_user_id))
    if not callee:
        raise HTTPException(status_code=404, detail="Callee user not found")

    telephony = get_telephony_provider()
    bridge_id = await telephony.initiate_masked_call(
        caller_phone=current_user.phone,
        callee_phone=callee.phone,
        context_id=f"deal-{payload.deal_id}" if payload.deal_id else "direct-negotiation",
    )

    return MaskedCallOut(
        bridge_id=bridge_id,
        status="connecting",
        message="Masked call connecting through GrowCircle virtual proxy. Your personal number remains private.",
    )
