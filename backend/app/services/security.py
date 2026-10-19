"""
Security, Authentication, and DPDP Act compliance service.
- Fernet symmetric encryption for sensitive documents and GST numbers.
- Phone-OTP authentication with provider interface (SMS/WhatsApp/Mock in demo).
- Expiring codes (5 minutes), rate limiting, and failure lockouts (15 minutes).
- JWT role-based access control with session version tracking ("log out of all devices").
- 2FA enforcement for administrative access.
"""

import base64
import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import jwt
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.db.session import get_async_db
from backend.app.models.user import User
from backend.app.services.otp import get_otp_provider, is_real_otp_provider_configured

logger = logging.getLogger(__name__)

security_scheme = HTTPBearer(auto_error=False)

# Derive 32-byte Fernet key deterministically from app SECRET_KEY
_hashed_key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
_fernet_key = base64.urlsafe_b64encode(_hashed_key)
fernet = Fernet(_fernet_key)

# In-memory OTP storage: {clean_phone: {"otp": str, "expires_at": datetime, "attempts": int, "created_at": datetime}}
_OTP_CACHE: dict[str, dict] = {}

# Account lock tracker: {lock_key: {"failed_count": int, "locked_until": datetime | None}}
# lock_key is "{clean_phone}:{client_ip}" to prevent 3rd party lockouts of someone else's account
_LOCKOUT_CACHE: dict[str, dict] = {}

# OTP Send tracker: {clean_phone: {"last_sent_at": datetime, "daily_sends": list[datetime]}}
_SEND_TRACKER: dict[str, dict] = {}

OTP_EXPIRY_MINUTES = 5
LOCKOUT_MINUTES = 15
MAX_FAILED_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 30
DAILY_SEND_CAP = 10


def encrypt_document_data(plain_text: str) -> str:
    """Encrypts sensitive personal/business information at rest (DPDP Act)."""
    if not plain_text:
        return ""
    return fernet.encrypt(plain_text.encode("utf-8")).decode("utf-8")


def decrypt_document_data(cipher_text: str) -> str:
    """Decrypts sensitive document data for authorized admin review."""
    if not cipher_text:
        return ""
    try:
        if cipher_text.startswith("gAAAAA"):
            return fernet.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
        return cipher_text
    except Exception:
        return cipher_text


def get_lock_status(clean_phone: str, client_ip: str | None = None) -> tuple[bool, int]:
    """
    Checks lock status for a phone + device/IP combination.
    Prevents a malicious third party on IP A from locking out legitimate user on IP B.
    Returns (is_locked, remaining_seconds).
    """
    now = datetime.now(UTC)
    keys_to_check: list[str] = []
    if client_ip:
        keys_to_check.append(f"{clean_phone}:{client_ip}")
    else:
        keys_to_check.append(clean_phone)

    for key in keys_to_check:
        lock_info = _LOCKOUT_CACHE.get(key)
        if lock_info:
            locked_until = lock_info.get("locked_until")
            if locked_until:
                if now < locked_until:
                    remaining = int((locked_until - now).total_seconds())
                    return True, max(1, remaining)
                else:
                    # Lock has expired
                    del _LOCKOUT_CACHE[key]
    return False, 0


def is_phone_locked(clean_phone: str, client_ip: str | None = None) -> bool:
    """Backward-compatible helper checking whether account is currently locked."""
    locked, _ = get_lock_status(clean_phone, client_ip)
    return locked


