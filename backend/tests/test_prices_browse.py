"""
Tests for R4: Geographic browsing for prices.
Covers:
1. Dynamic cascade filter options from database (State > District > Mandal > Mandi, Crop, Variety).
2. Honest fallback when a mandal has no mandi (e.g. Chebrolu).
3. Area aggregates calculation (median modal price, count) and 1-2 mandi integrity warning note.
4. 30-day sparklines, sorting, and user preference persistence.
"""

from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.hierarchy import DistrictMaster, MandalMaster, StateMaster
from backend.app.models.mandi import Mandi
from backend.app.models.price import Price


async def setup_hierarchy_data(db_session: AsyncSession) -> dict[str, int]:
    """Helper to seed state, district, mandals, and Tenali mandi in test SQLite db."""
    state = StateMaster(
        id="AP",
        name="Andhra Pradesh",
        min_lat=12.0,
        max_lat=19.5,
        min_lon=76.0,
        max_lon=85.0,
    )
    db_session.add(state)
    await db_session.flush()

    district = DistrictMaster(
        state_id="AP",
        name="Guntur",
    )
    db_session.add(district)
    await db_session.flush()

    m_tenali = MandalMaster(
        district_id=district.id,
        name="Tenali",
        latitude=16.2430,
        longitude=80.6400,
    )
    m_chebrolu = MandalMaster(
        district_id=district.id,
        name="Chebrolu",
        latitude=16.1989,
        longitude=80.5283,
    )
    db_session.add_all([m_tenali, m_chebrolu])
    await db_session.flush()

    mandi_tenali = Mandi(
        name="Tenali",
        canonical_name="Tenali Market Yard",
        district="Guntur",
        state="Andhra Pradesh",
        mandal="Tenali",
        latitude=16.2430,
        longitude=80.6400,
        location_verified=True,
    )
    db_session.add(mandi_tenali)
    await db_session.flush()

    today = date.today()
    p_tenali = Price(
        mandi_id=mandi_tenali.id,
        crop_id="banana",
        variety="Robusta",
        grade="FAQ",
        price_date=today,
        min_price_quintal=1600.0,
        max_price_quintal=2000.0,
        modal_price_quintal=1800.0,
        min_price_kg=16.0,
        max_price_kg=20.0,
        modal_price_kg=18.0,
        modal_price_ton=18000.0,
        arrival_tonnes=25.0,
        source="data.gov.in",
        anomaly_status="clean",
    )
    db_session.add(p_tenali)
    await db_session.commit()

    return {"district_id": district.id, "tenali_mandi_id": mandi_tenali.id}


@pytest.mark.asyncio
async def test_dynamic_hierarchy_options(client: AsyncClient, db_session: AsyncSession) -> None:
    """R4 Rule 1: Filter options come dynamically from the database, not hardcoded lists."""
    await setup_hierarchy_data(db_session)

    # 1. States from database
    states_resp = await client.get("/hierarchy/states")
    assert states_resp.status_code == 200
    states = states_resp.json()
    assert isinstance(states, list)
    assert any(s["name"] == "Andhra Pradesh" for s in states)

    # 2. Districts narrowed by state
    dist_resp = await client.get("/hierarchy/districts?state=Andhra Pradesh")
    assert dist_resp.status_code == 200
    districts = dist_resp.json()
    assert isinstance(districts, list)
    assert any(d["name"] == "Guntur" for d in districts)

    # 3. Mandals narrowed by district
    mandal_resp = await client.get("/hierarchy/mandals?district=Guntur")
    assert mandal_resp.status_code == 200
    mandals = mandal_resp.json()
    assert isinstance(mandals, list)
    assert any(m["name"] == "Chebrolu" for m in mandals)
    assert any(m["name"] == "Tenali" for m in mandals)

    # 4. Mandis narrowed by district
    mandi_resp = await client.get("/hierarchy/mandis?state=Andhra Pradesh&district=Guntur")
    assert mandi_resp.status_code == 200
    mandis = mandi_resp.json()
    assert isinstance(mandis, list)
    assert any(m["name"] == "Tenali" for m in mandis)
    assert any(m["name"] == "Guntur" for m in mandis)

    # 5. Crops from database
    crops_resp = await client.get("/crops")
    assert crops_resp.status_code == 200
    crops = crops_resp.json()
    assert any((c["id"] == "banana" if isinstance(c, dict) else c == "banana") for c in crops)

    # 6. Varieties for chosen crop
    varieties_resp = await client.get("/varieties?crop=banana")
    assert varieties_resp.status_code == 200
    varieties = varieties_resp.json()
    assert isinstance(varieties, list)
    assert len(varieties) >= 1


