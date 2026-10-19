"""
Tests for OTP Security, Error Handling, and Hardening:
1. Dynamic 6-digit random code generation (using secrets, leading zeros, differing codes).
2. HMAC-SHA256 storage (never plaintext in cache).
3. 30-second server-side resend cooldown (returns 429 with Retry-After).
4. Max 5 verification attempts lockout.
5. Single-use deletion and reuse prevention.
6. Structured JSON error responses (no bare 500s).
7. Phone number normalization (handling +91, spaces, 10 digits).
"""

import hmac
import hashlib
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.rate_limit import in_memory_limiter
from backend.app.services.security import (
    _LOCKOUT_CACHE,
    _OTP_CACHE,
    _SEND_TRACKER,
    clear_all_otp_locks,
    generate_and_send_phone_otp_async,
    verify_phone_otp,
    normalize_phone,
)


@pytest.fixture(autouse=True)
def reset_auth_state():
    clear_all_otp_locks()
    in_memory_limiter.reset()
    yield
    clear_all_otp_locks()
    in_memory_limiter.reset()


def test_phone_normalization():
    assert normalize_phone("+91 98765 43210") == "9876543210"
    assert normalize_phone("919876543210") == "9876543210"
    assert normalize_phone("09876543210") == "9876543210"
    assert normalize_phone("9876543210") == "9876543210"
    assert normalize_phone("+91-98765-43210") == "9876543210"


@pytest.mark.asyncio
async def test_otp_is_random_and_varies():
    """Verify code is 6 digits, varies between calls, and never static 123456."""
    codes = set()
    for _ in range(5):
        clear_all_otp_locks()
        code, _ = await generate_and_send_phone_otp_async("9876543210")
        assert len(code) == 6
        assert code.isdigit()
        codes.add(code)
    # 5 random 6-digit codes must have at least 3 distinct values
    assert len(codes) >= 3
    # Cache must store HMAC hash, not plaintext code
    cached_record = _OTP_CACHE.get("9876543210")
    assert "otp_hash" in cached_record
    assert cached_record.get("otp") is None  # Never plaintext


@pytest.mark.asyncio
async def test_resend_cooldown_returns_429(client: AsyncClient):
    """Enforce 30s server-side cooldown returning 429 with retry_after."""
    phone = "9876543210"
    # First send: 200 OK
    res1 = await client.post("/auth/send-otp", json={"phone": phone})
    assert res1.status_code == 200

    # Second immediate send: 429 Too Many Requests
    res2 = await client.post("/auth/send-otp", json={"phone": phone})
    assert res2.status_code == 429
    data = res2.json()
    assert "retry_after" in data or "Retry-After" in res2.headers


@pytest.mark.asyncio
async def test_otp_single_use_and_reuse_prevention(client: AsyncClient, db_session: AsyncSession):
    """Once verified, OTP is deleted and cannot be reused."""
    phone = "9876543211"
    send_res = await client.post("/auth/send-otp", json={"phone": phone})
    assert send_res.status_code == 200
    otp = send_res.json().get("sandbox_otp") or send_res.json().get("dev_otp")

    # First verification succeeds
    v_res1 = await client.post(
        "/auth/verify-otp",
        json={"phone": phone, "otp": otp, "name": "Ravi", "role": "farmer"},
    )
    assert v_res1.status_code == 200

    # Second verification fails (code was deleted)
    v_res2 = await client.post(
        "/auth/verify-otp",
        json={"phone": phone, "otp": otp, "name": "Ravi", "role": "farmer"},
    )
    assert v_res2.status_code in (400, 422)


@pytest.mark.asyncio
async def test_five_wrong_attempts_trigger_lockout(client: AsyncClient):
    """5 consecutive failed attempts lock device/account."""
    phone = "9876543212"
    await client.post("/auth/send-otp", json={"phone": phone})

    for attempt in range(4):
        res = await client.post(
            "/auth/verify-otp",
            json={"phone": phone, "otp": "000000", "role": "farmer"},
        )
        assert res.status_code == 400

    # 5th attempt locks
    res5 = await client.post(
        "/auth/verify-otp",
        json={"phone": phone, "otp": "000000", "role": "farmer"},
    )
    assert res5.status_code in (400, 429)

    # 6th attempt is blocked with 429
    res6 = await client.post(
        "/auth/verify-otp",
        json={"phone": phone, "otp": "000000", "role": "farmer"},
    )
    assert res6.status_code == 429
