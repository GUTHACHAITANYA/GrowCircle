"""
Mandi Master, LGD Hierarchy, and Geocoding Review Admin API Handlers.
Supports:
- Reviewing low-confidence / unverified coordinates
- Fixing / verifying mandi coordinates with state boundary sanity validation
- Merging duplicate mandis with full price re-pointing and audit logging
- Generating hierarchy reports (mandis per state, verified counts, review list)
- Mandal mapping overview (nearest mandis for mandals without physical markets)
"""

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_db
from backend.app.models.audit_log import AuditLog
from backend.app.models.ground_truth import GroundTruthCheck
from backend.app.models.hierarchy import DistrictMaster, MandalMaster, StateMaster
from backend.app.models.mandi import Mandi
from backend.app.models.price import Price
from backend.app.schemas.mandi_master import (
    CoordinateFixRequest,
    MandiHierarchyReport,
    MandiMergeRequest,
    MandiOut,
    StateMandiCount,
)
from backend.app.services.mandi_master.geocoder import STATE_BOUNDING_BOXES
from backend.app.services.mandi_master.mandal_mapper import haversine_km
from backend.app.services.security import require_admin_role_enforced

router = APIRouter(
    prefix="/admin/mandis",
    tags=["Mandi Master & Hierarchy"],
    dependencies=[Depends(require_admin_role_enforced(require_2fa=False))],
)


@router.get("", response_model=list[MandiOut])
async def list_mandis(
    state: Annotated[str | None, Query(description="Filter by state name")] = None,
    district: Annotated[str | None, Query(description="Filter by district name")] = None,
    location_verified: Annotated[bool | None, Query(description="Filter by verified location")] = None,
    needs_review: Annotated[bool | None, Query(description="Filter by review status")] = None,
    is_active: Annotated[bool, Query(description="Active mandis only")] = True,
    db: AsyncSession = Depends(get_async_db),
) -> list[MandiOut]:
    """Returns list of mandis with optional administrative and verification filters."""
    stmt = select(Mandi).where(Mandi.is_active == is_active)

    if state:
        stmt = stmt.where(func.lower(Mandi.state) == state.strip().lower())
    if district:
        stmt = stmt.where(func.lower(Mandi.district) == district.strip().lower())
    if location_verified is not None:
        stmt = stmt.where(Mandi.location_verified == location_verified)
    if needs_review is not None:
        stmt = stmt.where(Mandi.needs_review == needs_review)

    stmt = stmt.order_by(Mandi.state, Mandi.district, Mandi.name)
    results = (await db.execute(stmt)).scalars().all()
    return [MandiOut.model_validate(m) for m in results]


@router.get("/review", response_model=list[MandiOut])
async def list_mandis_for_review(
    db: AsyncSession = Depends(get_async_db),
) -> list[MandiOut]:
    """Returns all mandis flagged for manual review or lacking verified coordinates."""
    stmt = (
        select(Mandi)
        .where(
            Mandi.is_active == True,
            (Mandi.needs_review == True) | (Mandi.location_verified == False),
        )
        .order_by(desc(Mandi.needs_review), Mandi.state, Mandi.name)
    )
    results = (await db.execute(stmt)).scalars().all()
    return [MandiOut.model_validate(m) for m in results]


