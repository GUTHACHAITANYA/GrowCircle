"""
FastAPI route integration tests:
- GET /health
- GET /prices
- GET /nearby-mandis
- GET /history
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["database"] == "connected"
    assert data["service"] == "growcircle-engine"
    assert "last_successful_fetch_time" in data


@pytest.mark.asyncio
async def test_get_prices_unfiltered(client: AsyncClient) -> None:
    response = await client.get("/prices?crop=banana")
    assert response.status_code == 200
    prices = response.json()
    assert len(prices) >= 3

    first = prices[0]
    assert first["crop_id"] == "banana"
    assert first["modal_price_kg"] > 0
    assert first["modal_price_quintal"] == first["modal_price_kg"] * 100
    assert first["source"] == "data.gov.in"
    assert "price_date" in first
    assert "last_updated" in first


@pytest.mark.asyncio
async def test_get_prices_filtered_by_district(client: AsyncClient) -> None:
    response = await client.get("/prices?crop=banana&state=andhra-pradesh&district=guntur")
    assert response.status_code == 200
    prices = response.json()
    assert len(prices) == 1
    assert prices[0]["mandi_name"] == "Guntur"
    assert prices[0]["district"] == "Guntur"
    assert prices[0]["modal_price_kg"] == 25.0


@pytest.mark.asyncio
async def test_get_nearby_mandis_distance_ranking(client: AsyncClient) -> None:
    # Query centered on Guntur coordinates
    guntur_lat, guntur_lng = 16.3067, 80.4365
    response = await client.get(
        f"/nearby-mandis?lat={guntur_lat}&lng={guntur_lng}&crop=banana&limit=3"
    )
    assert response.status_code == 200
    nearby = response.json()
    assert len(nearby) == 3

    # Guntur must be closest (distance ~0 km)
    assert nearby[0]["mandi_name"] == "Guntur"
    assert nearby[0]["distance_km"] <= 1.0

    # Vijayawada must be 2nd closest (~31-35 km)
    assert nearby[1]["mandi_name"] == "Vijayawada"
    assert 25.0 <= nearby[1]["distance_km"] <= 40.0

    # Madanapalle must be 3rd closest (~380 km)
    assert nearby[2]["mandi_name"] == "Madanapalle"
    assert nearby[2]["distance_km"] > 300.0


@pytest.mark.asyncio
async def test_get_history_endpoint(client: AsyncClient) -> None:
    # History for Guntur mandi (id=1)
    response = await client.get("/history?mandi_id=1&crop=banana&days=30")
    assert response.status_code == 200
    data = response.json()
    assert data["mandi_name"] == "Guntur"
    assert data["crop_id"] == "banana"
    assert len(data["history"]) >= 1
    assert data["history"][0]["modal_price_kg"] == 25.0


@pytest.mark.asyncio
async def test_get_history_mandi_not_found(client: AsyncClient) -> None:
    response = await client.get("/history?mandi_id=99999&crop=banana")
    assert response.status_code == 404
    assert response.json()["detail"] == "Mandi not found"
