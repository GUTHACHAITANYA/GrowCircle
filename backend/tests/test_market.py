"""
Comprehensive tests for Phase 3: Direct Selling, Verification, Fresh Listings,
Matching, Offers, Deals, Ratings, and Masked Calls.
"""

from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.buyer import BuyerProfile
from backend.app.models.buyer_need import BuyerNeed
from backend.app.models.deal import Deal
from backend.app.models.listing import Listing
from backend.app.models.user import User
from backend.app.services.security import create_access_token, decrypt_document_data


@pytest.mark.asyncio
async def test_phone_otp_send_and_verify(client: AsyncClient) -> None:
    """Phone-OTP login: generates OTP and exchanges for JWT token."""
    phone = "9848011222"
    send_res = await client.post("/auth/send-otp", json={"phone": phone})
    assert send_res.status_code == 200
    assert send_res.json()["status"] == "otp_sent"

    # Verify with valid OTP
    verify_res = await client.post(
        "/auth/verify-otp",
        json={"phone": phone, "otp": "123456", "role": "farmer"},
    )
    assert verify_res.status_code == 200
    data = verify_res.json()
    assert "access_token" in data
    assert data["role"] == "farmer"


@pytest.mark.asyncio
async def test_invalid_otp_rejected(client: AsyncClient) -> None:
    """Incorrect OTP is rejected with 400 Bad Request."""
    res = await client.post(
        "/auth/verify-otp",
        json={"phone": "9848099999", "otp": "000000", "role": "farmer"},
    )
    assert res.status_code == 400
    assert "Invalid or expired OTP" in res.json()["detail"]


