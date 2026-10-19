"""
Tests for production mode fail-safe rules, startup checks, age labeling,
fail-closed messages, and data health endpoints.
"""

from datetime import date, datetime, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.main import lifespan, app
from backend.app.models.mandi import Mandi
from backend.app.models.price import Price


@pytest.mark.asyncio
async def test_production_startup_refuses_demo_data(db_session: AsyncSession):
    """
    Requirement 6 & Rule A: Startup check fails in production if any row has source = 'demo'.
    """
    mandi = (await db_session.execute(select(Mandi))).scalars().first()
    assert mandi is not None

    # Insert a demo price row
    demo_price = Price(
        mandi_id=mandi.id,
        crop_id="banana",
        variety="Robusta",
        grade="FAQ",
        price_date=date.today(),
        min_price_quintal=1500.0,
        max_price_quintal=2000.0,
        modal_price_quintal=1800.0,
        min_price_kg=15.0,
        max_price_kg=20.0,
        modal_price_kg=18.0,
        modal_price_ton=18000.0,
        source="demo",
        anomaly_status="clean",
    )
    db_session.add(demo_price)
    await db_session.commit()

    # Temporarily set APP_MODE to 'production' and configure app.state.engine to test engine
    original_mode = settings.APP_MODE
    app.state.engine = db_session.bind
    try:
        settings.APP_MODE = "production"

        # Calling lifespan should raise RuntimeError because demo row is present
        with pytest.raises(RuntimeError) as exc_info:
            async with lifespan(app):
                pass

        assert "PRODUCTION STARTUP REFUSAL" in str(exc_info.value)
        assert "source='demo'" in str(exc_info.value)

    finally:
        settings.APP_MODE = original_mode
        app.state.engine = None


@pytest.mark.asyncio
async def test_production_mode_excludes_demo_prices_from_api(
    client: AsyncClient, db_session: AsyncSession
):
    """
    In production mode, GET /prices must never return demo prices.
    """
    mandi = (await db_session.execute(select(Mandi))).scalars().first()
    assert mandi is not None

    # Add a demo row alongside existing real rows
    demo_price = Price(
        mandi_id=mandi.id,
        crop_id="banana",
        variety="Synthetic Variety",
        grade="FAQ",
        price_date=date.today(),
        min_price_quintal=1500.0,
        max_price_quintal=2000.0,
        modal_price_quintal=1800.0,
        min_price_kg=15.0,
        max_price_kg=20.0,
        modal_price_kg=18.0,
        modal_price_ton=18000.0,
        source="demo",
        anomaly_status="clean",
    )
    db_session.add(demo_price)
    await db_session.commit()

    original_mode = settings.APP_MODE
    try:
        settings.APP_MODE = "production"
        resp = await client.get("/prices?crop=banana")
        assert resp.status_code == 200
        data = resp.json()

        # None of the returned items should have source == 'demo'
        for item in data:
            assert item["source"] != "demo"
            assert item["variety"] != "Synthetic Variety"
    finally:
        settings.APP_MODE = original_mode


@pytest.mark.asyncio
async def test_prices_age_labeling_and_fail_closed(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Rule B: If a price is old, show 'No price reported for this mandi today. Last reported: <date>'
    and correctly label age ('today', 'yesterday', 'N days ago').
    """
    mandi = (await db_session.execute(select(Mandi))).scalars().first()
    assert mandi is not None

    today = date.today()
    three_days_ago = today - timedelta(days=3)

    old_price = Price(
        mandi_id=mandi.id,
        crop_id="banana",
        variety="HistoricalVariety",
        grade="FAQ",
        price_date=three_days_ago,
        min_price_quintal=1600.0,
        max_price_quintal=2100.0,
        modal_price_quintal=1900.0,
        min_price_kg=16.0,
        max_price_kg=21.0,
        modal_price_kg=19.0,
        modal_price_ton=19000.0,
        source="data.gov.in",
        anomaly_status="clean",
    )
    db_session.add(old_price)
    await db_session.commit()

    resp = await client.get("/prices?crop=banana")
    assert resp.status_code == 200
    prices = resp.json()

    # Find the old price entry
    old_item = next((p for p in prices if p["variety"] == "HistoricalVariety"), None)
    assert old_item is not None
    assert old_item["is_reported_today"] is False
    assert old_item["is_stale"] is True
    assert "3 days ago" in old_item["age_label"]
    assert "No price reported for this mandi today. Last reported:" in old_item["status_message"]
    assert three_days_ago.isoformat() in old_item["status_message"]
    assert "Agmarknet" in old_item["provenance_text"]


@pytest.mark.asyncio
async def test_data_health_endpoint(client: AsyncClient, db_session: AsyncSession):
    """
    Requirement 4: /health/data endpoint shows last successful fetch per source
    and per state, number of mandis reporting today, and alerts if data is older than 24h.
    """
    resp = await client.get("/health/data")
    assert resp.status_code == 200
    data = resp.json()

    assert "overall_healthy" in data
    assert "sources" in data
    assert "states" in data
    assert "mandis_reporting_today" in data
    assert "stale_alerts" in data
    assert isinstance(data["mandis_reporting_today"], int)
    assert isinstance(data["stale_alerts"], list)