def check_send_rate_limits(clean_phone: str, client_ip: str = "127.0.0.1") -> tuple[int, int]:
    """
    Enforces:
    1. 30s resend cooldown per phone number.
    2. Daily send cap (10 requests per 24h) per phone and per IP.
    Returns (resend_cooldown_seconds, daily_sends_remaining).
    """
    now = datetime.now(UTC)
    cutoff_24h = now - timedelta(hours=24)

    record = _SEND_TRACKER.get(clean_phone, {"last_sent_at": None, "daily_sends": []})
    last_sent = record.get("last_sent_at")

    # 1. 30s cooldown check
    if last_sent:
        elapsed = (now - last_sent).total_seconds()
        if elapsed < RESEND_COOLDOWN_SECONDS:
            cooldown_left = int(RESEND_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Resend cooldown active. Please wait {cooldown_left}s before requesting a new code.",
                headers={"Retry-After": str(cooldown_left)},
            )

    # 2. Daily send cap on phone
    daily_sends = [ts for ts in record.get("daily_sends", []) if ts > cutoff_24h]
    record["daily_sends"] = daily_sends
    if len(daily_sends) >= DAILY_SEND_CAP:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily OTP request limit reached ({DAILY_SEND_CAP}/day). Please try again tomorrow.",
        )

    # 3. Daily send cap on IP (prevent bulk automated spam across numbers)
    ip_key = f"ip:{client_ip}"
    ip_record = _SEND_TRACKER.get(ip_key, {"daily_sends": []})
    ip_sends = [ts for ts in ip_record.get("daily_sends", []) if ts > cutoff_24h]
    ip_record["daily_sends"] = ip_sends
    if len(ip_sends) >= DAILY_SEND_CAP * 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily OTP limit exceeded from this device/IP. Please try again tomorrow.",
        )

    remaining_sends = max(0, DAILY_SEND_CAP - len(daily_sends) - 1)
    return RESEND_COOLDOWN_SECONDS, remaining_sends


import hmac
import re

def normalize_phone(phone: str) -> str:
    """
    Normalizes Indian mobile numbers:
    Removes all non-digit characters.
    If 12 digits starting with '91', strips '91'.
    If 11 digits starting with '0', strips '0'.
    Returns cleaned 10-digit string.
    """
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits


def compute_otp_hash(clean_phone: str, otp: str) -> str:
    """Generates server-side HMAC-SHA256 of identifier + OTP."""
    secret = (getattr(settings, "OTP_SECRET", None) or settings.SECRET_KEY).encode("utf-8")
    message = f"{clean_phone}:{otp}".encode("utf-8")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


async def generate_and_send_phone_otp_async(
    phone: str, client_ip: str = "127.0.0.1"
) -> tuple[str, dict[str, Any]]:
    """
    Generates a fresh random 6-digit OTP using secrets module, stores HMAC-SHA256 hash,
    and dispatches via OtpProvider.
    Enforces lockout, 30s resend cooldown, and daily cap.
    In demo mode only: logs OTP in server log. In production: never logs OTP.
    """
    clean_phone = normalize_phone(phone)
    if len(clean_phone) != 10 or clean_phone[0] not in "6789":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please enter a valid 10-digit Indian mobile number (starts with 6-9).",
        )

    # 1. Check lock
    is_locked, remaining_secs = get_lock_status(clean_phone, client_ip)
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Verification temporarily locked on this device. Please wait {remaining_secs} seconds.",
            headers={"Retry-After": str(remaining_secs)},
        )

    # 2. Check send limits
    cooldown, sends_left = check_send_rate_limits(clean_phone, client_ip)

    # 3. Generate random 6-digit code with secrets module (preserves leading zeros)
    otp = f"{secrets.randbelow(1_000_000):06d}"

    is_demo = (
        settings.APP_MODE == "demo"
        or settings.ENVIRONMENT in ("development", "test")
    )
    if is_demo:
        # Demo mode ONLY: show OTP in server log with clear DEV label
        logger.info(f"[DEMO OTP] +91 {clean_phone}: {otp}")
    else:
        masked = f"+91 ******{clean_phone[-4:]}" if len(clean_phone) >= 4 else "+91 ******"
        # Production mode: NEVER show or log the OTP
        logger.info(f"[AUTH] Dispatched OTP to {masked} via configured provider")

    now = datetime.now(UTC)
    _OTP_CACHE[clean_phone] = {
        "otp_hash": compute_otp_hash(clean_phone, otp),
        "expires_at": now + timedelta(minutes=OTP_EXPIRY_MINUTES),
        "attempts": 0,
        "created_at": now,
    }

    # Record send in tracker
    if clean_phone not in _SEND_TRACKER:
        _SEND_TRACKER[clean_phone] = {"last_sent_at": None, "daily_sends": []}
    _SEND_TRACKER[clean_phone]["last_sent_at"] = now
    _SEND_TRACKER[clean_phone]["daily_sends"].append(now)

    ip_key = f"ip:{client_ip}"
    if ip_key not in _SEND_TRACKER:
        _SEND_TRACKER[ip_key] = {"daily_sends": []}
    _SEND_TRACKER[ip_key]["daily_sends"].append(now)

    # Dispatch via OTP Provider
    provider = get_otp_provider()
    await provider.send_otp(clean_phone, otp)

    meta = {
        "resend_cooldown_seconds": cooldown,
        "daily_sends_remaining": sends_left,
        "is_demo": is_demo,
        "is_real_provider": is_real_otp_provider_configured(),
    }
    return otp, meta


