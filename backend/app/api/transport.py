"""
Transport API Router for Phase 4: Transport.
Handles Transporters, Vehicle matching, Guide rates, Trips, OTPs, Disputes, Pooling v1, and Admin verification.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.rate_limit import get_client_ip
from backend.app.db.session import get_async_db
from backend.app.models.transporter import Transporter
from backend.app.models.trip import Trip
from backend.app.models.user import User
from backend.app.services.audit_service import log_security_event
from backend.app.schemas.transport import (
    AvailabilityToggleRequest,
    BuyerDisputeRequest,
    DisputeResolveRequest,
    DriverSuggestionResponse,
    PoolingPlanRequest,
    PoolingPlanResponse,
    TransporterCreate,
    TransporterResponse,
    TripCreateRequest,
    TripRatingCreate,
    TripRatingResponse,
    TripResponse,
    VerifyDeliveryOtpRequest,
    VerifyPickupOtpRequest,
)
from backend.app.services.security import (
    decrypt_document_data,
    encrypt_document_data,
    get_current_user,
    get_optional_current_user,
    require_roles,
)
from backend.app.services.transport_matching import (
    plan_pooled_trips_v1,
    suggest_drivers_for_deal,
)
from backend.app.services.trip_service import (
    add_trip_rating,
    create_trip,
    raise_buyer_delivery_dispute,
    resolve_trip_dispute,
    verify_delivery_otp_and_photo,
    verify_pickup_otp,
)

router = APIRouter(prefix="/transport", tags=["Transport"])


def format_transporter_response(t: Transporter, is_admin: bool = False) -> dict[str, Any]:
    res: dict[str, Any] = {
        "id": t.id,
        "user_id": t.user_id,
        "name": t.name,
        "phone": t.phone,
        "vehicle_type": t.vehicle_type,
        "vehicle_model": t.vehicle_model,
        "capacity_kg": t.capacity_kg,
        "service_area_districts": t.service_area_districts,
        "current_latitude": t.current_latitude,
        "current_longitude": t.current_longitude,
        "is_verified": t.is_verified,
        "available_today": t.available_today,
        "reliability_rating": t.reliability_rating,
        "trips_completed": t.trips_completed,
        "license_expiry": t.license_expiry,
        "rc_expiry": t.rc_expiry,
        "insurance_expiry": t.insurance_expiry,
        "fitness_expiry": t.fitness_expiry,
        "is_compliant": t.is_active_and_compliant(),
        "expired_documents": t.get_expired_documents(),
    }
    if is_admin:
        res["decrypted_license_number"] = decrypt_document_data(t.license_number)
        res["decrypted_rc_number"] = decrypt_document_data(t.rc_number)
    return res


# =====================================================================
# 1. TRANSPORTER REGISTRATION & PROFILE
# =====================================================================

@router.post(
    "/transporters",
    response_model=TransporterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new transporter / driver",
)
async def register_transporter(
    data: TransporterCreate,
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    # Check if transporter already exists for this phone
    stmt = select(Transporter).where(Transporter.phone == data.phone)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transporter with this phone number is already registered.",
        )

    transporter = Transporter(
        user_id=data.user_id,
        name=data.name,
        phone=data.phone,
        license_number=encrypt_document_data(data.license_number),
        license_expiry=data.license_expiry,
        license_photo_url=data.license_photo_url,
        rc_number=encrypt_document_data(data.rc_number),
        rc_expiry=data.rc_expiry,
        rc_photo_url=data.rc_photo_url,
        insurance_expiry=data.insurance_expiry,
        insurance_photo_url=data.insurance_photo_url,
        fitness_expiry=data.fitness_expiry,
        fitness_photo_url=data.fitness_photo_url,
        vehicle_type=data.vehicle_type,
        vehicle_model=data.vehicle_model,
        capacity_kg=data.capacity_kg,
        service_area_districts=data.service_area_districts,
        current_latitude=data.current_latitude,
        current_longitude=data.current_longitude,
        is_verified=False,  # Requires admin verification
        available_today=True,
    )
    db.add(transporter)
    await db.commit()
    await db.refresh(transporter)
    return format_transporter_response(transporter)


@router.get(
    "/transporters/{transporter_id}",
    response_model=TransporterResponse,
    summary="Get transporter details and compliance status",
)
async def get_transporter(
    transporter_id: int,
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    stmt = select(Transporter).where(Transporter.id == transporter_id)
    transporter = (await db.execute(stmt)).scalar_one_or_none()
    if not transporter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transporter not found")
    return format_transporter_response(transporter)


@router.patch(
    "/transporters/{transporter_id}/availability",
    response_model=TransporterResponse,
    summary="Toggle Available Today status for driver",
)
async def toggle_availability(
    transporter_id: int,
    data: AvailabilityToggleRequest,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    stmt = select(Transporter).where(Transporter.id == transporter_id)
    transporter = (await db.execute(stmt)).scalar_one_or_none()
    if not transporter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transporter not found")

    if settings.ENVIRONMENT in ("production", "staging"):
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to update transporter availability",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if current_user.role != "admin" and current_user.id != transporter.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot alter another transporter's status",
            )
    else:
        if current_user and current_user.role != "admin" and current_user.id != transporter.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot alter another transporter's status",
            )

    transporter.available_today = data.available_today
    await db.commit()
    await db.refresh(transporter)
    return format_transporter_response(transporter)


# =====================================================================
# 2. MATCHING & DRIVER SUGGESTIONS
# =====================================================================

@router.get(
    "/suggestions",
    response_model=DriverSuggestionResponse,
    summary="Suggest 3 verified drivers near pickup point matched to load weight",
)
async def get_driver_suggestions(
    pickup_lat: float = Query(..., ge=-90.0, le=90.0),
    pickup_lng: float = Query(..., ge=-180.0, le=180.0),
    dropoff_lat: float = Query(..., ge=-90.0, le=90.0),
    dropoff_lng: float = Query(..., ge=-180.0, le=180.0),
    load_weight_kg: float = Query(..., gt=0.0),
    limit: int = Query(3, ge=1, le=10),
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    return await suggest_drivers_for_deal(
        db=db,
        pickup_lat=pickup_lat,
        pickup_lng=pickup_lng,
        dropoff_lat=dropoff_lat,
        dropoff_lng=dropoff_lng,
        load_weight_kg=load_weight_kg,
        limit=limit,
    )


# =====================================================================
# 3. TRIPS & OTP LIFECYCLE
# =====================================================================

@router.post(
    "/trips",
    response_model=TripResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and assign a trip to a transporter",
)
async def create_new_trip(
    data: TripCreateRequest,
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    stmt = select(Transporter).where(Transporter.id == data.transporter_id)
    transporter = (await db.execute(stmt)).scalar_one_or_none()
    if not transporter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transporter not found")

    if not transporter.is_active_and_compliant():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transporter cannot be assigned trips due to expired documents, unverified status, or unavailable toggle.",
        )

    trip = await create_trip(
        db=db,
        transporter_id=data.transporter_id,
        deal_ids=data.deal_ids,
        vehicle_type=data.vehicle_type,
        total_weight_kg=data.total_weight_kg,
        distance_km=data.distance_km,
        guide_rate=data.guide_rate,
        pickup_latitude=data.pickup_latitude,
        pickup_longitude=data.pickup_longitude,
        dropoff_latitude=data.dropoff_latitude,
        dropoff_longitude=data.dropoff_longitude,
        pickup_address=data.pickup_address,
        dropoff_address=data.dropoff_address,
        actual_freight_agreed=data.actual_freight_agreed,
        is_pooled=data.is_pooled,
    )
    return trip


@router.get(
    "/trips/{trip_id}",
    response_model=TripResponse,
    summary="Get trip details",
)
async def get_trip_details(
    trip_id: int,
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    stmt = select(Trip).where(Trip.id == trip_id)
    trip = (await db.execute(stmt)).scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    return trip


@router.get(
    "/trips/driver/{transporter_id}",
    response_model=list[TripResponse],
    summary="List all trips assigned to a transporter",
)
async def get_driver_trips(
    transporter_id: int,
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    stmt = select(Trip).where(Trip.transporter_id == transporter_id).order_by(Trip.id.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post(
    "/trips/{trip_id}/pickup-otp",
    response_model=TripResponse,
    summary="Driver enters Pickup OTP from farmer to transition trip to in_transit",
)
async def verify_pickup(
    trip_id: int,
    data: VerifyPickupOtpRequest,
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    success, msg, trip = await verify_pickup_otp(
        db=db, trip_id=trip_id, entered_otp=data.pickup_otp
    )
    if not success or not trip:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return trip


@router.post(
    "/trips/{trip_id}/delivery-otp",
    response_model=TripResponse,
    summary="Driver enters Delivery OTP from buyer + photo to complete delivery",
)
async def verify_delivery(
    trip_id: int,
    data: VerifyDeliveryOtpRequest,
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    success, msg, trip = await verify_delivery_otp_and_photo(
        db=db,
        trip_id=trip_id,
        entered_otp=data.delivery_otp,
        delivery_photo_url=data.delivery_photo_url,
    )
    if not success or not trip:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return trip


@router.post(
    "/trips/{trip_id}/dispute",
    response_model=TripResponse,
    summary="Buyer raises complaint with mandatory damage photo at delivery",
)
async def file_delivery_dispute(
    trip_id: int,
    data: BuyerDisputeRequest,
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    success, msg, trip = await raise_buyer_delivery_dispute(
        db=db,
        trip_id=trip_id,
        reason=data.dispute_reason,
        dispute_photo_url=data.dispute_photo_url,
    )
    if not success or not trip:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return trip


@router.post(
    "/trips/{trip_id}/ratings",
    response_model=TripRatingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Mutual ratings between driver, buyer, and farmer",
)
async def submit_trip_rating(
    trip_id: int,
    data: TripRatingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    rater_id = current_user.id
    rating = await add_trip_rating(
        db=db,
        trip_id=trip_id,
        rater_id=rater_id,
        ratee_id=data.ratee_id,
        role=data.role,
        score=data.score,
        tag=data.tag,
        comment=data.comment,
    )
    return rating


# =====================================================================
# 4. POOLING V1 (RULE-BASED)
# =====================================================================

@router.post(
    "/pooling/plan",
    response_model=PoolingPlanResponse,
    summary="Plan pooled trips grouping nearby loads going to the same institution",
)
async def calculate_pooling_plan(
    data: PoolingPlanRequest,
) -> Any:
    deals_raw = [d.dict() for d in data.deals]
    plans_raw = plan_pooled_trips_v1(deals_raw, max_pickup_cluster_km=data.max_pickup_cluster_km)
    pooled_count = sum(1 for p in plans_raw if p["is_pooled"])
    return {
        "plans": plans_raw,
        "total_pooled_plans": pooled_count,
    }


# =====================================================================
# 5. ADMIN VERIFICATION & DISPUTES
# =====================================================================

@router.get(
    "/admin/transporters/pending",
    response_model=list[TransporterResponse],
    summary="Admin queue of transporters awaiting document verification",
    dependencies=[Depends(require_roles(["admin"]))],
)
async def get_pending_transporters(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    stmt = select(Transporter).where(Transporter.is_verified.is_(False)).order_by(Transporter.id.desc())
    result = await db.execute(stmt)
    drivers = result.scalars().all()

    # R6 Requirement 6: Audit log for document view
    if drivers:
        await log_security_event(
            db=db,
            action="DOCUMENT_VIEW",
            user_id=current_user.id,
            actor_role=current_user.role,
            client_ip=get_client_ip(request),
            target_resource="Transporter",
            target_id="pending_queue",
            details=f"Admin viewed documents for {len(drivers)} pending transporter(s)",
            status="SUCCESS",
        )

    return [format_transporter_response(d, is_admin=True) for d in drivers]


@router.post(
    "/admin/transporters/{transporter_id}/verify",
    response_model=TransporterResponse,
    summary="Admin verify or reject transporter",
    dependencies=[Depends(require_roles(["admin"]))],
)
async def admin_verify_transporter(
    transporter_id: int,
    request: Request,
    verify: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    stmt = select(Transporter).where(Transporter.id == transporter_id)
    transporter = (await db.execute(stmt)).scalar_one_or_none()
    if not transporter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transporter not found")

    transporter.is_verified = verify
    await db.commit()
    await db.refresh(transporter)

    # R6 Requirement 6: Audit log for approval or rejection
    action = "APPROVAL" if verify else "REJECTION"
    await log_security_event(
        db=db,
        action=action,
        user_id=current_user.id,
        actor_role=current_user.role,
        client_ip=get_client_ip(request),
        target_resource="Transporter",
        target_id=str(transporter.id),
        details=f"Admin {'approved' if verify else 'rejected'} transporter #{transporter.id} ({transporter.name})",
        status="SUCCESS",
    )

    return format_transporter_response(transporter)


@router.get(
    "/admin/disputes",
    response_model=list[TripResponse],
    summary="Admin list of trips with active buyer disputes",
    dependencies=[Depends(require_roles(["admin"]))],
)
async def get_active_disputes(
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    stmt = select(Trip).where(Trip.status == "disputed").order_by(Trip.id.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post(
    "/admin/disputes/{trip_id}/resolve",
    response_model=TripResponse,
    summary="Admin resolve dispute with mediation notes",
    dependencies=[Depends(require_roles(["admin"]))],
)
async def admin_resolve_dispute(
    trip_id: int,
    data: DisputeResolveRequest,
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    success, msg, trip = await resolve_trip_dispute(
        db=db,
        trip_id=trip_id,
        resolution_notes=data.resolution_notes,
        final_status=data.final_status,
    )
    if not success or not trip:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return trip
