"""
Unit and integration tests for Mandi Master, LGD Hierarchy, Normalization,
Geocoding Sanity, Duplicate Detection, and Admin Coordinate Fix / Merging.
"""

from datetime import date
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit_log import AuditLog
from backend.app.models.hierarchy import DistrictMaster, MandalMaster, StateMaster
from backend.app.models.mandi import Mandi
from backend.app.models.price import Price
from backend.app.services.mandi_master.geocoder import NominatimGeocoder
from backend.app.services.mandi_master.mandal_mapper import MandalMapper
from backend.app.services.mandi_master.normalizer import (
    find_potential_duplicates,
    normalize_market_name,
)


def test_mandi_name_normalization():
    # 1. Strip APMC suffix
    assert normalize_market_name("Somala APMC") == "Somala"
    assert normalize_market_name("Guntur A.P.M.C.") == "Guntur"

    # 2. Strip Market Yard / Sub-Yard
    assert normalize_market_name("Vijayawada Market Yard") == "Vijayawada"
    assert normalize_market_name("Tenali Sub-Yard (Grain)") == "Tenali"

    # 3. Strip Rythu Bazar / Fruit Market
    assert normalize_market_name("Tirupati Rythu Bazar") == "Tirupati"
    assert normalize_market_name("Madanapalle Fruit Market (F&V)") == "Madanapalle"

    # 4. Known spelling corrections
    assert normalize_market_name("Vijaywada APMC") == "Vijayawada"
    assert normalize_market_name("Madanapalli Market Yard") == "Madanapalle"
    assert normalize_market_name("Rajahmundri") == "Rajahmundry"
    assert normalize_market_name("Ananthapur APMC") == "Anantapur"


def test_duplicate_detection():
    mandis_sample = [
        {"id": 1, "name": "Guntur APMC", "district": "Guntur", "state": "Andhra Pradesh"},
        {"id": 2, "name": "Guntur Market Yard", "district": "Guntur", "state": "Andhra Pradesh"},
        {"id": 3, "name": "Vijayawada", "district": "NTR", "state": "Andhra Pradesh"},
        {"id": 4, "name": "Vijaywada APMC", "district": "NTR", "state": "Andhra Pradesh"},
    ]

    duplicates = find_potential_duplicates(mandis_sample, threshold=0.85)
    assert len(duplicates) == 2

    guntur_dup = next(d for d in duplicates if "Guntur" in d["canonical_name"])
    assert guntur_dup["mandi_1_id"] == 1
    assert guntur_dup["mandi_2_id"] == 2
    assert guntur_dup["similarity"] == 1.0

    vja_dup = next(d for d in duplicates if "Vijayawada" in d["canonical_name"])
    assert vja_dup["mandi_1_id"] == 3
    assert vja_dup["mandi_2_id"] == 4
    assert vja_dup["similarity"] == 1.0


def test_coordinate_sanity_against_state_bounds():
    geocoder = NominatimGeocoder()

    # Inside AP bounds: Guntur (16.3067, 80.4365)
    assert geocoder.is_coordinate_inside_state(16.3067, 80.4365, "Andhra Pradesh") is True

    # Inside AP bounds: Madanapalle (13.5500, 78.5000)
    assert geocoder.is_coordinate_inside_state(13.5500, 78.5000, "Andhra Pradesh") is True

    # Outside AP bounds: New Delhi (28.6139, 77.2090)
    assert geocoder.is_coordinate_inside_state(28.6139, 77.2090, "Andhra Pradesh") is False

    # Outside AP bounds: Mumbai (19.0760, 72.8777 - Longitude is in Maharashtra)
    assert geocoder.is_coordinate_inside_state(19.0760, 72.8777, "Andhra Pradesh") is False


@pytest.mark.asyncio
async def test_lgd_hierarchy_and_mandal_overview(db_session: AsyncSession):
    # Setup LGD hierarchy
    state = StateMaster(
        id="AP", name="Andhra Pradesh", lgd_code=28,
        min_lat=12.6, max_lat=19.9, min_lon=76.7, max_lon=84.8
    )
    db_session.add(state)
    await db_session.flush()

    district = DistrictMaster(id=1, state_id="AP", name="Guntur", lgd_code=506)
    db_session.add(district)
    await db_session.flush()

    mandal_chebrolu = MandalMaster(
        id=10, district_id=1, name="Chebrolu", lgd_code=4917, latitude=16.1989, longitude=80.5303
    )
    db_session.add(mandal_chebrolu)
    await db_session.commit()

    mapper = MandalMapper(db_session)
    overview = await mapper.get_mandal_market_overview(mandal_id=10)

    # Chebrolu has no direct mandi in db, so it must return nearest mandis
    assert overview["has_local_mandi"] is False
    assert "No mandi in Chebrolu mandal. Nearest reporting mandis:" in overview["status_message"]
    assert len(overview["nearest_mandis"]) >= 1