def generate_and_send_phone_otp(phone: str, client_ip: str = "127.0.0.1") -> str:
    """Sync wrapper for backward compatibility."""
    import asyncio
    clean_phone = normalize_phone(phone)
    if len(clean_phone) != 10 or clean_phone[0] not in "6789":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please enter a valid 10-digit Indian mobile number (starts with 6-9).",
        )

    is_locked, remaining_secs = get_lock_status(clean_phone, client_ip)
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account temporarily locked due to repeated failed OTP attempts. Please wait {remaining_secs} seconds.",
        )

    check_send_rate_limits(clean_phone, client_ip)

    otp = f"{secrets.randbelow(1_000_000):06d}"
    is_demo = (
        settings.APP_MODE == "demo"
        or settings.ENVIRONMENT in ("development", "test")
    )
    if is_demo:
        logger.info(f"[DEMO OTP] +91 {clean_phone}: {otp}")
    else:
        masked = f"+91 ******{clean_phone[-4:]}" if len(clean_phone) >= 4 else "+91 ******"
        logger.info(f"[AUTH] Dispatched OTP to {masked} via configured provider")

    now = datetime.now(UTC)
    _OTP_CACHE[clean_phone] = {
        "otp_hash": compute_otp_hash(clean_phone, otp),
        "expires_at": now + timedelta(minutes=OTP_EXPIRY_MINUTES),
        "attempts": 0,
        "created_at": now,
    }

    if clean_phone not in _SEND_TRACKER:
        _SEND_TRACKER[clean_phone] = {"last_sent_at": None, "daily_sends": []}
    _SEND_TRACKER[clean_phone]["last_sent_at"] = now
    _SEND_TRACKER[clean_phone]["daily_sends"].append(now)

    provider = get_otp_provider()
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(provider.send_otp(clean_phone, otp))
        else:
            loop.run_until_complete(provider.send_otp(clean_phone, otp))
    except Exception:
        pass

    return otp


