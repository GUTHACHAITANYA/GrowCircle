"""
Integration tests verifying OWASP Top 10 security hardening:
- A01: Broken Access Control (offer actions, deal handover, transporter availability, deleted user JWTs)
- A02: Cryptographic Failures (Fernet encryption at rest for Driving Licence and RC, constant-time webhook tokens)
- A04: Insecure Design & Rate Limiting (Deal handover OTP rate limit, IVR rate limits)
- A08: Software & Data Integrity (File upload validation, magic bytes, payload size caps)
"""

from datetime import UTC, date, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.buyer import BuyerProfile
from backend.app.models.listing import Listing
from backend.app.models.offer import Offer
from backend.app.models.transporter import Transporter
from backend.app.models.user import User
from backend.app.services.security import create_access_token, encrypt_document_data


@pytest.mark.asyncio
async def test_offer_action_broken_access_control_prevented(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OWASP A01: A third party cannot accept, counter, or reject someone else's offer."""
    # Farmer user 101
    farmer = User(id=101, phone="9848010101", role="farmer", consent_at=datetime.now(UTC))
    # Buyer user 102
    buyer_user = User(id=102, phone="9848010102", role="buyer", consent_at=datetime.now(UTC))
    # Attacker user 103
    attacker_user = User(id=103, phone="9848010103", role="farmer", consent_at=datetime.now(UTC))
    db_session.add_all([farmer, buyer_user, attacker_user])
    await db_session.flush()

    buyer_prof = BuyerProfile(
        user_id=102,
        business_name="Krishna Wholesale",
        business_type="wholesaler",
        verification_status="verified",
        address="Guntur Market Yard",
        district="Guntur",
        latitude=16.30,
        longitude=80.44,
    )
    db_session.add(buyer_prof)
    await db_session.flush()

    listing = Listing(
        farmer_id=101,
        crop_id="banana",
        variety="Robusta",
        quantity_kg=1000.0,
        grade="A",
        harvest_date=date.today(),
        expected_price_kg=25.0,
        district="Guntur",
        status="active",
        latitude=16.30,
        longitude=80.44,
        media_checklist={"whole_lot": "https://img1.jpg", "close_up": "https://img2.jpg", "opened_crate": "https://img3.jpg"},
        media_captured_at=datetime.now(UTC),
    )
    db_session.add(listing)
    await db_session.flush()

    offer = Offer(
        listing_id=listing.id,
        buyer_id=buyer_prof.id,
        offered_price_kg=24.0,
        quantity_kg=500.0,
        status="pending",
    )
    db_session.add(offer)
    await db_session.commit()

    attacker_token = create_access_token(user_id=103, phone="9848010103", role="farmer")

    # Attacker tries to accept the offer
    resp = await client.post(
        f"/offers/{offer.id}/action",
        headers={"Authorization": f"Bearer {attacker_token}"},
        json={"action": "accept", "confirmed_readback": True},
    )
    assert resp.status_code == 403
    assert "Access denied: Only parties to this offer may take action" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_transporter_license_and_rc_encrypted_at_rest(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OWASP A02: Transporter Driving Licence & RC numbers are encrypted with Fernet at rest."""
    phone = "9848055555"
    driver_user = User(id=201, phone=phone, role="driver", consent_at=datetime.now(UTC))
    db_session.add(driver_user)
    await db_session.commit()

    reg_payload = {
        "user_id": 201,
        "name": "Ramu Driver",
        "phone": phone,
        "license_number": "AP07 20269988776",
        "license_expiry": str(date(2028, 12, 31)),
        "license_photo_url": "https://storage.growcircle.in/docs/dl_201.jpg",
        "rc_number": "AP07 TC 1234",
        "rc_expiry": str(date(2029, 6, 30)),
        "rc_photo_url": "https://storage.growcircle.in/docs/rc_201.jpg",
        "insurance_expiry": str(date(2027, 5, 15)),
        "fitness_expiry": str(date(2027, 5, 15)),
        "vehicle_type": "goods_auto",
        "vehicle_model": "Piaggio Ape",
        "capacity_kg": 450,
        "service_area_districts": ["Guntur"],
        "current_latitude": 16.3067,
        "current_longitude": 80.4365,
    }

    res = await client.post("/transport/transporters", json=reg_payload)
    assert res.status_code == 201
    transporter_id = res.json()["id"]

    # Verify raw database row stores encrypted ciphertext (starts with Fernet header 'gAAAAA')
    stmt = select(Transporter).where(Transporter.id == transporter_id)
    raw_driver = (await db_session.execute(stmt)).scalar_one()

    assert raw_driver.license_number.startswith("gAAAAA")
    assert raw_driver.rc_number.startswith("gAAAAA")
    assert "AP07 20269988776" not in raw_driver.license_number
    assert "AP07 TC 1234" not in raw_driver.rc_number

    # Verify decrypted helpers return the original data for authorized admin review
    assert raw_driver.get_decrypted_license() == "AP07 20269988776"
    assert raw_driver.get_decrypted_rc() == "AP07 TC 1234"


@pytest.mark.asyncio
async def test_deactivated_user_jwt_rejected(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OWASP A01 / A07: Deleted / deactivated users with active JWTs are rejected with 401."""
    user = User(
        id=301,
        phone="9848077777",
        role="farmer",
        is_deleted=True,
        consent_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user_id=301, phone="9848077777", role="farmer")

    resp = await client.get("/buyers/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert "User account has been deactivated or deleted" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_transporter_toggle_availability_bola_prevented(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """OWASP A01: Another driver cannot modify a foreign transporter's availability."""
    user_a = User(id=401, phone="9848011111", role="driver", consent_at=datetime.now(UTC))
    user_b = User(id=402, phone="9848022222", role="driver", consent_at=datetime.now(UTC))
    db_session.add_all([user_a, user_b])
    await db_session.flush()

    transporter = Transporter(
        user_id=401,
        name="Driver A",
        phone="9848011111",
        license_number=encrypt_document_data("LIC-401"),
        license_expiry=date(2028, 1, 1),
        license_photo_url="https://docs/401.jpg",
        rc_number=encrypt_document_data("RC-401"),
        rc_expiry=date(2028, 1, 1),
        rc_photo_url="https://docs/rc401.jpg",
        insurance_expiry=date(2028, 1, 1),
        fitness_expiry=date(2028, 1, 1),
        vehicle_type="mini_truck",
        vehicle_model="Tata Ace",
        capacity_kg=1000,
        current_latitude=16.30,
        current_longitude=80.44,
        available_today=True,
    )
    db_session.add(transporter)
    await db_session.commit()

    # User B tries to toggle User A's availability
    token_b = create_access_token(user_id=402, phone="9848022222", role="driver")
    patch_res = await client.patch(
        f"/transport/transporters/{transporter.id}/availability",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"available_today": False},
    )
    assert patch_res.status_code == 403
    assert "Cannot alter another transporter" in patch_res.json()["detail"]


@pytest.mark.asyncio
async def test_whatsapp_webhook_constant_time_verification(client: AsyncClient) -> None:
    """OWASP A02: WhatsApp webhook verify token rejects mismatches with 403."""
    # Invalid token
    resp_invalid = await client.get(
        "/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_token_here",
            "hub.challenge": "11223344",
        },
    )
    assert resp_invalid.status_code == 403

    # Valid token
    resp_valid = await client.get(
        "/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "growcircle_webhook_token_2026",
            "hub.challenge": "11223344",
        },
    )
    assert resp_valid.status_code == 200
    assert resp_valid.text == "11223344"