@router.post("/{mandi_id}/verify-coordinates", response_model=MandiOut)
async def verify_mandi_coordinates(
    mandi_id: int,
    payload: CoordinateFixRequest,
    db: AsyncSession = Depends(get_async_db),
) -> MandiOut:
    """
    Sets verified coordinates for a mandi after admin manual inspection.
    Enforces geographic bounding box sanity check against the mandi's state.
    Maps to the closest mandal and writes an immutable entry into AuditLog.
    """
    mandi = await db.get(Mandi, mandi_id)
    if not mandi:
        raise HTTPException(status_code=404, detail=f"Mandi ID {mandi_id} not found.")

    # 1. Coordinate Sanity Validation against State Bounding Box
    state_key = mandi.state.strip().lower()
    bbox = STATE_BOUNDING_BOXES.get(state_key)
    if bbox:
        inside = (
            bbox["min_lat"] <= payload.latitude <= bbox["max_lat"]
            and bbox["min_lon"] <= payload.longitude <= bbox["max_lon"]
        )
        if not inside:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Coordinates ({payload.latitude:.4f}, {payload.longitude:.4f}) fall outside "
                    f"the geographic boundary for {mandi.state} "
                    f"[Lat: {bbox['min_lat']}..{bbox['max_lat']}, Lon: {bbox['min_lon']}..{bbox['max_lon']}]."
                ),
            )

    old_lat = mandi.latitude
    old_lon = mandi.longitude
    old_verified = mandi.location_verified

    # 2. Update mandi coordinates
    mandi.latitude = payload.latitude
    mandi.longitude = payload.longitude
    mandi.location_verified = True
    mandi.needs_review = False
    mandi.review_reason = None
    mandi.geocode_confidence = 1.0
    mandi.geocode_source = "manual"

    # 3. Associate with Mandal
    if payload.mandal_name:
        matched_mandal = await db.scalar(
            select(MandalMaster)
            .join(DistrictMaster, MandalMaster.district_id == DistrictMaster.id)
            .where(
                DistrictMaster.name.ilike(mandi.district.strip()),
                MandalMaster.name.ilike(payload.mandal_name.strip()),
            )
        )
        if matched_mandal:
            mandi.mandal_id = matched_mandal.id
            mandi.mandal = matched_mandal.name
            mandi.mandal_lgd_code = matched_mandal.lgd_code
    else:
        # Auto-match closest mandal in district
        mandals = (
            await db.execute(
                select(MandalMaster)
                .join(DistrictMaster, MandalMaster.district_id == DistrictMaster.id)
                .where(DistrictMaster.name.ilike(mandi.district.strip()))
            )
        ).scalars().all()

        best_mandal = None
        min_d = float("inf")
        for m in mandals:
            if m.latitude and m.longitude:
                d = haversine_km(payload.latitude, payload.longitude, m.latitude, m.longitude)
                if d < min_d:
                    min_d = d
                    best_mandal = m

        if best_mandal:
            mandi.mandal_id = best_mandal.id
            mandi.mandal = best_mandal.name
            mandi.mandal_lgd_code = best_mandal.lgd_code

    # 4. Write Audit Trail
    audit_log = AuditLog(
        action="MANDI_COORDINATES_FIX",
        actor_role="admin",
        target_resource="mandis",
        target_id=str(mandi.id),
        details=(
            f"Verified coordinates for '{mandi.name}' ({mandi.state}, {mandi.district}). "
            f"Old: ({old_lat}, {old_lon}, verified={old_verified}) -> "
            f"New: ({payload.latitude}, {payload.longitude}, mandal='{mandi.mandal}'). "
            f"Notes: {payload.notes or 'None'}"
        ),
        status="SUCCESS",
    )
    db.add(audit_log)

    await db.commit()
    await db.refresh(mandi)
    return MandiOut.model_validate(mandi)


