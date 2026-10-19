"""
Trip Lifecycle Service:
Manages trip assignment, pickup OTP verification, delivery OTP & photo verification,
dispute filing with photo, mutual ratings, and admin dispute resolution.
Phase 4: Transport.
"""

import secrets
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.transporter import Transporter
from backend.app.models.trip import Trip
from backend.app.models.trip_rating import TripRating


def generate_numeric_otp(length: int = 4) -> str:
    """Generates a cryptographically secure numeric OTP."""
    digits = [str(secrets.randbelow(10)) for _ in range(length)]
    return "".join(digits)



async def create_trip(
    db: AsyncSession,
    transporter_id: int,
    deal_ids: list[int],
    vehicle_type: str,
    total_weight_kg: float,
    distance_km: float,
    guide_rate: float,
    pickup_latitude: float,
    pickup_longitude: float,
    dropoff_latitude: float,
    dropoff_longitude: float,
    pickup_address: str | None = None,
    dropoff_address: str | None = None,
    actual_freight_agreed: float | None = None,
    is_pooled: bool = False,
) -> Trip:
    """Creates a new assigned trip with pickup and delivery OTPs."""
    p_otp = generate_numeric_otp(4)
    d_otp = generate_numeric_otp(4)

    primary_deal_id = deal_ids[0] if deal_ids else None

    trip = Trip(
        transporter_id=transporter_id,
        deal_id=primary_deal_id,
        deal_ids=deal_ids,
        status="assigned",
        vehicle_type=vehicle_type,
        total_weight_kg=total_weight_kg,
        distance_km=distance_km,
        guide_rate=guide_rate,
        actual_freight_agreed=actual_freight_agreed,
        pickup_otp=p_otp,
        delivery_otp=d_otp,
        pickup_latitude=pickup_latitude,
        pickup_longitude=pickup_longitude,
        pickup_address=pickup_address,
        dropoff_latitude=dropoff_latitude,
        dropoff_longitude=dropoff_longitude,
        dropoff_address=dropoff_address,
        is_pooled=is_pooled,
    )
    db.add(trip)
    await db.commit()
    await db.refresh(trip)
    return trip


async def verify_pickup_otp(
    db: AsyncSession,
    trip_id: int,
    entered_otp: str,
) -> tuple[bool, str, Trip | None]:
    """
    Verifies the pickup OTP shared by the farmer when loading produce into vehicle.
    On success: transitions trip status to 'in_transit'.
    """
    stmt = select(Trip).where(Trip.id == trip_id)
    result = await db.execute(stmt)
    trip = result.scalar_one_or_none()

    if not trip:
        return False, "Trip not found", None

    if trip.status not in ["assigned", "arrived_pickup"]:
        return False, f"Trip is already in '{trip.status}' status", trip

    if trip.pickup_otp != entered_otp.strip():
        return False, "Invalid pickup OTP. Please verify with the farmer.", trip

    trip.status = "in_transit"
    trip.pickup_confirmed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(trip)
    return True, "Pickup verified! Produce is now in transit.", trip


async def verify_delivery_otp_and_photo(
    db: AsyncSession,
    trip_id: int,
    entered_otp: str,
    delivery_photo_url: str,
) -> tuple[bool, str, Trip | None]:
    """
    Verifies the delivery OTP shared by the buyer upon unloading crates at destination,
    requiring a proof photo of unloaded produce.
    On success: transitions trip status to 'delivered' and increments transporter trips count.
    """
    if not delivery_photo_url or not delivery_photo_url.strip():
        return False, "Delivery photo is required as physical proof of unloaded produce.", None

    stmt = select(Trip).where(Trip.id == trip_id)
    result = await db.execute(stmt)
    trip = result.scalar_one_or_none()

    if not trip:
        return False, "Trip not found", None

    if trip.status != "in_transit":
        return False, f"Cannot complete delivery for trip in '{trip.status}' status", trip

    if trip.delivery_otp != entered_otp.strip():
        return False, "Invalid delivery OTP. Please verify with the buyer/kitchen manager.", trip

    trip.status = "delivered"
    trip.delivery_confirmed_at = datetime.now(UTC)
    trip.delivery_photo_url = delivery_photo_url.strip()

    # Update Transporter trip stats
    trans_stmt = select(Transporter).where(Transporter.id == trip.transporter_id)
    trans_res = await db.execute(trans_stmt)
    transporter = trans_res.scalar_one_or_none()
    if transporter:
        transporter.trips_completed += 1

    await db.commit()
    await db.refresh(trip)
    return True, "Delivery verified and produce accepted!", trip


async def raise_buyer_delivery_dispute(
    db: AsyncSession,
    trip_id: int,
    reason: str,
    dispute_photo_url: str,
) -> tuple[bool, str, Trip | None]:
    """
    Allows a buyer to register a complaint if produce arrives damaged/spoiled in transit.
    Mandatory proof photo required.
    Transitions trip status to 'disputed'.
    """
    if not dispute_photo_url or not dispute_photo_url.strip():
        return False, "A photo of the damaged or spoiled crates is mandatory to file a dispute.", None

    stmt = select(Trip).where(Trip.id == trip_id)
    result = await db.execute(stmt)
    trip = result.scalar_one_or_none()

    if not trip:
        return False, "Trip not found", None

    trip.status = "disputed"
    trip.buyer_dispute_reason = reason.strip()
    trip.buyer_dispute_photo_url = dispute_photo_url.strip()
    await db.commit()
    await db.refresh(trip)
    return True, "Dispute registered. Our dispute desk will review the evidence.", trip


async def resolve_trip_dispute(
    db: AsyncSession,
    trip_id: int,
    resolution_notes: str,
    final_status: str = "delivered",
) -> tuple[bool, str, Trip | None]:
    """
    Admin action to resolve a dispute with notes.
    """
    stmt = select(Trip).where(Trip.id == trip_id)
    result = await db.execute(stmt)
    trip = result.scalar_one_or_none()

    if not trip:
        return False, "Trip not found", None

    trip.status = final_status
    trip.dispute_resolved_at = datetime.now(UTC)
    trip.dispute_resolution_notes = resolution_notes.strip()
    await db.commit()
    await db.refresh(trip)
    return True, "Dispute resolved successfully.", trip


async def add_trip_rating(
    db: AsyncSession,
    trip_id: int,
    rater_id: int,
    ratee_id: int,
    role: str,
    score: int,
    tag: str | None = None,
    comment: str | None = None,
) -> TripRating:
    """
    Adds a mutual rating for a completed trip.
    Updates the Transporter reliability score if driver is being rated.
    """
    rating = TripRating(
        trip_id=trip_id,
        rater_id=rater_id,
        ratee_id=ratee_id,
        role=role,
        score=score,
        tag=tag,
        comment=comment,
    )
    db.add(rating)

    # If rating driver, recalculate driver reliability rating
    if role in ["farmer_to_driver", "buyer_to_driver"]:
        trip_stmt = select(Trip).where(Trip.id == trip_id)
        trip_res = await db.execute(trip_stmt)
        trip = trip_res.scalar_one_or_none()
        if trip:
            trans_stmt = select(Transporter).where(Transporter.id == trip.transporter_id)
            trans_res = await db.execute(trans_stmt)
            transporter = trans_res.scalar_one_or_none()
            if transporter:
                # Weighted running average (0.85 prior + 0.15 current)
                transporter.reliability_rating = round(
                    (transporter.reliability_rating * 0.85) + (float(score) * 0.15), 2
                )

    await db.commit()
    await db.refresh(rating)
    return rating
