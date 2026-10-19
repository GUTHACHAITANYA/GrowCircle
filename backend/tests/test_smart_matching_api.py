"""
Integration tests for ML-5: Smart Matching and Logistics API.

Tests:
1. POST /logistics/rank-listings: Buyer-farmer ranking with A/B variant and fairness audit.
2. POST /logistics/rate-guide: Fair transport rate regression guide with ranges.
3. POST /logistics/pool-routes: OR-Tools multi-stop CVRPTW pooling with cost-per-kg savings.
4. POST /logistics/rank-drivers: Driver matching with anti-monopoly fair distribution.
5. GET /logistics/data-sufficiency: Honest data threshold documentation (1,200 sessions).
6. GET /logistics/audit-logs: Structured decision audit trail retrieval.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_rank_listings_endpoint(client: AsyncClient) -> None:
    """Verifies buyer-farmer ranking endpoint with fairness audit."""
    payload = {
        "query_id": "test-query-101",
        "buyer_id": "buyer-99",
        "candidates": [
            {
                "candidate_id": "cand-1",
                "farmer_name": "Ramesh",
                "crop": "tomato",
                "distance_km": 10.0,
                "quantity_kg": 500.0,
                "requested_qty_kg": 500.0,
                "farmer_grade": "A",
                "buyer_grade_req": "A",
                "price_per_kg": 20.0,
                "mandi_modal_price": 20.0,
                "completion_rate": 0.95,
                "response_time_hours": 1.0,
                "rating": 4.8,
                "is_smallholder": True,
            },
            {
                "candidate_id": "cand-2",
                "farmer_name": "Kalyan",
                "crop": "tomato",
                "distance_km": 35.0,
                "quantity_kg": 200.0,
                "requested_qty_kg": 500.0,
                "farmer_grade": "B",
                "buyer_grade_req": "A",
                "price_per_kg": 28.0,
                "mandi_modal_price": 20.0,
                "completion_rate": 0.70,
                "response_time_hours": 5.0,
                "rating": 3.8,
                "is_smallholder": False,
            },
        ],
        "forced_variant": "rules",
        "apply_fairness_mitigation": True,
    }

    resp = await client.post("/logistics/rank-listings", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["query_id"] == "test-query-101"
    assert data["variant_used"] == "rules"
    assert len(data["ranked_candidates"]) == 2
    assert data["ranked_candidates"][0]["candidate_id"] == "cand-1"
    assert "fairness_audit" in data
    assert data["fairness_audit"]["is_fair"] is True
    assert "data_sufficiency" in data


@pytest.mark.asyncio
async def test_transport_rate_guide_endpoint(client: AsyncClient) -> None:
    """Verifies fair transport rate guide endpoint with ranges and breakdown."""
    payload = {
        "distance_km": 35.0,
        "load_weight_kg": 650.0,
        "vehicle_type": "mini_truck",
        "fuel_price_per_litre": 98.50,
        "road_type": "district_road",
        "is_night": False,
    }

    resp = await client.post("/logistics/rate-guide", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["min_guide_rate"] <= data["estimated_guide_rate"] <= data["max_guide_rate"]
    assert data["rate_per_kg"] > 0.0
    assert "breakdown" in data
    assert "disclaimer" in data
    assert "Indicative" in data["disclaimer"]


@pytest.mark.asyncio
async def test_pool_routes_endpoint(client: AsyncClient) -> None:
    """Verifies OR-Tools vehicle routing pooling endpoint."""
    payload = {
        "pickups": [
            {
                "order_id": "ORD-1",
                "farmer_name": "Sita",
                "latitude": 16.24,
                "longitude": 80.64,
                "weight_kg": 400.0,
                "crop": "tomato",
                "earliest_pickup_hour": 1.0,
                "latest_pickup_hour": 5.0,
            },
            {
                "order_id": "ORD-2",
                "farmer_name": "Govind",
                "latitude": 16.25,
                "longitude": 80.63,
                "weight_kg": 350.0,
                "crop": "tomato",
                "earliest_pickup_hour": 1.5,
                "latest_pickup_hour": 5.5,
            },
        ],
        "dropoff": {
            "destination_name": "Guntur Market Yard",
            "latitude": 16.30,
            "longitude": 80.43,
            "latest_arrival_hour": 12.0,
        },
        "vehicles": [
            {
                "vehicle_id": "V-101",
                "vehicle_type": "mini_truck",
                "capacity_kg": 1500.0,
            }
        ],
    }

    resp = await client.post("/logistics/pool-routes", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["success"] is True
    assert data["total_cargo_weight_kg"] == 750.0
    assert len(data["routes"]) >= 1
    assert data["savings"]["percentage_saved"] > 0
    assert data["savings"]["cost_per_kg_pooled_inr"] < data["savings"]["cost_per_kg_separate_inr"]


@pytest.mark.asyncio
async def test_rank_drivers_endpoint(client: AsyncClient) -> None:
    """Verifies driver matching endpoint with anti-monopoly fair distribution."""
    payload = {
        "pickup_lat": 16.24,
        "pickup_lng": 80.64,
        "load_weight_kg": 400.0,
        "drivers": [
            {
                "driver_id": "D-1",
                "name": "Driver Active",
                "phone": "9998887771",
                "vehicle_type": "mini_truck",
                "vehicle_model": "Tata Ace",
                "capacity_kg": 1000.0,
                "current_latitude": 16.241,
                "current_longitude": 80.641,
                "reliability_rating": 4.9,
                "on_time_rate": 0.98,
                "trips_completed_total": 80,
                "recent_trips_count": 9,
                "is_verified": True,
                "is_available": True,
            },
            {
                "driver_id": "D-2",
                "name": "Driver Idle",
                "phone": "9998887772",
                "vehicle_type": "mini_truck",
                "vehicle_model": "Tata Ace",
                "capacity_kg": 1000.0,
                "current_latitude": 16.242,
                "current_longitude": 80.642,
                "reliability_rating": 4.7,
                "on_time_rate": 0.95,
                "trips_completed_total": 30,
                "recent_trips_count": 0,
                "is_verified": True,
                "is_available": True,
            },
        ],
        "apply_fairness_leveling": True,
        "limit": 3,
    }

    resp = await client.post("/logistics/rank-drivers", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_evaluated"] == 2
    assert len(data["ranked_drivers"]) == 2
    # Fair leveling prioritizes idle peer
    assert data["ranked_drivers"][0]["driver_id"] == "D-2"
    assert data["leveling_enabled"] is True


@pytest.mark.asyncio
async def test_data_sufficiency_and_audit_logs(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    """Verifies data sufficiency check and decision audit logs endpoints."""
    # Data sufficiency
    suff_resp = await client.get("/logistics/data-sufficiency")
    assert suff_resp.status_code == 200
    suff_data = suff_resp.json()
    assert suff_data["required_sessions"] == 1200
    assert "statistical_rationale" in suff_data

    # Audit logs
    audit_resp = await client.get("/logistics/audit-logs", headers=admin_headers)
    assert audit_resp.status_code == 200
    assert isinstance(audit_resp.json(), list)