@router.post("/merge", response_model=dict[str, Any])
async def merge_duplicate_mandis(
    payload: MandiMergeRequest,
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """
    Merges duplicate_mandi into primary_mandi:
    1. Re-points all Price records to primary_mandi.
    2. Re-points all GroundTruthCheck records to primary_mandi.
    3. Deactivates duplicate_mandi (is_active=False, merged_into_id=primary_mandi_id).
    4. Records immutable entry in AuditLog.
    """
    if payload.primary_mandi_id == payload.duplicate_mandi_id:
        raise HTTPException(status_code=400, detail="Cannot merge a mandi into itself.")

    primary = await db.get(Mandi, payload.primary_mandi_id)
    if not primary:
        raise HTTPException(
            status_code=404, detail=f"Primary Mandi ID {payload.primary_mandi_id} not found."
        )

    duplicate = await db.get(Mandi, payload.duplicate_mandi_id)
    if not duplicate:
        raise HTTPException(
            status_code=404, detail=f"Duplicate Mandi ID {payload.duplicate_mandi_id} not found."
        )

    # 1. Re-point or deduplicate Price rows
    dup_prices = (
        await db.execute(select(Price).where(Price.mandi_id == duplicate.id))
    ).scalars().all()

    prices_repointed = 0
    prices_deduplicated = 0
    for p in dup_prices:
        existing_primary_price = await db.scalar(
            select(Price).where(
                Price.mandi_id == primary.id,
                Price.crop_id == p.crop_id,
                Price.variety == p.variety,
                Price.grade == p.grade,
                Price.price_date == p.price_date,
                Price.source == p.source,
            )
        )
        if existing_primary_price:
            await db.delete(p)
            prices_deduplicated += 1
        else:
            p.mandi_id = primary.id
            prices_repointed += 1

    # 2. Re-point GroundTruthCheck rows
    gt_update_res = await db.execute(
        update(GroundTruthCheck)
        .where(GroundTruthCheck.mandi_id == duplicate.id)
        .values(mandi_id=primary.id)
    )
    checks_repointed = gt_update_res.rowcount or 0

    # 3. Deactivate duplicate mandi
    duplicate.is_active = False
    duplicate.merged_into_id = primary.id
    duplicate.needs_review = False
    duplicate.review_reason = f"Merged into Mandi #{primary.id} ({primary.name})"

    # 4. Create Audit Log Entry
    audit = AuditLog(
        action="MANDI_MERGE",
        actor_role="admin",
        target_resource="mandis",
        target_id=str(duplicate.id),
        details=(
            f"Merged duplicate mandi #{duplicate.id} ('{duplicate.name}') into "
            f"primary mandi #{primary.id} ('{primary.name}'). "
            f"Re-pointed {prices_repointed} prices, deduplicated {prices_deduplicated} prices, "
            f"{checks_repointed} ground-truth checks. "
            f"Notes: {payload.notes or 'None'}"
        ),
        status="SUCCESS",
    )
    db.add(audit)

    await db.commit()

    return {
        "status": "success",
        "primary_mandi_id": primary.id,
        "primary_mandi_name": primary.name,
        "duplicate_mandi_id": duplicate.id,
        "duplicate_mandi_name": duplicate.name,
        "prices_repointed": prices_repointed,
        "prices_deduplicated": prices_deduplicated,
        "total_prices_processed": prices_repointed + prices_deduplicated,
        "checks_repointed": checks_repointed,
        "message": f"Successfully merged '{duplicate.name}' into '{primary.name}'.",
    }


@router.get("/hierarchy-report", response_model=MandiHierarchyReport)
async def get_mandi_hierarchy_report(
    db: AsyncSession = Depends(get_async_db),
) -> MandiHierarchyReport:
    """
    R2 Acceptance Report:
    - How many mandis exist per state.
    - How many have verified coordinates and a mandal.
    - List of mandis that still need manual review.
    """
    all_mandis = (
        (await db.execute(select(Mandi).where(Mandi.is_active == True).order_by(Mandi.state, Mandi.name)))
        .scalars()
        .all()
    )

    state_groups: dict[str, list[Mandi]] = {}
    for m in all_mandis:
        state_groups.setdefault(m.state, []).append(m)

    states_breakdown: list[StateMandiCount] = []
    for state_name, m_list in sorted(state_groups.items()):
        total = len(m_list)
        verified = sum(1 for m in m_list if m.location_verified and m.latitude and m.longitude)
        mandal_mapped = sum(1 for m in m_list if m.mandal_id is not None or m.mandal)
        needs_rev = sum(1 for m in m_list if m.needs_review or not m.location_verified)
        state_id = m_list[0].state_id if m_list else None

        states_breakdown.append(
            StateMandiCount(
                state_name=state_name,
                state_id=state_id,
                total_mandis=total,
                verified_coordinates_count=verified,
                mandal_mapped_count=mandal_mapped,
                needs_review_count=needs_rev,
            )
        )

    review_queue = [
        MandiOut.model_validate(m)
        for m in all_mandis
        if m.needs_review or not m.location_verified or not m.latitude or not m.longitude
    ]

    total_mandis = len(all_mandis)
    total_verified = sum(1 for m in all_mandis if m.location_verified and m.latitude and m.longitude)
    total_mandal_mapped = sum(1 for m in all_mandis if m.mandal_id is not None or m.mandal)
    total_needs_review = len(review_queue)

    return MandiHierarchyReport(
        total_mandis=total_mandis,
        total_verified_coordinates=total_verified,
        total_mandal_mapped=total_mandal_mapped,
        total_needs_review=total_needs_review,
        states_breakdown=states_breakdown,
        review_queue=review_queue,
    )