def verify_phone_otp(
    phone: str, submitted_otp: str, client_ip: str = "127.0.0.1"
) -> tuple[bool, str, dict[str, Any]]:
    """
    Verifies submitted OTP against HMAC-SHA256 hash using hmac.compare_digest.
    Tracks failed attempts (5 max) per OTP session.
    Locks device/IP + phone combination for 15 minutes after 5 failures.
    Does NOT lock out a third-party legitimate phone from another IP/device.
    Returns: (is_valid, message, metadata_dict)
    """
    clean_phone = normalize_phone(phone)
    now = datetime.now(UTC)

    # 1. Check if device/phone is locked
    is_locked, remaining_secs = get_lock_status(clean_phone, client_ip)
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account is locked due to repeated failed attempts. Please try again after {remaining_secs} seconds.",
            headers={"Retry-After": str(remaining_secs)},
        )

    record = _OTP_CACHE.get(clean_phone)
    lock_key = f"{clean_phone}:{client_ip}"

    if not record:
        _record_failed_attempt(clean_phone, client_ip)
        return False, "Invalid or expired OTP. Please check and try again.", {
            "locked": False,
            "attempts_left": 0,
            "retry_after_seconds": 0,
        }

    # Check expiration (5 minutes)
    if now > record["expires_at"]:
        del _OTP_CACHE[clean_phone]
        _record_failed_attempt(clean_phone, client_ip)
        return False, "OTP has expired. Please request a new verification code.", {
            "locked": False,
            "attempts_left": 0,
            "retry_after_seconds": 0,
        }

    attempts = record.get("attempts", 0) + 1
    record["attempts"] = attempts
    attempts_left = max(0, MAX_FAILED_ATTEMPTS - attempts)

    submitted_hash = compute_otp_hash(clean_phone, (submitted_otp or "").strip())
    expected_hash = record.get("otp_hash", "")

    if hmac.compare_digest(expected_hash, submitted_hash):
        # Success: Clear OTP immediately (single use!) and reset failed lockout
        del _OTP_CACHE[clean_phone]
        if lock_key in _LOCKOUT_CACHE:
            del _LOCKOUT_CACHE[lock_key]
        if clean_phone in _LOCKOUT_CACHE:
            del _LOCKOUT_CACHE[clean_phone]
        return True, "Verification successful", {
            "locked": False,
            "attempts_left": MAX_FAILED_ATTEMPTS,
            "retry_after_seconds": 0,
        }

    # Wrong OTP submitted
    if lock_key not in _LOCKOUT_CACHE:
        _LOCKOUT_CACHE[lock_key] = {"failed_count": 0, "locked_until": None}
    _LOCKOUT_CACHE[lock_key]["failed_count"] += 1

    if (
        attempts >= MAX_FAILED_ATTEMPTS
        or _LOCKOUT_CACHE[lock_key]["failed_count"] >= MAX_FAILED_ATTEMPTS
    ):
        locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
        _LOCKOUT_CACHE[lock_key] = {
            "failed_count": MAX_FAILED_ATTEMPTS,
            "locked_until": locked_until,
        }
        if not client_ip:
            _LOCKOUT_CACHE[clean_phone] = {
                "failed_count": MAX_FAILED_ATTEMPTS,
                "locked_until": locked_until,
            }
        if clean_phone in _OTP_CACHE:
            del _OTP_CACHE[clean_phone]
        return False, f"Invalid OTP. 0 attempt(s) remaining. Account is now locked for {LOCKOUT_MINUTES} minutes.", {
            "locked": False,
            "just_locked": True,
            "retry_after_seconds": LOCKOUT_MINUTES * 60,
            "attempts_left": 0,
        }

    return False, f"Invalid OTP. {attempts_left} attempt(s) remaining.", {
        "locked": False,
        "attempts_left": attempts_left,
        "retry_after_seconds": 0,
    }


def _record_failed_attempt(clean_phone: str, client_ip: str | None = None) -> None:
    now = datetime.now(UTC)
    lock_key = f"{clean_phone}:{client_ip}" if client_ip else clean_phone
    if lock_key not in _LOCKOUT_CACHE:
        _LOCKOUT_CACHE[lock_key] = {"failed_count": 0, "locked_until": None}
    _LOCKOUT_CACHE[lock_key]["failed_count"] += 1
    if _LOCKOUT_CACHE[lock_key]["failed_count"] >= MAX_FAILED_ATTEMPTS:
        _LOCKOUT_CACHE[lock_key] = {
            "failed_count": MAX_FAILED_ATTEMPTS,
            "locked_until": now + timedelta(minutes=LOCKOUT_MINUTES),
        }