@pytest.mark.asyncio
async def test_unverified_mandis_excluded_from_distance_queries(
    client: AsyncClient, db_session: AsyncSession, admin_headers: dict[str, str]
):
    """
    Requirement 3: Unmapped or unverified mandis are excluded from distance-based results until verified.
    """
    # Create an unverified mandi with coordinates close to user
    unverified_mandi = Mandi(
        name="Unverified Secret Market",
        canonical_name="Secret Market",
        district="Guntur",
        state="Andhra Pradesh",
        latitude=16.3100,
        longitude=80.4400,
        location_verified=False,  # NOT verified
        needs_review=True,
    )
    db_session.add(unverified_mandi)
    await db_session.flush()

    # Add price for this unverified mandi
    p = Price(
        mandi_id=unverified_mandi.id,
        crop_id="banana",
        variety="Robusta",
        grade="FAQ",
        price_date=date.today(),
        min_price_quintal=2000.0,
        max_price_quintal=2500.0,
        modal_price_quintal=2200.0,
        min_price_kg=20.0,
        max_price_kg=25.0,
        modal_price_kg=22.0,
        modal_price_ton=22000.0,
        source="data.gov.in",
        anomaly_status="clean",
    )
    db_session.add(p)
    await db_session.commit()

    # 1. Query /nearby-mandis close to Guntur
    resp = await client.get("/nearby-mandis?lat=16.30&lng=80.43&crop=banana&limit=5")
    assert resp.status_code == 200
    data = resp.json()

    # Unverified mandi must NOT appear in distance results
    mandi_names = [item["mandi_name"] for item in data]
    assert "Unverified Secret Market" not in mandi_names

    # 2. Verify the mandi via Admin API
    fix_payload = {
        "latitude": 16.3100,
        "longitude": 80.4400,
        "notes": "Verified via secretary call",
    }
    verify_resp = await client.post(
        f"/admin/mandis/{unverified_mandi.id}/verify-coordinates", json=fix_payload, headers=admin_headers
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["location_verified"] is True

    # 3. Query /nearby-mandis again: verified mandi should now appear!
    resp2 = await client.get("/nearby-mandis?lat=16.30&lng=80.43&crop=banana&limit=5")
    assert resp2.status_code == 200
    mandi_names2 = [item["mandi_name"] for item in resp2.json()]
    assert "Unverified Secret Market" in mandi_names2


@pytest.mark.asyncio
async def test_admin_verify_coordinates_rejects_out_of_state_bounds(
    client: AsyncClient, db_session: AsyncSession, admin_headers: dict[str, str]
):
    """
    Ensures admin coordinate fix rejects coordinates outside the state's bounding box.
    """
    mandi = (await db_session.execute(select(Mandi))).scalars().first()
    assert mandi is not None

    # Try setting New Delhi coordinates for Andhra Pradesh mandi
    bad_payload = {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "notes": "Invalid Delhi coordinates",
    }
    resp = await client.post(f"/admin/mandis/{mandi.id}/verify-coordinates", json=bad_payload, headers=admin_headers)
    assert resp.status_code == 400
    assert "fall outside the geographic boundary" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_admin_merge_duplicates_and_audit_trail(
    client: AsyncClient, db_session: AsyncSession, admin_headers: dict[str, str]
):
    """
    Requirement 5: Admin page to merge duplicates and fix coordinates, with an audit log.
    """
    primary = (await db_session.execute(select(Mandi))).scalars().first()
    assert primary is not None

    # Create a duplicate mandi
    duplicate = Mandi(
        name="Guntur Duplicate APMC",
        canonical_name="Guntur",
        district="Guntur",
        state="Andhra Pradesh",
        latitude=16.3067,
        longitude=80.4365,
        location_verified=False,
        needs_review=True,
    )
    db_session.add(duplicate)
    await db_session.flush()

    # Add a price row pointing to duplicate
    price = Price(
        mandi_id=duplicate.id,
        crop_id="tomato",
        variety="Amruthapani",
        grade="FAQ",
        price_date=date.today(),
        min_price_quintal=2100.0,
        max_price_quintal=2600.0,
        modal_price_quintal=2300.0,
        min_price_kg=21.0,
        max_price_kg=26.0,
        modal_price_kg=23.0,
        modal_price_ton=23000.0,
        source="data.gov.in",
        anomaly_status="clean",
    )
    db_session.add(price)
    await db_session.commit()

    # Perform Merge
    merge_payload = {
        "primary_mandi_id": primary.id,
        "duplicate_mandi_id": duplicate.id,
        "notes": "Merging duplicate spelling into canonical Guntur",
    }
    merge_resp = await client.post("/admin/mandis/merge", json=merge_payload, headers=admin_headers)
    assert merge_resp.status_code == 200
    res_data = merge_resp.json()
    assert res_data["status"] == "success"
    assert res_data["prices_repointed"] >= 1
    assert res_data["total_prices_processed"] >= 1

    # Verify duplicate is deactivated
    await db_session.refresh(duplicate)
    assert duplicate.is_active is False
    assert duplicate.merged_into_id == primary.id

    # Verify price is now attached to primary
    await db_session.refresh(price)
    assert price.mandi_id == primary.id

    # Verify audit log entry
    audit = (
        (
            await db_session.execute(
                select(AuditLog).where(AuditLog.action == "MANDI_MERGE")
            )
        )
        .scalars()
        .first()
    )
    assert audit is not None
    assert str(duplicate.id) in audit.details
    assert str(primary.id) in audit.details


@pytest.mark.asyncio
async def test_mandi_hierarchy_report_endpoint(client: AsyncClient, admin_headers: dict[str, str]):
    """
    Acceptance: report how many mandis exist per state, how many have verified coordinates
    and a mandal, and list the ones that still need manual review.
    """
    resp = await client.get("/admin/mandis/hierarchy-report", headers=admin_headers)
    assert resp.status_code == 200
    report = resp.json()

    assert "total_mandis" in report
    assert "total_verified_coordinates" in report
    assert "total_mandal_mapped" in report
    assert "total_needs_review" in report
    assert "states_breakdown" in report
    assert "review_queue" in report

    assert report["total_mandis"] >= 3
    assert len(report["states_breakdown"]) >= 1
    state_ap = next(
        (s for s in report["states_breakdown"] if s["state_name"] == "Andhra Pradesh"), None
    )
    assert state_ap is not None
    assert state_ap["total_mandis"] >= 3