@pytest.mark.asyncio
async def test_buyer_registration_encrypts_proof(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Buyer registration encrypts GSTIN and document proofs at rest."""
    phone = "9848033333"
    user = User(phone=phone, role="buyer", language="te", consent_at=datetime.now(UTC))
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.id, user.phone, user.role)
    headers = {"Authorization": f"Bearer {token}"}

    raw_gst = "37AAAAA0000A1Z5"
    raw_doc = "https://s3.ap-south-1.amazonaws.com/growcircle/proofs/shop_act_01.pdf"

    payload = {
        "business_name": "Guntur University Hostel",
        "business_type": "hostel",
        "gst_number": raw_gst,
        "document_ref": raw_doc,
        "address": "Nagarjuna Nagar, Guntur",
        "district": "Guntur",
        "state": "Andhra Pradesh",
        "latitude": 16.3772,
        "longitude": 80.5244,
    }

    res = await client.post("/buyers/register", json=payload, headers=headers)
    assert res.status_code == 200
    b_data = res.json()
    assert b_data["verification_status"] == "pending"

    # Verify database record is encrypted
    buyer_db = await db_session.scalar(
        select(BuyerProfile).where(BuyerProfile.id == b_data["id"])
    )
    assert buyer_db is not None
    assert buyer_db.encrypted_gst_number != raw_gst
    assert decrypt_document_data(buyer_db.encrypted_gst_number or "") == raw_gst
    assert decrypt_document_data(buyer_db.encrypted_document_ref or "") == raw_doc


@pytest.mark.asyncio
async def test_admin_can_view_pending_and_verify_buyer(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Admin can decrypt proofs and verify buyer accounts."""
    # 1. Seed admin
    admin = User(phone="9999900001", role="admin", language="en")
    # 2. Seed pending buyer
    buyer_user = User(phone="9848044444", role="buyer", language="te")
    db_session.add_all([admin, buyer_user])
    await db_session.flush()

    from backend.app.services.security import encrypt_document_data

    buyer = BuyerProfile(
        user_id=buyer_user.id,
        business_name="Krishna Grand Hotel",
        business_type="hotel",
        verification_status="pending",
        encrypted_gst_number=encrypt_document_data("37BBBBB1111B2Z6"),
        encrypted_document_ref=encrypt_document_data("doc_ref_123"),
        address="Besant Road, Vijayawada",
        district="NTR",
        latitude=16.5062,
        longitude=80.6480,
    )
    db_session.add(buyer)
    await db_session.commit()

    admin_token = create_access_token(admin.id, admin.phone, "admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Admin lists pending buyers
    pending_res = await client.get("/admin/buyers/pending", headers=admin_headers)
    assert pending_res.status_code == 200
    pending_list = pending_res.json()
    assert len(pending_list) >= 1
    assert pending_list[0]["decrypted_gst_number"] == "37BBBBB1111B2Z6"

    # Admin verifies buyer
    verify_res = await client.post(
        f"/admin/buyers/{buyer.id}/verify",
        json={"decision": "verified", "notes": "GST verified on portal"},
        headers=admin_headers,
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["verification_status"] == "verified"


@pytest.mark.asyncio
async def test_fresh_listing_creation_and_checklist_validation(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Farmer creates listing with fresh media and 3-photo checklist."""
    farmer = User(phone="9848055555", role="farmer", language="te")
    db_session.add(farmer)
    await db_session.commit()

    token = create_access_token(farmer.id, farmer.phone, "farmer")
    headers = {"Authorization": f"Bearer {token}"}

    now = datetime.now(UTC)
    payload = {
        "crop_id": "banana",
        "variety": "Robusta",
        "quantity_kg": 500.0,
        "grade": "A",
        "harvest_date": (now - timedelta(days=1)).date().isoformat(),
        "expected_price_kg": 24.50,
        "district": "Guntur",
        "latitude": 16.3067,
        "longitude": 80.4365,
        "media_checklist": {
            "whole_lot": "https://cdn.growcircle.in/lots/lot_01.jpg",
            "close_up": "https://cdn.growcircle.in/lots/close_01.jpg",
            "opened_crate": "https://cdn.growcircle.in/lots/crate_01.jpg",
        },
        "media_captured_at": (now - timedelta(hours=2)).isoformat(),
    }

    res = await client.post("/listings", json=payload, headers=headers)
    assert res.status_code == 200
    l_data = res.json()
    assert l_data["grade"] == "A"
    assert "Premium" in l_data["grade_description"]
    assert l_data["quantity_kg"] == 500.0


@pytest.mark.asyncio
async def test_listing_rejects_stale_gallery_photos(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Rejects photo uploads captured older than 24 hours."""
    farmer = User(phone="9848066666", role="farmer", language="te")
    db_session.add(farmer)
    await db_session.commit()

    token = create_access_token(farmer.id, farmer.phone, "farmer")
    headers = {"Authorization": f"Bearer {token}"}

    now = datetime.now(UTC)
    stale_capture = now - timedelta(hours=36)  # 36 hours old!

    payload = {
        "crop_id": "banana",
        "variety": "Robusta",
        "quantity_kg": 300.0,
        "grade": "B",
        "harvest_date": now.date().isoformat(),
        "expected_price_kg": 22.0,
        "district": "Guntur",
        "latitude": 16.3067,
        "longitude": 80.4365,
        "media_checklist": {
            "whole_lot": "url1",
            "close_up": "url2",
            "opened_crate": "url3",
        },
        "media_captured_at": stale_capture.isoformat(),
    }

    res = await client.post("/listings", json=payload, headers=headers)
    assert res.status_code == 400
    assert "older than 24 hours" in res.json()["detail"]


@pytest.mark.asyncio
async def test_listing_rejects_incomplete_photo_checklist(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Rejects produce listing missing any of the 3 required photo views."""
    farmer = User(phone="9848077777", role="farmer", language="te")
    db_session.add(farmer)
    await db_session.commit()

    token = create_access_token(farmer.id, farmer.phone, "farmer")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "crop_id": "banana",
        "variety": "Robusta",
        "quantity_kg": 300.0,
        "grade": "B",
        "harvest_date": date.today().isoformat(),
        "expected_price_kg": 22.0,
        "district": "Guntur",
        "latitude": 16.3067,
        "longitude": 80.4365,
        "media_checklist": {
            "whole_lot": "url1",
            "close_up": "url2",
            # Missing 'opened_crate'!
        },
        "media_captured_at": datetime.now(UTC).isoformat(),
    }

    res = await client.post("/listings", json=payload, headers=headers)
    assert res.status_code == 400
    assert "Missing required photo for 'opened_crate'" in res.json()["detail"]


@pytest.mark.asyncio
async def test_matching_buyers_and_group_supply_aggregation(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Matching engine ranks buyers and bundles multi-farmer group supply within 50 km."""
    # Seed 1 institutional buyer needing 1,000 kg banana weekly
    b_user = User(phone="9848088888", role="buyer", language="en")
    f_user1 = User(phone="9848088881", role="farmer", language="te")
    f_user2 = User(phone="9848088882", role="farmer", language="te")
    db_session.add_all([b_user, f_user1, f_user2])
    await db_session.flush()

    buyer = BuyerProfile(
        user_id=b_user.id,
        business_name="Andhra Loyola College Canteen",
        business_type="college",
        verification_status="verified",
        reliability_score=4.9,
        address="Vijayawada",
        district="NTR",
        latitude=16.5062,
        longitude=80.6480,
    )
    db_session.add(buyer)
    await db_session.flush()

    need = BuyerNeed(
        buyer_id=buyer.id,
        crop_id="banana",
        quantity_kg=1000.0,
        frequency="weekly",
        preferred_grade="A",
        start_date=date.today(),
        district="NTR",
        latitude=16.5062,
        longitude=80.6480,
    )
    db_session.add(need)

    # Seed 2 nearby farmer listings (600 kg and 500 kg, ~25 km away in Guntur)
    now = datetime.now(UTC)
    l1 = Listing(
        farmer_id=f_user1.id,
        crop_id="banana",
        variety="Robusta",
        quantity_kg=600.0,
        grade="A",
        harvest_date=date.today(),
        expected_price_kg=24.0,
        district="Guntur",
        latitude=16.3067,
        longitude=80.4365,
        media_checklist={"whole_lot": "u1", "close_up": "u2", "opened_crate": "u3"},
        media_captured_at=now,
    )
    l2 = Listing(
        farmer_id=f_user2.id,
        crop_id="banana",
        variety="Robusta",
        quantity_kg=500.0,
        grade="A",
        harvest_date=date.today(),
        expected_price_kg=25.0,
        district="Guntur",
        latitude=16.3067,
        longitude=80.4365,
        media_checklist={"whole_lot": "u4", "close_up": "u5", "opened_crate": "u6"},
        media_captured_at=now,
    )
    db_session.add_all([l1, l2])
    await db_session.commit()

    # Query group supply aggregation endpoint
    res = await client.get(f"/needs/{need.id}/group-supply")
    assert res.status_code == 200
    group = res.json()
    assert group["target_quantity_kg"] == 1000.0
    assert group["bundled_quantity_kg"] == 1000.0
    assert group["is_fully_fulfilled"] is True
    assert group["farmers_count"] == 2
    # Weighted average price: (600*24 + 400*25) / 1000 = 24.40
    assert group["weighted_average_price_kg"] == 24.40


@pytest.mark.asyncio
async def test_negotiation_counter_and_accept_creates_deal(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Full negotiation lifecycle: offer -> counter -> accept -> Deal created with OTP."""
    b_user = User(phone="9848012341", role="buyer", language="te")
    f_user = User(phone="9848012342", role="farmer", language="te")
    db_session.add_all([b_user, f_user])
    await db_session.flush()

    buyer = BuyerProfile(
        user_id=b_user.id,
        business_name="Amaravati Mess",
        business_type="hotel",
        verification_status="verified",
        address="Guntur",
        district="Guntur",
        latitude=16.3067,
        longitude=80.4365,
    )
    db_session.add(buyer)

    listing = Listing(
        farmer_id=f_user.id,
        crop_id="banana",
        variety="Amruthapani",
        quantity_kg=400.0,
        grade="A",
        harvest_date=date.today(),
        expected_price_kg=26.0,
        district="Guntur",
        latitude=16.3067,
        longitude=80.4365,
        media_checklist={"whole_lot": "u1", "close_up": "u2", "opened_crate": "u3"},
        media_captured_at=datetime.now(UTC),
    )
    db_session.add(listing)
    await db_session.commit()

    # 1. Buyer makes offer: ₹23/kg
    buyer_token = create_access_token(b_user.id, b_user.phone, "buyer")
    b_headers = {"Authorization": f"Bearer {buyer_token}"}

    offer_res = await client.post(
        "/offers",
        json={"listing_id": listing.id, "offered_price_kg": 23.0, "quantity_kg": 400.0},
        headers=b_headers,
    )
    assert offer_res.status_code == 200
    offer_id = offer_res.json()["id"]

    # 2. Farmer counters: ₹24.50/kg
    farmer_token = create_access_token(f_user.id, f_user.phone, "farmer")
    f_headers = {"Authorization": f"Bearer {farmer_token}"}

    counter_res = await client.post(
        f"/offers/{offer_id}/action",
        json={"action": "counter", "counter_price_kg": 24.50, "confirmed_readback": True},
        headers=f_headers,
    )
    assert counter_res.status_code == 200
    assert counter_res.json()["status"] == "countered"

    # 3. Buyer accepts counter: ₹24.50/kg with readback confirmation
    accept_res = await client.post(
        f"/offers/{offer_id}/action",
        json={"action": "accept", "confirmed_readback": True},
        headers=b_headers,
    )
    assert accept_res.status_code == 200
    deal_info = accept_res.json()
    assert deal_info["status"] == "accepted"
    assert "deal_id" in deal_info
    assert len(deal_info["pickup_otp"]) == 4

    # Verify Deal in database
    deal_db = await db_session.scalar(select(Deal).where(Deal.id == deal_info["deal_id"]))
    assert deal_db is not None
    assert deal_db.agreed_price_kg == 24.50
    assert deal_db.status == "confirmed"

    # 4. Complete deal with pickup OTP
    comp_res = await client.post(
        f"/deals/{deal_db.id}/complete",
        params={"otp": deal_db.pickup_otp},
    )
    assert comp_res.status_code == 200
    assert comp_res.json()["status"] == "completed"

    # 5. Farmer rates buyer 5 stars
    rate_res = await client.post(
        "/ratings",
        json={
            "deal_id": deal_db.id,
            "score": 5,
            "reliability_tag": "prompt_pickup",
            "comment": "Quick payment and prompt vehicle arrival.",
        },
        headers=f_headers,
    )
    assert rate_res.status_code == 200
    assert rate_res.json()["score"] == 5


@pytest.mark.asyncio
async def test_masked_call_connection_bridges_numbers(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Masked call bridge connects parties without exposing real numbers."""
    u1 = User(phone="9848099111", role="farmer", language="te")
    u2 = User(phone="9848099222", role="buyer", language="te")
    db_session.add_all([u1, u2])
    await db_session.commit()

    token = create_access_token(u1.id, u1.phone, "farmer")
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.post(
        "/telephony/masked-call",
        json={"callee_user_id": u2.id},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "connecting"
    assert "bridge_id" in data
    assert "personal number remains private" in data["message"]
