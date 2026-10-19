"""
Tests for R3: Geolocation-based nearest mandis, PIN code fallback, and hierarchy endpoints.
Covers 5 nearest mandis, few-results, no-results, max_age_days cutoff, pincode lookup, and hierarchy.
"""

from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.hierarchy import DistrictMaster, MandalMaster, StateMaster
from backend.app.models.mandi import Mandi
from backend.app.models.price import Price


@pytest.mark.asyncio
async def test_nearby_mandis_returns_sorted_by_distance(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """R3: Returns up to 5 mandis sorted by straight-line distance with recent prices."""
    _ = db_session
    # User at Guntur (16.3067, 80.4365)
    response = await client.get(
        "/nearby-mandis",
        params={
            "lat": 16.3067,
            "lng": 80.4365,
            "crop": "banana",
            "limit": 5,
            "radius_km": 100.0,
            "max_age_days": 3,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert len(data) <= 5

    # Check sorting: distance must be non-decreasing
    distances = [m["distance_km"] for m in data]
    assert distances == sorted(distances)

    # First mandi is Guntur itself (distance ~0.0)
    assert data[0]["canonical_name"] == "Guntur" or data[0]["name"] == "Guntur"
    assert data[0]["distance_km"] < 1.0

    # Fields required by R3: price per kg, per quintal, reported date, age, arrivals, distance
    first = data[0]
    assert "modal_price_kg" in first
    assert "modal_price_quintal" in first
    assert "price_date" in first
    assert "age_days" in first
    assert "age_label" in first
    assert "arrivals_tonnes" in first
    assert "distance_km" in first
    assert "distance_label" in first
    assert first["distance_label"] == "straight-line distance"

    # Response headers
    assert response.headers.get("x-distance-type") == "straight-line distance"
    assert response.headers.get("x-radius-km") == "100.0"


@pytest.mark.asyncio
async def test_nearby_mandis_few_results_case(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """R3: When fewer than 5 mandis report within radius, returns only available without padding."""
    _ = db_session
    # With a small radius of 20 km from Guntur, only Guntur is within 20km (Vijayawada is ~31km away)
    response = await client.get(
        "/nearby-mandis",
        params={
            "lat": 16.3067,
            "lng": 80.4365,
            "crop": "banana",
            "limit": 5,
            "radius_km": 20.0,
            "max_age_days": 3,
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Few results: exactly 1 mandi reported within 20km
    assert len(data) == 1
    assert data[0]["canonical_name"] == "Guntur" or data[0]["name"] == "Guntur"
    assert response.headers.get("x-reported-count") == "1"


@pytest.mark.asyncio
async def test_nearby_mandis_no_results_case(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """R3: When no mandis report within radius, returns empty list without padding."""
    _ = db_session
    # Middle of ocean / desert or remote coordinates with radius 5km
    response = await client.get(
        "/nearby-mandis",
        params={
            "lat": 10.0,
            "lng": 70.0,
            "crop": "banana",
            "limit": 5,
            "radius_km": 5.0,
            "max_age_days": 3,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data == []
    assert response.headers.get("x-reported-count") == "0"


@pytest.mark.asyncio
async def test_nearby_mandis_excludes_stale_prices(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """R3 Fail-Closed: Mandis with price older than max_age_days (e.g. 10 days ago) are excluded."""
    # Create an extra verified mandi near Guntur
    mandi_stale = Mandi(
        name="Stale Test Mandi",
        canonical_name="Stale Test Mandi",
        district="Guntur",
        state="Andhra Pradesh",
        latitude=16.3100,
        longitude=80.4400,
        location_verified=True,
        geocode_confidence=1.0,
        geocode_source="test",
    )
    db_session.add(mandi_stale)
    await db_session.flush()

    # Add a price from 10 days ago (well beyond 3-day max age)
    stale_date = date.today() - timedelta(days=10)
    old_price = Price(
        mandi_id=mandi_stale.id,
        crop_id="banana",
        variety="Robusta",
        grade="FAQ",
        price_date=stale_date,
        modal_price_kg=20.0,
        min_price_kg=18.0,
        max_price_kg=22.0,
        min_price_quintal=1800.0,
        max_price_quintal=2200.0,
        modal_price_quintal=2000.0,
        modal_price_ton=20000.0,
        source="data.gov.in",
    )
    db_session.add(old_price)
    await db_session.commit()

    response = await client.get(
        "/nearby-mandis",
        params={
            "lat": 16.3067,
            "lng": 80.4365,
            "crop": "banana",
            "limit": 5,
            "radius_km": 100.0,
            "max_age_days": 3,
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Verify that Stale Test Mandi is NOT included
    mandi_names = [m["mandi_name"] for m in data]
    assert "Stale Test Mandi" not in mandi_names


@pytest.mark.asyncio
async def test_pincode_lookup_endpoint(client: AsyncClient) -> None:
    """R3: Tests PIN code resolution for non-blocking geolocation fallback."""
    # Valid PIN code
    response = await client.get("/pincode-lookup", params={"pincode": "522001"})
    assert response.status_code == 200
    data = response.json()
    assert data["pincode"] == "522001"
    assert data["district"] == "Guntur"
    assert data["state"] == "Andhra Pradesh"
    assert "latitude" in data
    assert "longitude" in data

    # Invalid PIN code (format triggers FastAPI 422 validation error)
    resp_invalid = await client.get("/pincode-lookup", params={"pincode": "abc"})
    assert resp_invalid.status_code in (400, 422)

    # Unrecognized PIN code
    resp_not_found = await client.get("/pincode-lookup", params={"pincode": "999999"})
    assert resp_not_found.status_code == 404


@pytest.mark.asyncio
async def test_hierarchy_cascade_endpoints(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """R3/R4: Cascade selectors: State > District > Mandal hierarchy."""
    # Seed state, district, mandal in test db
    state = StateMaster(
        id="AP_TEST",
        name="Andhra Pradesh Test",
        min_lat=12.0,
        max_lat=19.5,
        min_lon=76.0,
        max_lon=85.0,
    )
    db_session.add(state)
    await db_session.flush()

    district = DistrictMaster(
        state_id="AP_TEST",
        name="Guntur Test",
    )
    db_session.add(district)
    await db_session.flush()

    mandal = MandalMaster(
        district_id=district.id,
        name="Tenali Test",
        latitude=16.2430,
        longitude=80.6400,
    )
    db_session.add(mandal)
    await db_session.commit()

    # 1. States
    r_states = await client.get("/hierarchy/states")
    assert r_states.status_code == 200
    states_data = r_states.json()
    assert any(s["id"] == "AP_TEST" for s in states_data)

    # 2. Districts
    r_districts = await client.get("/hierarchy/districts", params={"state_id": "AP_TEST"})
    assert r_districts.status_code == 200
    districts_data = r_districts.json()
    assert any(d["name"] == "Guntur Test" for d in districts_data)

    # 3. Mandals
    r_mandals = await client.get("/hierarchy/mandals", params={"district_id": district.id})
    assert r_mandals.status_code == 200
    mandals_data = r_mandals.json()
    assert any(m["name"] == "Tenali Test" for m in mandals_data)
