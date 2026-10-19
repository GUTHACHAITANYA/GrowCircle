"""
Tests for Phase 5: Farm Diary, economics metrics, voice read-back, and exports.
"""

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.price import Price


@pytest.mark.asyncio
async def test_farm_diary_season_lifecycle_and_entries(
    client: AsyncClient,
) -> None:
    # 1. Create a season
    res = await client.post(
        "/diary/seasons?farmer_id=1",
        json={
            "season_name": "Kharif Banana 2026",
            "crop_id": "banana",
            "area_acres": 2.5,
            "soil_type": "Black cotton soil",
            "planting_date": "2026-06-01",
            "harvest_date": "2026-10-15",
            "expected_yield_kg": 5000.0,
            "district": "Guntur",
        },
    )
    assert res.status_code == 201
    season_data = res.json()
    season_id = season_data["id"]
    assert season_data["season_name"] == "Kharif Banana 2026"
    assert season_data["area_acres"] == 2.5

    # 2. Add cost entries
    res_cost1 = await client.post(
        f"/diary/seasons/{season_id}/entries",
        json={
            "entry_type": "cost",
            "category": "seeds",
            "amount_inr": 12000.0,
            "quantity_kg": 0.0,
            "unit_price_inr": 0.0,
            "entry_date": "2026-06-02",
            "notes": "Tissue culture saplings (800 plants)",
            "readback_confirmed": True,
        },
    )
    assert res_cost1.status_code == 201

    res_cost2 = await client.post(
        f"/diary/seasons/{season_id}/entries",
        json={
            "entry_type": "cost",
            "category": "labour",
            "amount_inr": 8000.0,
            "quantity_kg": 0.0,
            "unit_price_inr": 0.0,
            "entry_date": "2026-07-15",
            "notes": "Weeding and trenching labour",
            "readback_confirmed": True,
        },
    )
    assert res_cost2.status_code == 201

    # 3. Add yield log entry
    res_yield = await client.post(
        f"/diary/seasons/{season_id}/entries",
        json={
            "entry_type": "yield_log",
            "category": "harvest",
            "amount_inr": 0.0,
            "quantity_kg": 4000.0,
            "unit_price_inr": 0.0,
            "entry_date": "2026-10-10",
            "notes": "First cut harvest (400 bunches)",
            "readback_confirmed": True,
        },
    )
    assert res_yield.status_code == 201

    # 4. Add sale revenue entry
    res_sale = await client.post(
        f"/diary/seasons/{season_id}/entries",
        json={
            "entry_type": "sale_revenue",
            "category": "sale",
            "amount_inr": 114000.0,
            "quantity_kg": 4000.0,
            "unit_price_inr": 28.5,
            "entry_date": "2026-10-12",
            "notes": "Sold to ANU Hostel via GrowCircle direct contract",
            "readback_confirmed": True,
        },
    )
    assert res_sale.status_code == 201


