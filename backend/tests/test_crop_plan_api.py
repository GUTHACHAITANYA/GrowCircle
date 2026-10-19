"""
FastAPI Integration Tests for GET /crop-plan Endpoint (Phase ML-3).
Verifies:
1. Status 200, Pydantic schema validation, and mandatory disclaimer.
2. 3 to 5 candidate crops ranked by expected profit with downside risk ranges.
3. Month parameter bounds validation (ge=1, le=12).
4. Blended farmer diary cost integration when farmer_id has logged seasons.
5. Multilingual audio guidance payloads.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_crop_plan_basic_success(client: AsyncClient) -> None:
    """Verifies standard GET /crop-plan response without farmer_id."""
    res = await client.get("/crop-plan?district=Guntur&month=7")
    assert res.status_code == 200

    data = res.json()
    assert data["district"] == "Guntur"
    assert data["planting_month"] == 7
    assert data["planting_month_name"] == "July"
    assert data["farmer_id"] is None
    assert data["data_sufficiency"] == "regional_norms"

    # Mandatory KVK disclaimer
    assert "guidance" in data["plain_disclaimer"].lower()
    assert "kvk" in data["plain_disclaimer"].lower() or "agriculture officer" in data["plain_disclaimer"].lower()

    # 3 to 5 candidates
    candidates = data["ranked_candidates"]
    assert 3 <= len(candidates) <= 5

    # Check first candidate fields
    top = candidates[0]
    assert "crop_id" in top
    assert "crop_name_en" in top
    assert "crash_risk_score" in top
    assert top["crash_risk_level"] in ["LOW", "MEDIUM", "HIGH", "SEVERE"]
    assert len(top["profit_per_acre_range"]) == 3
    assert len(top["harvest_price_kg_range"]) == 3
    assert len(top["yield_tonnes_acre_range"]) == 3
    assert len(top["cost_per_acre_range"]) == 3

    # Ranking check: profits must descend
    profits = [c["expected_profit_acre"] for c in candidates]
    assert profits == sorted(profits, reverse=True)

    # 4 languages for voice
    assert set(data["voice_summary"].keys()) == {"en", "te", "hi", "gu"}


@pytest.mark.asyncio
async def test_get_crop_plan_validation_error(client: AsyncClient) -> None:
    """Verifies that invalid month parameter returns 422."""
    res = await client.get("/crop-plan?district=Guntur&month=13")
    assert res.status_code == 422

    res_zero = await client.get("/crop-plan?district=Guntur&month=0")
    assert res_zero.status_code == 422


@pytest.mark.asyncio
async def test_get_crop_plan_blended_farmer_diary(client: AsyncClient) -> None:
    """Verifies that when a farmer has diary entries, data_sufficiency is 'blended_farmer_diary'."""
    # 1. Create a season for farmer_id=1
    season_res = await client.post(
        "/diary/seasons?farmer_id=1",
        json={
            "season_name": "Personal Tomato Trial 2026",
            "crop_id": "tomato",
            "area_acres": 2.0,
            "soil_type": "Red loamy",
            "planting_date": "2026-05-10",
            "harvest_date": "2026-08-15",
            "expected_yield_kg": 20000.0,
            "district": "Guntur",
        },
    )
    assert season_res.status_code == 201
    season_id = season_res.json()["id"]

    # 2. Add cost entries (total Rs. 60,000 for 2 acres = Rs. 30,000 / acre)
    entry_res = await client.post(
        f"/diary/seasons/{season_id}/entries",
        json={
            "entry_type": "cost",
            "category": "seeds",
            "amount_inr": 60000.0,
            "quantity_kg": 0.0,
            "unit_price_inr": 0.0,
            "entry_date": "2026-05-15",
            "notes": "Hybrid seedlings",
            "readback_confirmed": True,
        },
    )
    assert entry_res.status_code == 201

    # 3. Add yield log (18,000 kg for 2 acres = 9 tonnes / acre)
    yield_res = await client.post(
        f"/diary/seasons/{season_id}/entries",
        json={
            "entry_type": "yield_log",
            "category": "harvest",
            "amount_inr": 0.0,
            "quantity_kg": 18000.0,
            "unit_price_inr": 0.0,
            "entry_date": "2026-08-10",
            "notes": "Harvest pick 1",
            "readback_confirmed": True,
        },
    )
    assert yield_res.status_code == 201

    # 4. Request crop plan with farmer_id=1
    plan_res = await client.get("/crop-plan?district=Guntur&month=7&farmer_id=1")
    assert plan_res.status_code == 200
    plan = plan_res.json()

    assert plan["farmer_id"] == 1
    assert plan["data_sufficiency"] == "blended_farmer_diary"
    # Farmer personal diary should be cited in sources
    assert any("personal" in s.lower() or "diary" in s.lower() for s in plan["sources_and_assumptions"])