@pytest.mark.asyncio
async def test_prices_cascade_browsing(client: AsyncClient, db_session: AsyncSession) -> None:
    """R4 Acceptance: Pick Andhra Pradesh > Guntur district > Tenali mandal > Tenali mandi."""
    await setup_hierarchy_data(db_session)

    # Query Tenali specifically
    resp = await client.get(
        "/prices",
        params={
            "state": "Andhra Pradesh",
            "district": "Guntur",
            "mandal": "Tenali",
            "mandi": "Tenali",
            "crop": "banana",
        },
    )
    assert resp.status_code == 200
    prices = resp.json()
    assert isinstance(prices, list)
    assert len(prices) >= 1

    tenali_price = prices[0]
    assert tenali_price["mandi_name"] == "Tenali"
    assert tenali_price["district"] == "Guntur"
    assert tenali_price["crop_id"] == "banana"
    assert tenali_price["modal_price_kg"] == 18.0
    assert tenali_price["modal_price_quintal"] == 1800.0
    assert "reported_date" in tenali_price
    assert "sparkline_30d" in tenali_price
    assert isinstance(tenali_price["sparkline_30d"], list)


@pytest.mark.asyncio
async def test_honest_mandal_fallback_when_no_mandi(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """R4 Rule 4: If a mandal has no mandi, show nearest reporting mandis and explain honestly."""
    await setup_hierarchy_data(db_session)

    # Chebrolu has no APMC market yard
    resp = await client.get(
        "/prices",
        params={
            "state": "Andhra Pradesh",
            "district": "Guntur",
            "mandal": "Chebrolu",
            "crop": "banana",
        },
    )
    assert resp.status_code == 200

    # Must flag honest fallback in headers
    assert resp.headers.get("x-mandal-has-mandi") == "false"
    assert resp.headers.get("x-mandal-fallback") == "true"

    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    # Mandis returned are nearest ones with distance computed from Chebrolu centroid
    first_mandi = data[0]
    assert first_mandi["status_message"] is not None
    assert "No mandi exists in Chebrolu mandal" in first_mandi["status_message"]
    assert first_mandi["distance_km"] is not None
    assert first_mandi["distance_km"] > 5.0
    assert first_mandi["distance_label"] == "straight-line distance"


@pytest.mark.asyncio
async def test_price_aggregates_and_sample_size_alert(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """R4 Rule 3: Aggregates show median modal price and count. If 1 or 2 mandis reported, warn explicitly."""
    await setup_hierarchy_data(db_session)

    # Query Guntur district
    resp = await client.get("/prices/aggregates?district=Guntur&crop=banana")
    assert resp.status_code == 200
    agg = resp.json()

    assert "reporting_mandis_count" in agg
    assert "median_modal_price_kg" in agg
    assert "median_modal_price_quintal" in agg
    assert "note" in agg

    # Guntur has 2 reporting mandis (Guntur at 25.0 and Tenali at 18.0)
    assert agg["reporting_mandis_count"] == 2
    assert agg["is_area_average_reliable"] is False
    assert "Only 2 mandis reported" in agg["note"]
    assert "instead of an area average" in agg["note"]


@pytest.mark.asyncio
async def test_prices_sorting_options(client: AsyncClient, db_session: AsyncSession) -> None:
    """R4 Rule 2: Sort by price, distance (if location is known) or name."""
    await setup_hierarchy_data(db_session)

    # 1. Sort by price ascending
    resp_asc = await client.get("/prices?district=Guntur&crop=banana&sort_by=price&sort_order=asc")
    assert resp_asc.status_code == 200
    data_asc = resp_asc.json()
    prices_asc = [p["modal_price_kg"] for p in data_asc]
    assert prices_asc == sorted(prices_asc)

    # 2. Sort by price descending
    resp_desc = await client.get("/prices?district=Guntur&crop=banana&sort_by=price&sort_order=desc")
    assert resp_desc.status_code == 200
    data_desc = resp_desc.json()
    prices_desc = [p["modal_price_kg"] for p in data_desc]
    assert prices_desc == sorted(prices_desc, reverse=True)

    # 3. Sort by name ascending
    resp_name = await client.get("/prices?district=Guntur&crop=banana&sort_by=name&sort_order=asc")
    assert resp_name.status_code == 200
    data_name = resp_name.json()
    names = [p["mandi_name"].lower() for p in data_name]
    assert names == sorted(names)


@pytest.mark.asyncio
async def test_user_preferences_persistence(client: AsyncClient, db_session: AsyncSession) -> None:
    """R4 Rule 5: User preferences persistence for geographic browsing."""
    _ = db_session

    # Save preference
    post_resp = await client.post(
        "/user/preferences",
        json={"state": "Andhra Pradesh", "district": "Guntur", "crop": "banana"},
    )
    assert post_resp.status_code == 200
    res_data = post_resp.json()
    assert res_data["status"] == "saved"

    # Get default preference
    get_resp = await client.get("/user/preferences")
    assert get_resp.status_code == 200
    pref = get_resp.json()
    assert pref["state"] == "Andhra Pradesh"
    assert pref["district"] == "Guntur"
