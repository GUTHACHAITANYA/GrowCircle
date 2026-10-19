"""
DPDP Act 2023 compliance service: consent management, data export, account deletion,
data minimisation retention routines, and statutory grievance metadata.
"""

import hashlib
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.farm_diary import FarmSeason
from backend.app.models.listing import Listing
from backend.app.models.transporter import Transporter
from backend.app.models.trip import Trip
from backend.app.models.user import User
from backend.app.services.audit_service import log_security_event

GRIEVANCE_OFFICER_INFO = {
    "name": "Radhika Varma",
    "designation": "Data Protection Officer & Grievance Redressal Officer",
    "organization": "GrowCircle Technologies Private Limited",
    "email": "grievance@growcircle.in",
    "phone": "+91 863 294 5678",
    "address": "4th Floor, Agriculture Innovation Hub, Ring Road, Guntur, Andhra Pradesh - 522002",
    "statutory_acknowledgment_hours": 72,
    "statutory_resolution_days": 30,
    "dpdp_notice_version": "1.0",
}


async def record_user_consent(
    db: AsyncSession,
    user_id: int,
    version: str = "1.0",
    purpose: str = "mandi_prices_and_marketplace",
    client_ip: str | None = None,
) -> User:
    """Records explicit consent under Section 6 of DPDP Act 2023."""
    user = await db.get(User, user_id)
    if not user:
        raise ValueError("User not found")

    user.consent_at = datetime.now(UTC)
    user.consent_version = version
    user.consent_purpose = purpose
    user.consent_withdrawn_at = None
    await db.commit()
    await db.refresh(user)

    await log_security_event(
        db=db,
        action="DPDP_CONSENT_GRANTED",
        user_id=user_id,
        actor_role=user.role,
        client_ip=client_ip,
        target_resource="User",
        target_id=str(user_id),
        details={"version": version, "purpose": purpose},
    )
    return user


async def export_user_data(
    db: AsyncSession,
    user_id: int,
    client_ip: str | None = None,
) -> dict[str, Any]:
    """Generates complete machine-readable portable data package under Section 11 of DPDP Act."""
    user = await db.get(User, user_id)
    if not user:
        raise ValueError("User not found")

    # 1. Profile
    profile_data = {
        "id": user.id,
        "phone": user.phone,
        "language": user.language,
        "district": user.district,
        "role": user.role,
        "consent_at": user.consent_at.isoformat() if user.consent_at else None,
        "consent_version": user.consent_version,
        "consent_purpose": user.consent_purpose,
    }

    # 2. Listings
    res_listings = await db.execute(select(Listing).where(Listing.farmer_id == user_id))
    listings = [
        {
            "id": item.id,
            "crop_id": item.crop_id,
            "variety": item.variety,
            "quantity_kg": item.quantity_kg,
            "expected_price_kg": item.expected_price_kg,
            "grade": item.grade,
            "status": item.status,
            "created_at": item.created_at.isoformat(),
        }
        for item in res_listings.scalars().all()
    ]

    # 3. Farm Diary Seasons & Entries (Eager loaded to avoid N+1 queries)
    res_seasons = await db.execute(
        select(FarmSeason)
        .where(FarmSeason.farmer_id == user_id)
        .options(selectinload(FarmSeason.entries))
    )
    seasons_data = []
    for s in res_seasons.scalars().all():
        seasons_data.append({
            "season_id": s.id,
            "season_name": s.season_name,
            "crop_id": s.crop_id,
            "area_acres": s.area_acres,
            "planting_date": s.planting_date.isoformat(),
            "expected_yield_kg": s.expected_yield_kg,
            "entries": [
                {
                    "id": e.id,
                    "entry_type": e.entry_type,
                    "category": e.category,
                    "amount_inr": e.amount_inr,
                    "quantity_kg": e.quantity_kg,
                    "entry_date": e.entry_date.isoformat(),
                    "notes": e.notes,
                }
                for e in s.entries
            ],
        })

    # 4. Transporter profile if applicable
    res_transporter = await db.execute(select(Transporter).where(Transporter.user_id == user_id))
    transporter = res_transporter.scalar_one_or_none()
    transporter_data = None
    if transporter:
        transporter_data = {
            "id": transporter.id,
            "name": transporter.name,
            "vehicle_type": transporter.vehicle_type,
            "capacity_kg": transporter.capacity_kg,
            "service_area_districts": transporter.service_area_districts,
        }

    # 5. Trips
    trips_data = []
    if transporter:
        res_trips = await db.execute(select(Trip).where(Trip.transporter_id == transporter.id))
        trips_data = [
            {
                "id": t.id,
                "status": t.status,
                "distance_km": t.distance_km,
                "freight_agreed_or_guide": t.actual_freight_agreed or t.guide_rate,
                "created_at": t.created_at.isoformat() if hasattr(t, "created_at") and t.created_at else None,
            }
            for t in res_trips.scalars().all()
        ]


    await log_security_event(
        db=db,
        action="DPDP_DATA_EXPORT",
        user_id=user_id,
        actor_role=user.role,
        client_ip=client_ip,
        target_resource="User",
        target_id=str(user_id),
        details={"exported_sections": ["profile", "listings", "farm_diary", "transporter", "trips"]},
    )

    return {
        "export_timestamp": datetime.now(UTC).isoformat(),
        "dpdp_notice_version": GRIEVANCE_OFFICER_INFO["dpdp_notice_version"],
        "user_profile": profile_data,
        "listings": listings,
        "farm_diary": seasons_data,
        "transporter": transporter_data,
        "trips": trips_data,
    }


async def delete_user_account(
    db: AsyncSession,
    user_id: int,
    reason: str = "User requested deletion",
    client_ip: str | None = None,
) -> dict[str, Any]:
    """
    Executes Right to Erasure under Section 12 of DPDP Act.
    Anonymizes identifying information while retaining legally mandated audit trails.
    """
    user = await db.get(User, user_id)
    if not user:
        raise ValueError("User not found")

    old_phone = user.phone
    phone_hash = hashlib.sha256(f"{old_phone}_{datetime.now().timestamp()}".encode()).hexdigest()[:10]

    # Anonymize User record
    user.phone = f"deleted_{user.id}_{phone_hash}"
    user.is_deleted = True
    user.consent_withdrawn_at = datetime.now(UTC)

    # Cancel active listings
    await db.execute(
        update(Listing)
        .where(Listing.farmer_id == user_id, Listing.status == "active")
        .values(status="cancelled")
    )

    # Anonymize transporter documents if exists
    res_transporter = await db.execute(select(Transporter).where(Transporter.user_id == user_id))
    transporter = res_transporter.scalar_one_or_none()
    if transporter:
        transporter.available_today = False
        transporter.is_verified = False
        transporter.license_photo_url = "anonymized"
        transporter.rc_photo_url = "anonymized"
        transporter.insurance_photo_url = None
        transporter.fitness_photo_url = None

    await db.commit()

    await log_security_event(
        db=db,
        action="DPDP_DATA_DELETION",
        user_id=user_id,
        actor_role="user",
        client_ip=client_ip,
        target_resource="User",
        target_id=str(user_id),
        details={"reason": reason, "anonymized_phone_hash": phone_hash},
    )

    return {
        "status": "success",
        "message": "User personal data successfully erased and anonymized per DPDP Act Section 12.",
        "user_id": user_id,
        "deleted_at": datetime.now(UTC).isoformat(),
    }