@pytest.mark.asyncio
async def test_voice_entry_transcription_and_readback(client: AsyncClient) -> None:
    res = await client.post(
        "/diary/voice-readback",
        json={
            "voice_transcript_text": "Spent 6500 on fertilizer DAP yesterday",
            "entry_date": "2026-10-12",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["parsed_entry"]["entry_type"] == "cost"
    assert data["parsed_entry"]["category"] == "fertilizer"
    assert data["parsed_entry"]["amount_inr"] == 6500.0
    assert "₹6500" in data["readback_text_en"]
    assert "₹6500" in data["readback_text_te"]
    assert "₹6500" in data["readback_text_hi"]
    assert "₹6500" in data["readback_text_gu"]


@pytest.mark.asyncio
async def test_financial_metrics_and_mandi_comparison(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    # Seed historical mandi prices in Guntur for Mandi comparison
    p1 = Price(
        mandi_id=1,
        crop_id="banana",
        variety="Robusta",
        grade="A",
        price_date=date(2026, 7, 1),
        min_price_kg=22.0,
        max_price_kg=26.0,
        modal_price_kg=24.0,
        min_price_quintal=2200.0,
        max_price_quintal=2600.0,
        modal_price_quintal=2400.0,
        modal_price_ton=24000.0,
        arrival_tonnes=15.0,
        source="agmarknet",
    )
    p2 = Price(
        mandi_id=1,
        crop_id="banana",
        variety="Robusta",
        grade="A",
        price_date=date(2026, 9, 1),
        min_price_kg=23.0,
        max_price_kg=27.0,
        modal_price_kg=25.0,
        min_price_quintal=2300.0,
        max_price_quintal=2700.0,
        modal_price_quintal=2500.0,
        modal_price_ton=25000.0,
        arrival_tonnes=20.0,
        source="agmarknet",
    )
    db_session.add_all([p1, p2])
    await db_session.commit()

    # Create season (2.0 acres)
    res_s = await client.post(
        "/diary/seasons?farmer_id=1",
        json={
            "season_name": "Banana Plot 2",
            "crop_id": "banana",
            "area_acres": 2.0,
            "soil_type": "Clay",
            "planting_date": "2026-06-15",
            "harvest_date": "2026-10-15",
            "expected_yield_kg": 4000.0,
            "district": "Guntur",
        },
    )
    season_id = res_s.json()["id"]

    # Costs: 20,000 INR
    await client.post(
        f"/diary/seasons/{season_id}/entries",
        json={
            "entry_type": "cost",
            "category": "labour",
            "amount_inr": 20000.0,
            "quantity_kg": 0.0,
            "unit_price_inr": 0.0,
            "entry_date": "2026-07-01",
            "notes": "Farm workers",
            "readback_confirmed": True,
        },
    )

    # Yield: 2000 kg
    await client.post(
        f"/diary/seasons/{season_id}/entries",
        json={
            "entry_type": "yield_log",
            "category": "harvest",
            "amount_inr": 0.0,
            "quantity_kg": 2000.0,
            "unit_price_inr": 0.0,
            "entry_date": "2026-10-01",
            "notes": "Harvested",
            "readback_confirmed": True,
        },
    )

    # Sale: 2000 kg sold at ₹30/kg -> ₹60,000 revenue
    await client.post(
        f"/diary/seasons/{season_id}/entries",
        json={
            "entry_type": "sale_revenue",
            "category": "sale",
            "amount_inr": 60000.0,
            "quantity_kg": 2000.0,
            "unit_price_inr": 30.0,
            "entry_date": "2026-10-02",
            "notes": "Direct Sale",
            "readback_confirmed": True,
        },
    )

    # Calculate metrics
    res_m = await client.get(f"/diary/seasons/{season_id}/metrics")
    assert res_m.status_code == 200
    metrics = res_m.json()

    assert metrics["total_cost_inr"] == 20000.0
    assert metrics["total_revenue_inr"] == 60000.0
    assert metrics["net_profit_loss_inr"] == 40000.0
    # Profit per acre = 40,000 / 2.0 = 20,000 INR
    assert metrics["profit_loss_per_acre_inr"] == 20000.0
    # Break-even price = 20,000 / 2000 kg = ₹10.0 / kg
    assert metrics["break_even_price_per_kg"] == 10.0

    # Mandi comparison
    comp = metrics["mandi_comparison"]
    assert comp["farmer_actual_price_per_kg"] == 30.0
    assert comp["mandi_average_price_per_kg"] > 0
    assert comp["price_premium_inr"] > 0
    assert comp["price_premium_percent"] > 0
    assert "earned an extra" in comp["comparison_summary"]


@pytest.mark.asyncio
async def test_diary_export_csv_and_json(
    client: AsyncClient,
) -> None:
    res_s = await client.post(
        "/diary/seasons?farmer_id=1",
        json={
            "season_name": "Export Test Season",
            "crop_id": "banana",
            "area_acres": 1.5,
            "planting_date": "2026-05-01",
            "expected_yield_kg": 3000.0,
            "district": "Guntur",
        },
    )
    season_id = res_s.json()["id"]

    # CSV Export
    res_csv = await client.get(f"/diary/seasons/{season_id}/export?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "GrowCircle Farm Diary Export" in res_csv.text
    assert "Export Test Season" in res_csv.text

    # JSON Export
    res_json = await client.get(f"/diary/seasons/{season_id}/export?format=json")
    assert res_json.status_code == 200
    data = res_json.json()
    assert data["season_id"] == season_id
    assert data["crop_id"] == "banana"
