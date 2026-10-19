"""
Tests for Phase 5: Consumer features: multi-crop listing, seasonality, and price alerts.
"""

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.price import Price


@pytest.mark.asyncio
async def test_consumer_crops_catalog_multilingual(client: AsyncClient) -> None:
    res = await client.get("/consumer/crops")
    assert res.status_code == 200
    crops = res.json()
    crop_ids = [c["id"] for c in crops]
    assert "banana" in crop_ids
    assert "tomato" in crop_ids
    assert "onion" in crop_ids
    assert "chilli" in crop_ids

    # Verify multilingual support
    banana = next(c for c in crops if c["id"] == "banana")
    assert banana["name_te"] == "అరటిపండు"
    assert banana["name_hi"] == "केला"
    assert banana["name_gu"] == "કેળા"


@pytest.mark.asyncio
async def test_consumer_seasonality_analysis(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    # 1. Normal/fair baseline check
    res_fair = await client.get("/consumer/seasonality?crop=banana&district=Guntur")
    assert res_fair.status_code == 200
    data_fair = res_fair.json()
    assert data_fair["crop_id"] == "banana"
    assert "plain_language_verdict" in data_fair

    # 2. Seed high price to trigger "expensive this month"
    p_high = Price(
        mandi_id=1,
        crop_id="tomato",
        variety="Local",
        grade="A",
        price_date=date(2026, 10, 13),
        min_price_kg=40.0,
        max_price_kg=50.0,
        modal_price_kg=45.0,  # Far above standard benchmark 28.0
        min_price_quintal=4000.0,
        max_price_quintal=5000.0,
        modal_price_quintal=4500.0,
        modal_price_ton=45000.0,
        arrival_tonnes=8.0,
        source="agmarknet",
    )
    db_session.add(p_high)
    await db_session.commit()

    res_exp = await client.get("/consumer/seasonality?crop=tomato&district=Guntur")
    assert res_exp.status_code == 200
    data_exp = res_exp.json()
    assert data_exp["is_expensive"] is True
    assert data_exp["status"] == "expensive"
    assert "Expensive this month" in data_exp["plain_language_verdict"]


@pytest.mark.asyncio
async def test_consumer_price_alerts_lifecycle(client: AsyncClient) -> None:
    # 1. Subscribe to WhatsApp alert without login
    res_sub = await client.post(
        "/consumer/alerts",
        json={
            "user_phone": "+919876543210",
            "channel": "whatsapp",
            "crop_id": "tomato",
            "district": "Guntur",
            "alert_type": "below_price",
            "target_price_kg": 25.0,
        },
    )
    assert res_sub.status_code == 201
    alert = res_sub.json()
    alert_id = alert["id"]
    assert alert["user_phone"] == "+919876543210"
    assert alert["channel"] == "whatsapp"
    assert alert["target_price_kg"] == 25.0

    # 2. List user alerts
    res_list = await client.get("/consumer/alerts?phone=%2B919876543210")
    assert res_list.status_code == 200
    alerts = res_list.json()
    assert len(alerts) == 1
    assert alerts[0]["crop_id"] == "tomato"

    # 3. Delete / unsubscribe alert
    res_del = await client.delete(f"/consumer/alerts/{alert_id}?phone=%2B919876543210")
    assert res_del.status_code == 204

    # 4. Confirm deleted
    res_list2 = await client.get("/consumer/alerts?phone=%2B919876543210")
    assert len(res_list2.json()) == 0