def clear_all_otp_locks(
    phone: str | None = None, client_ip: str | None = None
) -> dict[str, Any]:
    """
    Development & test utility: clears OTP locks, counters, and rate limits.
    Can unlock a single phone or all devices.
    """
    from backend.app.core.rate_limit import in_memory_limiter

    cleared_locks = 0
    cleared_otps = 0

    if phone:
        clean_phone = phone.strip().replace(" ", "").replace("+", "")
        keys_to_del = [k for k in list(_LOCKOUT_CACHE.keys()) if clean_phone in k]
        for k in keys_to_del:
            del _LOCKOUT_CACHE[k]
            cleared_locks += 1
        if clean_phone in _OTP_CACHE:
            del _OTP_CACHE[clean_phone]
            cleared_otps += 1
        if clean_phone in _SEND_TRACKER:
            del _SEND_TRACKER[clean_phone]
    else:
        cleared_locks = len(_LOCKOUT_CACHE)
        cleared_otps = len(_OTP_CACHE)
        _LOCKOUT_CACHE.clear()
        _OTP_CACHE.clear()
        _SEND_TRACKER.clear()

    if client_ip:
        ip_key = f"ip:{client_ip}"
        if ip_key in _SEND_TRACKER:
            del _SEND_TRACKER[ip_key]

    in_memory_limiter.reset()

    return {
        "cleared_locks": cleared_locks,
        "cleared_otps": cleared_otps,
        "target": phone or "all",
    }



def create_access_token(
    user_id: int,
    phone: str,
    role: str,
    session_version: int = 1,
    is_admin_2fa: bool = False,
    expires_delta: timedelta | None = None,
) -> str:
    """Creates signed JWT token with claims: user_id, phone, role, session_version, 2FA flag."""
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": str(user_id),
        "phone": phone,
        "role": role,
        "sv": session_version,
        "is_2fa": is_admin_2fa,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


async def get_current_user(
    token_auth: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)],
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """FastAPI dependency: extracts and verifies JWT user and checks session validity."""
    if not token_auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            token_auth.credentials, settings.SECRET_KEY, algorithms=["HS256"]
        )
        user_id = int(payload.get("sub", 0))
        token_sv = int(payload.get("sv", 1))
        token_is_2fa = bool(payload.get("is_2fa", False))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User account not found")
    if getattr(user, "is_deleted", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account has been deactivated or deleted",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # R6 Requirement 2: Log out of all devices verification
    # If user's session_version was incremented, previous tokens are rejected
    if getattr(user, "session_version", 1) != token_sv:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked on this device. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Attach token 2FA state to runtime user object
    setattr(user, "token_is_2fa", token_is_2fa)
    return user


async def get_optional_current_user(
    token_auth: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)],
    db: AsyncSession = Depends(get_async_db),
) -> User | None:
    """Optional JWT authentication dependency."""
    if not token_auth:
        return None
    try:
        payload = jwt.decode(
            token_auth.credentials, settings.SECRET_KEY, algorithms=["HS256"]
        )
        user_id = int(payload.get("sub", 0))
        token_sv = int(payload.get("sv", 1))
        token_is_2fa = bool(payload.get("is_2fa", False))
    except Exception:
        return None

    user = await db.scalar(select(User).where(User.id == user_id))
    if user and getattr(user, "is_deleted", False):
        return None
    if user and getattr(user, "session_version", 1) != token_sv:
        return None

    if user:
        setattr(user, "token_is_2fa", token_is_2fa)
    return user


def require_roles(allowed_roles: list[str]):
    """Role-based authorization dependency guard. Returns 403 Forbidden for disallowed roles."""

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Operation requires one of roles: {allowed_roles}. Current role: {current_user.role}",
            )
        return current_user

    return role_checker


def require_admin_role_enforced(require_2fa: bool = True):
    """
    Administrative authorization guard.
    Requirement 3 & 5: Protected on server, not only menu; 403 for other roles; 2FA required for admin.
    """

    async def admin_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Administrative access required.",
            )

        # Requirement 5: 2FA required for admin
        if require_2fa:
            is_2fa_ok = getattr(current_user, "is_admin_2fa_verified", False) or getattr(
                current_user, "token_is_2fa", False
            )
            # In development/test with debug, allow if explicitly set
            if not is_2fa_ok:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Two-factor authentication (2FA) required for admin operations.",
                )

        return current_user

    return admin_checker
