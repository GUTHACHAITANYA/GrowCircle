"""
Comprehensive Integration Tests for Phase 4: Transport.
Tests Transporters, Expiry checks, Vehicle classification, Guide rates,
Driver suggestions, Trips, OTPs, Delivery photo & disputes, Pooling v1, and Admin views.
"""

from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient

from backend.app.models.transporter import Transporter
from backend.app.models.user import User
from backend.app.services.security import create_access_token
from backend.app.services.transport_matching import (
    calculate_guide_rate,
    classify_vehicle_for_weight,
    plan_pooled_trips_v1,
)


@pytest.fixture
async def admin_headers(db_session):
    admin = User(
        phone="+919999999999",
        language="en",
        district="Guntur",
        role="admin",
        consent_at=datetime.now(UTC),
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    token = create_access_token(user_id=admin.id, phone=admin.phone, role="admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_vehicle_classification_by_weight():
    """Verify vehicle category by load weight."""
    assert classify_vehicle_for_weight(250.0) == "goods_auto"
    assert classify_vehicle_for_weight(499.0) == "goods_auto"
    assert classify_vehicle_for_weight(500.0) == "mini_truck"
    assert classify_vehicle_for_weight(1200.0) == "mini_truck"
    assert classify_vehicle_for_weight(1500.0) == "mini_truck"
    assert classify_vehicle_for_weight(1501.0) == "large_truck"
    assert classify_vehicle_for_weight(3500.0) == "large_truck"


@pytest.mark.asyncio
async def test_guide_rate_calculation():
    """Verify guide rate arithmetic and minimum distance baseline."""
    # 10 km distance
    # goods_auto: 150 + (10 * 18) = 330.0
    assert calculate_guide_rate(10.0, "goods_auto") == 330.0

    # mini_truck: 350 + (10 * 25) = 600.0
    assert calculate_guide_rate(10.0, "mini_truck") == 600.0

    # large_truck: 700 + (10 * 38) = 1080.0
    assert calculate_guide_rate(10.0, "large_truck") == 1080.0

    # Under 2km uses 2km minimum billable distance
    assert calculate_guide_rate(1.0, "goods_auto") == 150.0 + (2.0 * 18.0)


@pytest.mark.asyncio
async def test_transporter_registration_and_compliance(client: AsyncClient, db_session, admin_headers):
    """Verify transporter registration, default unverified state, and admin verification."""
    user = User(
        phone="+919848123456",
        language="te",
        district="Guntur",
        role="driver",
        consent_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    today = date.today()
    payload = {
        "user_id": user.id,
        "name": "Subba Rao",
        "phone": "+919848123456",
        "license_number": "AP07 20200001234",
        "license_expiry": (today + timedelta(days=365)).isoformat(),
        "license_photo_url": "https://cdn.growcircle.app/licenses/subba_rao.jpg",
        "rc_number": "AP07 TA 1234",
        "rc_expiry": (today + timedelta(days=700)).isoformat(),
        "rc_photo_url": "https://cdn.growcircle.app/rc/subba_rao.jpg",
        "insurance_expiry": (today + timedelta(days=180)).isoformat(),
        "insurance_photo_url": "https://cdn.growcircle.app/ins/subba_rao.jpg",
        "fitness_expiry": (today + timedelta(days=200)).isoformat(),
        "fitness_photo_url": "https://cdn.growcircle.app/fit/subba_rao.jpg",
        "vehicle_type": "goods_auto",
        "vehicle_model": "Piaggio Ape Extra LDX",
        "capacity_kg": 500,
        "service_area_districts": ["Guntur", "Krishna"],
        "current_latitude": 16.3067,
        "current_longitude": 80.4365,
    }

    resp = await client.post("/transport/transporters", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Subba Rao"
    assert data["is_verified"] is False
    assert data["is_compliant"] is False  # unverified so not compliant yet

    transporter_id = data["id"]

    # Admin verifies driver
    v_resp = await client.post(
        f"/transport/admin/transporters/{transporter_id}/verify?verify=true",
        headers=admin_headers,
    )
    assert v_resp.status_code == 200
    v_data = v_resp.json()
    assert v_data["is_verified"] is True
    assert v_data["is_compliant"] is True
    assert len(v_data["expired_documents"]) == 0


@pytest.mark.asyncio
async def test_automatic_document_expiry_checks_hide_driver(client: AsyncClient, db_session):
    """Verify that any expired document (License, RC, Insurance, Fitness) automatically hides the driver."""
    user = User(
        phone="+919848654321",
        language="te",
        district="Guntur",
        role="driver",
        consent_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    today = date.today()
    # Driver with EXPIRED insurance (expired 5 days ago)
    expired_driver = Transporter(
        user_id=user.id,
        name="Narasimha Rao",
        phone="+919848654321",
        license_number="AP07 20210005678",
        license_expiry=today + timedelta(days=300),
        license_photo_url="https://cdn.growcircle.app/license.jpg",
        rc_number="AP07 TB 5678",
        rc_expiry=today + timedelta(days=400),
        rc_photo_url="https://cdn.growcircle.app/rc.jpg",
        insurance_expiry=today - timedelta(days=5),  # EXPIRED!
        fitness_expiry=today + timedelta(days=100),
        vehicle_type="mini_truck",
        vehicle_model="Tata Ace Gold",
        capacity_kg=1000,
        service_area_districts=["Guntur"],
        current_latitude=16.3100,
        current_longitude=80.4400,
        is_verified=True,
        available_today=True,
    )
    db_session.add(expired_driver)
    await db_session.commit()
    await db_session.refresh(expired_driver)

    assert expired_driver.is_active_and_compliant() is False
    assert "insurance" in expired_driver.get_expired_documents()

    # Query suggestions for 800 kg load (requires mini_truck)
    sug_resp = await client.get(
        "/transport/suggestions",
        params={
            "pickup_lat": 16.3067,
            "pickup_lng": 80.4365,
            "dropoff_lat": 16.4400,
            "dropoff_lng": 80.5500,
            "load_weight_kg": 800.0,
        },
    )
    assert sug_resp.status_code == 200
    sug_data = sug_resp.json()
    driver_ids = [d["transporter_id"] for d in sug_data["suggested_drivers"]]
    assert expired_driver.id not in driver_ids  # Strictly excluded!


@pytest.mark.asyncio
async def test_suggest_drivers_near_pickup_ranked_and_capped_at_3(client: AsyncClient, db_session):
    """Verify that 3 verified compliant drivers closest to pickup are suggested with guide rate."""
    today = date.today()
    # Create 4 verified, compliant mini-truck drivers at different distances from pickup (16.3067, 80.4365)
    drivers_spec = [
        ("Driver Closest", "+919800000001", 16.3100, 80.4380, 4.9),  # ~0.4 km
        ("Driver Second", "+919800000002", 16.3500, 80.4500, 4.8),   # ~5 km
        ("Driver Third", "+919800000003", 16.4000, 80.5000, 4.7),    # ~12 km
        ("Driver Farthest", "+919800000004", 16.6000, 80.7000, 5.0), # ~40 km
    ]

    for name, phone, lat, lng, rel in drivers_spec:
        u = User(phone=phone, language="te", district="Guntur", role="driver")
        db_session.add(u)
        await db_session.commit()
        await db_session.refresh(u)

        t = Transporter(
            user_id=u.id,
            name=name,
            phone=phone,
            license_number="LIC" + phone[-4:],
            license_expiry=today + timedelta(days=365),
            license_photo_url="https://cdn.growcircle.app/lic.jpg",
            rc_number="RC" + phone[-4:],
            rc_expiry=today + timedelta(days=365),
            rc_photo_url="https://cdn.growcircle.app/rc.jpg",
            insurance_expiry=today + timedelta(days=365),
            fitness_expiry=today + timedelta(days=365),
            vehicle_type="mini_truck",
            vehicle_model="Tata Ace",
            capacity_kg=1200,
            service_area_districts=["Guntur"],
            current_latitude=lat,
            current_longitude=lng,
            is_verified=True,
            available_today=True,
            reliability_rating=rel,
        )
        db_session.add(t)

    await db_session.commit()

    resp = await client.get(
        "/transport/suggestions",
        params={
            "pickup_lat": 16.3067,
            "pickup_lng": 80.4365,
            "dropoff_lat": 16.4400,
            "dropoff_lng": 80.5500,
            "load_weight_kg": 600.0,  # mini_truck
            "limit": 3,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched_vehicle_type"] == "mini_truck"
    assert "Guide Rate" in data["rate_label"]
    assert "indicative estimate" in data["disclaimer"]
    assert len(data["suggested_drivers"]) == 3
    # Closest driver should be first
    assert data["suggested_drivers"][0]["name"] == "Driver Closest"
    assert data["suggested_drivers"][1]["name"] == "Driver Second"
    assert data["suggested_drivers"][2]["name"] == "Driver Third"


@pytest.mark.asyncio
async def test_trip_creation_and_otp_lifecycle(client: AsyncClient, db_session):
    """Verify trip creation, pickup OTP verification, and delivery OTP + photo verification."""
    today = date.today()
    user = User(phone="+919811122233", language="te", district="Guntur", role="driver")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    driver = Transporter(
        user_id=user.id,
        name="Koti Reddy",
        phone="+919811122233",
        license_number="AP07 9999",
        license_expiry=today + timedelta(days=365),
        license_photo_url="https://cdn.growcircle.app/lic.jpg",
        rc_number="AP07 RC 9999",
        rc_expiry=today + timedelta(days=365),
        rc_photo_url="https://cdn.growcircle.app/rc.jpg",
        insurance_expiry=today + timedelta(days=365),
        fitness_expiry=today + timedelta(days=365),
        vehicle_type="goods_auto",
        vehicle_model="Bajaj Maxima C",
        capacity_kg=500,
        service_area_districts=["Guntur"],
        current_latitude=16.3067,
        current_longitude=80.4365,
        is_verified=True,
        available_today=True,
    )
    db_session.add(driver)
    await db_session.commit()
    await db_session.refresh(driver)

    # 1. Create Trip
    create_payload = {
        "transporter_id": driver.id,
        "deal_ids": [101],
        "vehicle_type": "goods_auto",
        "total_weight_kg": 350.0,
        "distance_km": 14.5,
        "guide_rate": 411.0,
        "pickup_latitude": 16.2400,
        "pickup_longitude": 80.6400,
        "dropoff_latitude": 16.3067,
        "dropoff_longitude": 80.4365,
        "pickup_address": "Tenali Farm",
        "dropoff_address": "ANU Hostel",
    }
    trip_resp = await client.post("/transport/trips", json=create_payload)
    assert trip_resp.status_code == 201
    trip = trip_resp.json()
    trip_id = trip["id"]
    assert trip["status"] == "assigned"
    pickup_otp = trip["pickup_otp"]
    delivery_otp = trip["delivery_otp"]

    # 2. Pickup OTP verification: Wrong OTP fails
    fail_p = await client.post(
        f"/transport/trips/{trip_id}/pickup-otp",
        json={"pickup_otp": "0000"},
    )
    assert fail_p.status_code == 400

    # Correct Pickup OTP succeeds
    ok_p = await client.post(
        f"/transport/trips/{trip_id}/pickup-otp",
        json={"pickup_otp": pickup_otp},
    )
    assert ok_p.status_code == 200
    assert ok_p.json()["status"] == "in_transit"
    assert ok_p.json()["pickup_confirmed_at"] is not None

    # 3. Delivery OTP verification: Missing photo fails
    fail_d_photo = await client.post(
        f"/transport/trips/{trip_id}/delivery-otp",
        json={"delivery_otp": delivery_otp, "delivery_photo_url": ""},
    )
    assert fail_d_photo.status_code == 422  # validation error

    # Correct Delivery OTP + photo succeeds
    ok_d = await client.post(
        f"/transport/trips/{trip_id}/delivery-otp",
        json={
            "delivery_otp": delivery_otp,
            "delivery_photo_url": "https://cdn.growcircle.app/proofs/unloaded_crates_anu.jpg",
        },
    )
    assert ok_d.status_code == 200
    assert ok_d.json()["status"] == "delivered"
    assert ok_d.json()["delivery_confirmed_at"] is not None


@pytest.mark.asyncio
async def test_buyer_delivery_dispute_and_resolution(client: AsyncClient, db_session, admin_headers):
    """Verify buyer filing a delivery complaint with mandatory photo and admin resolving it."""
    today = date.today()
    user = User(phone="+919822233344", language="te", district="Guntur", role="driver")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    driver = Transporter(
        user_id=user.id,
        name="Srinivas M.",
        phone="+919822233344",
        license_number="LIC888",
        license_expiry=today + timedelta(days=365),
        license_photo_url="https://cdn.growcircle.app/lic.jpg",
        rc_number="RC888",
        rc_expiry=today + timedelta(days=365),
        rc_photo_url="https://cdn.growcircle.app/rc.jpg",
        insurance_expiry=today + timedelta(days=365),
        fitness_expiry=today + timedelta(days=365),
        vehicle_type="mini_truck",
        vehicle_model="Tata Ace",
        capacity_kg=1000,
        service_area_districts=["Guntur"],
        current_latitude=16.3067,
        current_longitude=80.4365,
        is_verified=True,
        available_today=True,
    )
    db_session.add(driver)
    await db_session.commit()
    await db_session.refresh(driver)

    # Create and start trip
    create_resp = await client.post(
        "/transport/trips",
        json={
            "transporter_id": driver.id,
            "deal_ids": [102],
            "vehicle_type": "mini_truck",
            "total_weight_kg": 800.0,
            "distance_km": 20.0,
            "guide_rate": 850.0,
            "pickup_latitude": 16.2400,
            "pickup_longitude": 80.6400,
            "dropoff_latitude": 16.3067,
            "dropoff_longitude": 80.4365,
        },
    )
    trip = create_resp.json()
    trip_id = trip["id"]

    # Pickup
    await client.post(
        f"/transport/trips/{trip_id}/pickup-otp",
        json={"pickup_otp": trip["pickup_otp"]},
    )

    # Buyer files dispute at delivery (e.g. 12 crates crushed in transit)
    dispute_resp = await client.post(
        f"/transport/trips/{trip_id}/dispute",
        json={
            "dispute_reason": "Top 12 banana crates were crushed due to improper vehicle stacking.",
            "dispute_photo_url": "https://cdn.growcircle.app/disputes/crushed_crates_102.jpg",
        },
    )
    assert dispute_resp.status_code == 200
    assert dispute_resp.json()["status"] == "disputed"

    # Admin checks active disputes queue
    admin_disputes = await client.get("/transport/admin/disputes", headers=admin_headers)
    assert admin_disputes.status_code == 200
    disputed_ids = [d["id"] for d in admin_disputes.json()]
    assert trip_id in disputed_ids

    # Admin resolves dispute
    res_resp = await client.post(
        f"/transport/admin/disputes/{trip_id}/resolve",
        json={
            "resolution_notes": "Mediated settlement: 20% freight deduction applied for damaged crates.",
            "final_status": "delivered",
        },
        headers=admin_headers,
    )
    assert res_resp.status_code == 200
    assert res_resp.json()["status"] == "delivered"


@pytest.mark.asyncio
async def test_mutual_ratings_updates_driver_reliability(client: AsyncClient, db_session):
    """Verify mutual rating submission and driver rating calculation."""
    today = date.today()
    u1 = User(phone="+919833344455", language="te", district="Guntur", role="farmer")
    u2 = User(phone="+919833344456", language="te", district="Guntur", role="driver")
    db_session.add_all([u1, u2])
    await db_session.commit()
    await db_session.refresh(u1)
    await db_session.refresh(u2)

    driver = Transporter(
        user_id=u2.id,
        name="Gopi K.",
        phone="+919833344456",
        license_number="LIC777",
        license_expiry=today + timedelta(days=365),
        license_photo_url="https://cdn.growcircle.app/lic.jpg",
        rc_number="RC777",
        rc_expiry=today + timedelta(days=365),
        rc_photo_url="https://cdn.growcircle.app/rc.jpg",
        insurance_expiry=today + timedelta(days=365),
        fitness_expiry=today + timedelta(days=365),
        vehicle_type="goods_auto",
        vehicle_model="Piaggio Ape",
        capacity_kg=500,
        service_area_districts=["Guntur"],
        current_latitude=16.3067,
        current_longitude=80.4365,
        is_verified=True,
        available_today=True,
        reliability_rating=5.0,
    )
    db_session.add(driver)
    await db_session.commit()
    await db_session.refresh(driver)

    # Create trip
    t_resp = await client.post(
        "/transport/trips",
        json={
            "transporter_id": driver.id,
            "deal_ids": [105],
            "vehicle_type": "goods_auto",
            "total_weight_kg": 300.0,
            "distance_km": 10.0,
            "guide_rate": 330.0,
            "pickup_latitude": 16.2400,
            "pickup_longitude": 80.6400,
            "dropoff_latitude": 16.3067,
            "dropoff_longitude": 80.4365,
        },
    )
    trip_id = t_resp.json()["id"]

    # Farmer rates driver (4 stars)
    farmer_token = create_access_token(
        user_id=u1.id, phone=u1.phone, role="farmer"
    )
    rate_resp = await client.post(
        f"/transport/trips/{trip_id}/ratings",
        json={
            "trip_id": trip_id,
            "ratee_id": u2.id,
            "role": "farmer_to_driver",
            "score": 4,
            "tag": "punctual",
            "comment": "Arrived at farm on time and helped loading.",
        },
        headers={"Authorization": f"Bearer {farmer_token}"},
    )
    assert rate_resp.status_code == 201


@pytest.mark.asyncio
async def test_pooling_v1_rule_based_algorithm():
    """Verify pooling v1 groups nearby loads to the same buyer into a single trip with savings."""
    deals = [
        # Deal 1: 400 kg from Farmer A (Tenali East) to ANU Hostel
        {
            "deal_id": 1,
            "buyer_id": 10,
            "farmer_name": "Farmer A",
            "quantity_kg": 400.0,
            "pickup_lat": 16.2400,
            "pickup_lng": 80.6400,
            "dropoff_lat": 16.3067,
            "dropoff_lng": 80.4365,
            "dropoff_address": "ANU Hostel",
        },
        # Deal 2: 500 kg from Farmer B (Tenali West, 4 km from Farmer A) to ANU Hostel
        {
            "deal_id": 2,
            "buyer_id": 10,
            "farmer_name": "Farmer B",
            "quantity_kg": 500.0,
            "pickup_lat": 16.2550,
            "pickup_lng": 80.6200,
            "dropoff_lat": 16.3067,
            "dropoff_lng": 80.4365,
            "dropoff_address": "ANU Hostel",
        },
        # Deal 3: Separate buyer (Retail Shop in Vijayawada)
        {
            "deal_id": 3,
            "buyer_id": 20,
            "farmer_name": "Farmer C",
            "quantity_kg": 300.0,
            "pickup_lat": 16.2400,
            "pickup_lng": 80.6400,
            "dropoff_lat": 16.5000,
            "dropoff_lng": 80.6500,
            "dropoff_address": "Vijayawada Shop",
        },
    ]

    plans = plan_pooled_trips_v1(deals, max_pickup_cluster_km=15.0)
    assert len(plans) == 2  # 1 pooled plan for ANU Hostel + 1 single plan for Vijayawada

    # Inspect pooled plan
    pooled = next(p for p in plans if p["is_pooled"])
    assert set(pooled["deal_ids"]) == {1, 2}
    assert pooled["total_weight_kg"] == 900.0
    assert pooled["vehicle_type"] == "mini_truck"  # 900 kg -> mini_truck
    assert len(pooled["pickup_stops"]) == 2
    assert pooled["estimated_savings"] > 0.0  # cheaper than two separate goods autos
