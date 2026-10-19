"""
Tests for Sign-In Flow Hardening:
1. Dev lock clearance and lock storage location.
2. Demo mode OTP logging & Dev OTP hints vs production secrecy.
3. Separate counters: 30s resend cooldown, daily cap, 5 verification attempts per code with attempts countdown.
4. Third-party protection: Lockout scoped by phone + device/IP so third party cannot lock legitimate user.
5. Public roles (farmer, buyer, transporter, consumer) only; buyer/transporter pending verification; admin creation guard.
6. Provider status (real SMS/WhatsApp vs demo simulation).
"""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.rate_limit import in_memory_limiter
from backend.app.models.user import User
from backend.app.services.security import (
    _LOCKOUT_CACHE,
    _OTP_CACHE,
    _SEND_TRACKER,
    clear_all_otp_locks,
    create_access_token,
    get_lock_status,
)


@pytest.fixture(autouse=True)
def reset_auth_caches():
    """Ensure clean state before and after each test."""
    clear_all_otp_locks()
    in_memory_limiter.reset()
    yield
    clear_all_otp_locks()
    in_memory_limiter.reset()


@pytest.mark.asyncio
async def test_dev_clear_lock_endpoint_and_python_helper(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Requirement 1: Verify OTP lock storage and clearance in development/demo mode."""
    phone = "9111222333"
    client_ip = "127.0.0.1"

    # Send OTP
    send_res = await client.post("/auth/send-otp", json={"phone": phone})
    assert send_res.status_code == 200

    # Fail 5 times to trigger lock
    for _ in range(5):
        await client.post(
            "/auth/verify-otp",
            json={"phone": phone, "otp": "000000", "role": "farmer"},
        )

    # 6th attempt is locked
    locked_res = await client.post(
        "/auth/verify-otp",
        json={"phone": phone, "otp": "000000", "role": "farmer"},
    )
    assert locked_res.status_code == 429
    is_locked, rem_secs = get_lock_status(phone, client_ip)
    assert is_locked
    assert rem_secs > 0

    # Clear via API endpoint
    clear_res = await client.post("/auth/dev/clear-lock", json={"phone": phone})
    assert clear_res.status_code == 200
    assert clear_res.json()["status"] == "success"

    # Verify device/phone is unlocked immediately
    is_locked_after, _ = get_lock_status(phone, client_ip)
    assert not is_locked_after

    # In production mode: endpoint must return 403 Forbidden
    with patch.object(settings, "ENVIRONMENT", "production"), patch.object(
        settings, "APP_MODE", "production"
    ):
        prod_clear = await client.post("/auth/dev/clear-lock", json={"phone": phone})
        assert prod_clear.status_code == 403


@pytest.mark.asyncio
async def test_demo_mode_vs_production_otp_exposure(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    """Requirement 2: In demo mode show dev OTP; in production mode NEVER show or log OTP."""
    phone = "9222333444"

    # 1. Demo Mode
    with caplog.at_level("INFO"):
        res_demo = await client.post("/auth/send-otp", json={"phone": phone})
        assert res_demo.status_code == 200
        data_demo = res_demo.json()
        assert "dev_otp" in data_demo
        assert "sandbox_otp" in data_demo
        assert len(data_demo["dev_otp"]) == 6
        assert data_demo["dev_otp"].isdigit()
        assert "[DEMO OTP]" in caplog.text

    # Clear for production test
    clear_all_otp_locks()
    caplog.clear()

    # 2. Production Mode Simulation
    with patch.object(settings, "ENVIRONMENT", "production"), patch.object(
        settings, "APP_MODE", "production"
    ), caplog.at_level("INFO"):
        res_prod = await client.post("/auth/send-otp", json={"phone": phone})
        assert res_prod.status_code == 200
        data_prod = res_prod.json()
        # In production NEVER return dev_otp or sandbox_otp
        assert "dev_otp" not in data_prod
        assert "sandbox_otp" not in data_prod
        assert "is_demo" not in data_prod
        # In production NEVER log plain OTP
        assert "[AUTH DEMO]" not in caplog.text
        assert "123456" not in caplog.text
        assert "[AUTH] Dispatched OTP to +91 ******3444" in caplog.text


@pytest.mark.asyncio
async def test_separate_counters_resend_cooldown_and_daily_cap(client: AsyncClient) -> None:
    """Requirement 3: Separate send counter with 30s resend cooldown and daily cap."""
    phone = "9333444555"

    # Send 1: Success
    res1 = await client.post("/auth/send-otp", json={"phone": phone})
    assert res1.status_code == 200
    assert res1.json()["resend_cooldown_seconds"] == 30

    # Send 2 immediately: Blocked by 30s cooldown
    res2 = await client.post("/auth/send-otp", json={"phone": phone})
    assert res2.status_code == 429
    assert "cooldown active" in res2.json()["detail"].lower()
    assert "Retry-After" in res2.headers

    # Simulate exhausting daily cap (10 requests)
    now = datetime.now(UTC)
    _SEND_TRACKER[phone] = {
        "last_sent_at": None,  # no cooldown blocking
        "daily_sends": [now] * 10,
    }

    res_cap = await client.post("/auth/send-otp", json={"phone": phone})
    assert res_cap.status_code == 429
    assert "daily" in res_cap.json()["detail"].lower()


@pytest.mark.asyncio
async def test_attempts_left_and_third_party_lockout_isolation(client: AsyncClient) -> None:
    """Requirement 3: 5 attempts countdown per code and prevent third-party lockouts."""
    alice_phone = "9444555666"

    # Send code for Alice
    send_res = await client.post("/auth/send-otp", json={"phone": alice_phone})
    assert send_res.status_code == 200
    valid_otp = send_res.json()["dev_otp"]

    # Attacker Eve from IP 198.51.100.99 submits wrong OTPs
    attacker_headers = {"X-Forwarded-For": "198.51.100.99"}

    for i in range(1, 5):
        fail = await client.post(
            "/auth/verify-otp",
            json={"phone": alice_phone, "otp": "000000", "role": "farmer"},
            headers=attacker_headers,
        )
        assert fail.status_code == 400
        # Verification reports remaining attempts
        assert f"{5 - i} attempt(s) remaining" in fail.json()["detail"]

    # 5th failed attempt from attacker
    fail5 = await client.post(
        "/auth/verify-otp",
        json={"phone": alice_phone, "otp": "000000", "role": "farmer"},
        headers=attacker_headers,
    )
    assert fail5.status_code == 400
    assert "0 attempt(s) remaining" in fail5.json()["detail"]

    # 6th attempt from attacker is locked
    locked_eve = await client.post(
        "/auth/verify-otp",
        json={"phone": alice_phone, "otp": "000000", "role": "farmer"},
        headers=attacker_headers,
    )
    assert locked_eve.status_code == 429
    assert "locked" in locked_eve.json()["detail"].lower()

    # LEGITIMATE USER ALICE from IP 203.0.113.10 is NOT locked out!
    alice_headers = {"X-Forwarded-For": "203.0.113.10"}
    is_alice_locked, _ = get_lock_status(alice_phone, "203.0.113.10")
    assert not is_alice_locked

    # Alice requests a fresh code for herself and logs in
    _SEND_TRACKER[alice_phone]["last_sent_at"] = None  # simulate 30s elapsed
    alice_send = await client.post(
        "/auth/send-otp", json={"phone": alice_phone}, headers=alice_headers
    )
    assert alice_send.status_code == 200
    new_otp = alice_send.json()["dev_otp"]

    alice_verify = await client.post(
        "/auth/verify-otp",
        json={"phone": alice_phone, "otp": new_otp, "role": "farmer"},
        headers=alice_headers,
    )
    assert alice_verify.status_code == 200
    assert alice_verify.json()["access_token"]


@pytest.mark.asyncio
async def test_public_roles_and_admin_creation_guard(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Requirement 5: Public roles only; admin cannot be self-registered."""
    phone = "9555666777"
    send_res = await client.post("/auth/send-otp", json={"phone": phone})
    otp = send_res.json()["dev_otp"]

    # Self-registering as admin must be rejected
    admin_signup = await client.post(
        "/auth/verify-otp",
        json={"phone": phone, "otp": otp, "role": "admin"},
    )
    assert admin_signup.status_code == 403
    assert "admin accounts cannot be self-registered" in admin_signup.json()["detail"].lower()

    # Public roles succeed
    for r in ["farmer", "buyer", "driver", "consumer"]:
        clear_all_otp_locks()
        s_res = await client.post("/auth/send-otp", json={"phone": phone})
        r_otp = s_res.json()["dev_otp"]
        res = await client.post(
            "/auth/verify-otp",
            json={"phone": phone, "otp": r_otp, "role": r},
        )
        assert res.status_code == 200

    # Test Admin creating another Admin via /auth/admin/create-admin
    # Create master admin user
    master_admin = User(
        phone="9000000000",
        role="admin",
        name="Master Admin",
        is_admin_2fa_verified=True,
        session_version=1,
    )
    db_session.add(master_admin)
    await db_session.commit()
    await db_session.refresh(master_admin)

    admin_token = create_access_token(
        user_id=master_admin.id,
        phone=master_admin.phone,
        role="admin",
        session_version=1,
        is_admin_2fa=True,
    )

    new_admin_phone = "9888899999"
    create_res = await client.post(
        "/auth/admin/create-admin",
        json={"phone": new_admin_phone, "name": "Sub-Admin", "district": "Guntur"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_res.status_code == 200
    assert create_res.json()["status"] == "success"

    # Now the provisioned admin CAN verify as admin
    clear_all_otp_locks()
    s_admin = await client.post("/auth/send-otp", json={"phone": new_admin_phone})
    admin_otp = s_admin.json()["dev_otp"]
    login_admin = await client.post(
        "/auth/verify-otp",
        json={"phone": new_admin_phone, "otp": admin_otp, "role": "admin"},
    )
    assert login_admin.status_code == 200
    assert login_admin.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_buyer_and_transporter_stay_pending_verification(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Requirement 5: Buyer and transporter stay 'pending verification' until approved."""
    # Farmer: auto-verified
    f_phone = "9666777888"
    s_f = await client.post("/auth/send-otp", json={"phone": f_phone})
    f_otp = s_f.json()["dev_otp"]
    f_res = await client.post(
        "/auth/verify-otp", json={"phone": f_phone, "otp": f_otp, "role": "farmer"}
    )
    assert f_res.json()["verification_status"] == "verified"
    assert f_res.json()["is_verified"] is True

    # Buyer: stays pending verification
    clear_all_otp_locks()
    b_phone = "9777888999"
    s_b = await client.post("/auth/send-otp", json={"phone": b_phone})
    b_otp = s_b.json()["dev_otp"]
    b_res = await client.post(
        "/auth/verify-otp", json={"phone": b_phone, "otp": b_otp, "role": "buyer"}
    )
    assert b_res.json()["verification_status"] == "pending"
    assert b_res.json()["is_verified"] is False

    # Transporter (Driver): stays pending verification
    clear_all_otp_locks()
    d_phone = "9888999000"
    s_d = await client.post("/auth/send-otp", json={"phone": d_phone})
    d_otp = s_d.json()["dev_otp"]
    d_res = await client.post(
        "/auth/verify-otp", json={"phone": d_phone, "otp": d_otp, "role": "driver"}
    )
    assert d_res.json()["verification_status"] == "pending"
    assert d_res.json()["is_verified"] is False


@pytest.mark.asyncio
async def test_provider_status_endpoint(client: AsyncClient) -> None:
    """Requirement 6: Verify provider status returns real vs demo mode."""
    # Demo mode check
    res = await client.get("/auth/provider-status")
    assert res.status_code == 200
    data = res.json()
    assert data["is_real_provider"] is False
    assert data["provider_type"] == "mock"

    # Real provider check
    with patch.object(settings, "APP_MODE", "production"), patch.object(
        settings, "ENVIRONMENT", "production"
    ), patch.object(settings, "SMS_API_KEY", "real-sms-key-123"):
        real_res = await client.get("/auth/provider-status")
        assert real_res.status_code == 200
        real_data = real_res.json()
        assert real_data["is_real_provider"] is True
        assert real_data["provider_type"] == "sms"
