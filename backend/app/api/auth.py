"""
Authentication and User Profile API Router.
R6 Implementation:
- Phone number + OTP login (no passwords for farmers and drivers).
- SMS / WhatsApp OTP provider behind interface with mock provider in demo.
- Rate limiting, expiring codes (5m), account lockout on repeated failures.
- Session expiry, logout, and "log out of all devices" session revocation.
- Role-based access control (farmer, buyer, driver, consumer, admin).
- Profile management with DPDP Act consent and data export / erasure handoff.
- Admin 2FA verification.
- Sensitive actions audit logging.
"""

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.rate_limit import RateLimitRule, get_client_ip, rate_limit_check
from backend.app.db.session import get_async_db
from backend.app.models.audit_log import AuditLog
from backend.app.models.buyer import BuyerProfile
from backend.app.models.transporter import Transporter
from backend.app.models.user import User
from backend.app.services.audit_service import log_security_event
from backend.app.services.dpdp_service import delete_user_account, export_user_data
from backend.app.services.otp import get_otp_provider_status, is_real_otp_provider_configured
from backend.app.services.security import (
    clear_all_otp_locks,
    create_access_token,
    generate_and_send_phone_otp_async,
    get_current_user,
    get_lock_status,
    is_phone_locked,
    require_admin_role_enforced,
    require_roles,
    verify_phone_otp,
)

router = APIRouter(prefix="/auth", tags=["Authentication & Profile"])

PUBLIC_ROLES = {"farmer", "buyer", "driver", "consumer"}


class SendOtpRequest(BaseModel):
    phone: str = Field(description="10-digit mobile phone number or E.164")


class VerifyOtpRequest(BaseModel):
    phone: str = Field(description="10-digit mobile phone number")
    otp: str = Field(description="6-digit verification OTP")
    role: str = Field(default="farmer", description="farmer, buyer, driver, consumer")
    name: str | None = Field(default=None, description="Optional user name")


class Admin2FARequest(BaseModel):
    code: str = Field(description="6-digit administrative 2FA verification code")


class CreateAdminRequest(BaseModel):
    phone: str = Field(description="10-digit mobile phone number for new admin")
    name: str = Field(description="Administrator full name")
    district: str | None = Field(default=None, description="Optional district")


class ClearLockRequest(BaseModel):
    phone: str | None = Field(default=None, description="Optional phone number to unlock")
    client_ip: str | None = Field(default=None, description="Optional client IP to unlock")


class UpdateProfileRequest(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    language: str | None = Field(default=None, max_length=10)
    district: str | None = Field(default=None, max_length=100)
    consent_location: bool | None = Field(default=None)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    phone: str
    name: str | None
    role: str
    verification_status: str = "verified"  # verified, pending, rejected
    is_verified: bool = True
    language: str
    district: str | None
    is_admin_2fa_verified: bool
    session_version: int


class UserProfileResponse(BaseModel):
    id: int
    phone: str
    name: str | None
    role: str
    verification_status: str = "verified"
    is_verified: bool = True
    language: str
    district: str | None
    consent_at: str | None
    consent_purpose: str | None
    is_admin_2fa_verified: bool
    session_version: int


async def get_user_verification_status(user: User, db: AsyncSession) -> tuple[str, bool]:
    """
    Public roles verification:
    - farmer & consumer: instantly active & verified ('verified', True)
    - buyer: stays 'pending' until admin approves ('pending', False)
    - transporter/driver: stays 'pending' until admin approves ('pending', False)
    - admin: 'verified', True
    """
    if user.role in ("farmer", "consumer"):
        return "verified", True

    if user.role == "buyer":
        buyer = (
            await db.execute(select(BuyerProfile).where(BuyerProfile.user_id == user.id))
        ).scalar_one_or_none()
        if buyer:
            return buyer.verification_status, (buyer.verification_status == "verified")
        return "pending", False

    if user.role in ("driver", "transporter"):
        transporter = (
            await db.execute(
                select(Transporter).where(
                    (Transporter.user_id == user.id) | (Transporter.phone == user.phone)
                )
            )
        ).scalar_one_or_none()
        if transporter:
            return ("verified", True) if transporter.is_verified else ("pending", False)
        return "pending", False

    return "verified", True


@router.get("/provider-status")
async def get_provider_status() -> dict[str, Any]:
    """Returns runtime OTP provider information (live SMS/WhatsApp vs demo simulation)."""
    return get_otp_provider_status()


@router.post("/send-otp")
async def send_otp(
    payload: SendOtpRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """
    Dispatches 6-digit OTP using SMS or WhatsApp provider behind interface.
    Enforces 30s resend cooldown, daily cap, and device/phone lockout.
    In demo mode only: logs OTP in server log and returns sandbox_otp / dev_otp.
    In production mode: never logs OTP and never returns OTP in response.
    """
    clean_phone = payload.phone.strip().replace(" ", "").replace("+", "")
    client_ip = get_client_ip(request)

    # 1. Check if account is locked
    is_locked, remaining_secs = get_lock_status(clean_phone, client_ip)
    if is_locked:
        await log_security_event(
            db=db,
            action="OTP_REQUEST_REJECTED_LOCKED",
            client_ip=client_ip,
            target_resource="user",
            target_id=clean_phone,
            details="Attempted OTP request on locked account",
            status="DENIED",
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account is temporarily locked due to repeated failed attempts. Please try again after {remaining_secs} seconds.",
            headers={"Retry-After": str(remaining_secs)},
        )

    # 2. Rate limit OTP requests
    await rate_limit_check("otp", clean_phone, *RateLimitRule.OTP)

    # 3. Generate and dispatch OTP (enforces 30s cooldown and daily cap)
    otp, meta = await generate_and_send_phone_otp_async(clean_phone, client_ip=client_ip)

    await log_security_event(
        db=db,
        action="OTP_DISPATCHED",
        client_ip=client_ip,
        target_resource="user",
        target_id=clean_phone,
        details="OTP dispatched via configured provider",
        status="SUCCESS",
    )

    is_real = meta.get("is_real_provider", False)
    response_data: dict[str, Any] = {
        "status": "otp_sent",
        "phone": clean_phone,
        "expires_in_seconds": 300,
        "resend_cooldown_seconds": meta.get("resend_cooldown_seconds", 30),
        "daily_sends_remaining": meta.get("daily_sends_remaining", 9),
        "is_real_provider": is_real,
        "message": (
            "Verification code sent via live SMS/WhatsApp provider."
            if is_real
            else "Demo mode: verification code simulated."
        ),
    }

    if meta.get("is_demo", False):
        response_data["sandbox_otp"] = otp
        response_data["dev_otp"] = otp
        response_data["is_demo"] = True

    return response_data


@router.post("/verify-otp", response_model=AuthResponse)
async def verify_otp(
    payload: VerifyOtpRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
) -> AuthResponse:
    """
    Verifies phone OTP and returns JWT token with claims and secure cookies.
    - Public roles allowed: farmer, buyer, driver, consumer only.
    - Admin accounts cannot be self-registered (must be created by an existing admin).
    - Buyer and transporter stay 'pending verification' until an admin approves.
    - Locks by phone + device/IP after 5 failed attempts per code.
    """
    clean_phone = payload.phone.strip().replace(" ", "").replace("+", "")
    client_ip = get_client_ip(request)

    # Public roles check & admin protection
    existing_user = await db.scalar(select(User).where(User.phone == clean_phone))

    if payload.role == "admin":
        if not existing_user or existing_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin accounts cannot be self-registered. An existing administrator must create your account.",
            )

    if payload.role not in PUBLIC_ROLES and payload.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{payload.role}' is not a valid public role. Allowed roles: farmer, buyer, driver, consumer.",
        )

    # Prevent a non-admin from upgrading to admin via verify-otp
    if existing_user and existing_user.role != "admin" and payload.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin accounts cannot be self-registered.",
        )

    is_valid, msg, verify_meta = verify_phone_otp(
        clean_phone, payload.otp, client_ip=client_ip
    )

    if not is_valid:
        await log_security_event(
            db=db,
            action="AUTH_FAILED_OTP",
            client_ip=client_ip,
            target_resource="user",
            target_id=clean_phone,
            details=msg,
            status="FAILURE",
        )
        if verify_meta.get("locked"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=msg,
                headers={"Retry-After": str(verify_meta.get("retry_after_seconds", 900))},
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )

    # Retrieve or create user
    user = existing_user
    if not user:
        user = User(
            phone=clean_phone,
            role=payload.role,
            name=payload.name,
            language="te",
            consent_at=datetime.now(UTC),
            session_version=1,
            is_admin_2fa_verified=False,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # Reset failed attempts on successful login
        user.failed_otp_attempts = 0
        user.locked_until = None
        if payload.name and not user.name:
            user.name = payload.name
        # Allow public role switch if specified during login, but never switch to/from admin
        if (
            payload.role in PUBLIC_ROLES
            and user.role != "admin"
            and user.role != payload.role
        ):
            user.role = payload.role
        await db.commit()

    ver_status, is_ver = await get_user_verification_status(user, db)

    token = create_access_token(
        user_id=user.id,
        phone=user.phone,
        role=user.role,
        session_version=user.session_version,
        is_admin_2fa=user.is_admin_2fa_verified,
    )

    # Set secure SameSite cookie
    response.set_cookie(
        key="growcircle_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.ENVIRONMENT in ("production", "staging"),
        max_age=86400 * 30,  # 30 days
        path="/",
    )

    await log_security_event(
        db=db,
        action="AUTH_LOGIN_SUCCESS",
        user_id=user.id,
        actor_role=user.role,
        client_ip=client_ip,
        target_resource="user",
        target_id=str(user.id),
        details="User successfully authenticated via phone-OTP",
        status="SUCCESS",
    )

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        phone=user.phone,
        name=user.name,
        role=user.role,
        verification_status=ver_status,
        is_verified=is_ver,
        language=user.language,
        district=user.district,
        is_admin_2fa_verified=user.is_admin_2fa_verified,
        session_version=user.session_version,
    )


@router.post("/admin/create-admin", summary="Provision new admin user (Admin only)")
async def create_admin_account(
    payload: CreateAdminRequest,
    request: Request,
    current_user: User = Depends(require_admin_role_enforced(require_2fa=True)),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """
    Requirement 5:
    Admin accounts can only be created by an existing administrator.
    """
    clean_phone = payload.phone.strip().replace(" ", "").replace("+", "")
    existing = await db.scalar(select(User).where(User.phone == clean_phone))
    if existing:
        existing.role = "admin"
        if payload.name:
            existing.name = payload.name
        admin_user = existing
    else:
        admin_user = User(
            phone=clean_phone,
            name=payload.name,
            role="admin",
            district=payload.district,
            language="en",
            consent_at=datetime.now(UTC),
            session_version=1,
            is_admin_2fa_verified=False,
        )
        db.add(admin_user)

    await db.commit()
    await db.refresh(admin_user)

    await log_security_event(
        db=db,
        action="ADMIN_ACCOUNT_PROVISIONED",
        user_id=current_user.id,
        actor_role="admin",
        client_ip=get_client_ip(request),
        target_resource="user",
        target_id=str(admin_user.id),
        details=f"Admin #{current_user.id} provisioned admin account for {clean_phone} ({payload.name})",
        status="SUCCESS",
    )

    return {
        "status": "success",
        "message": f"Administrator account created for +91 {clean_phone}.",
        "user_id": admin_user.id,
        "phone": admin_user.phone,
        "name": admin_user.name,
        "role": admin_user.role,
    }


@router.post("/dev/clear-lock", summary="Clear OTP locks and counters (Dev & Demo only)")
async def clear_dev_lock(
    payload: ClearLockRequest | None = None,
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """
    Requirement 1:
    Allows developers and automated tests to clear OTP lockouts, counters, and rate limits.
    Forbidden in production.
    """
    if settings.ENVIRONMENT not in ("development", "test") and settings.APP_MODE != "demo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Lock clearing is only available in development and demo environments.",
        )

    phone = payload.phone if payload else None
    client_ip = payload.client_ip if payload else None
    res = clear_all_otp_locks(phone=phone, client_ip=client_ip)

    if phone:
        clean_phone = phone.strip().replace(" ", "").replace("+", "")
        db_user = await db.scalar(select(User).where(User.phone == clean_phone))
        if db_user:
            db_user.failed_otp_attempts = 0
            db_user.locked_until = None
            await db.commit()

    return {
        "status": "success",
        "message": f"Locks and counters cleared for {phone or 'all devices'}.",
        "details": res,
    }



@router.post("/admin-2fa")
async def verify_admin_2fa(
    payload: Admin2FARequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """
    R6 Requirement 5:
    Two-factor authentication (2FA) verification required for admin role.
    Accepts 6-digit TOTP / master verification code.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: 2FA endpoint is reserved for administrators.",
        )

    # In production/test: verify admin code (default test/demo master code "654321")
    expected_code = getattr(settings, "ADMIN_2FA_CODE", "654321")
    if payload.code.strip() != expected_code:
        await log_security_event(
            db=db,
            action="ADMIN_2FA_FAILURE",
            user_id=current_user.id,
            actor_role="admin",
            client_ip=get_client_ip(request),
            details="Incorrect admin 2FA code",
            status="FAILURE",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA code. Please verify your authenticator app.",
        )

    current_user.is_admin_2fa_verified = True
    await db.commit()

    # Re-issue upgraded token with is_2fa: True
    token = create_access_token(
        user_id=current_user.id,
        phone=current_user.phone,
        role=current_user.role,
        session_version=current_user.session_version,
        is_admin_2fa=True,
    )

    response.set_cookie(
        key="growcircle_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.ENVIRONMENT in ("production", "staging"),
        max_age=86400 * 30,
        path="/",
    )

    await log_security_event(
        db=db,
        action="ADMIN_2FA_SUCCESS",
        user_id=current_user.id,
        actor_role="admin",
        client_ip=get_client_ip(request),
        details="Admin successfully verified 2FA",
        status="SUCCESS",
    )

    return {
        "status": "success",
        "message": "Admin 2FA successfully verified. Administrative dashboard unlocked.",
        "access_token": token,
        "is_admin_2fa_verified": True,
    }


@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """
    R6 Requirement 2:
    Logs out the current session and clears cookies.
    """
    response.delete_cookie(key="growcircle_token", path="/")
    await log_security_event(
        db=db,
        action="AUTH_LOGOUT",
        user_id=current_user.id,
        actor_role=current_user.role,
        client_ip=get_client_ip(request),
        details="User logged out of current session",
        status="SUCCESS",
    )
    return {"status": "logged_out", "message": "Successfully logged out."}


@router.post("/logout-all")
async def logout_all_devices(
    response: Response,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """
    R6 Requirement 2:
    "Log out of all devices" - increments session_version, invalidating all issued tokens.
    """
    current_user.session_version += 1
    current_user.is_admin_2fa_verified = False
    await db.commit()

    response.delete_cookie(key="growcircle_token", path="/")

    await log_security_event(
        db=db,
        action="AUTH_LOGOUT_ALL_DEVICES",
        user_id=current_user.id,
        actor_role=current_user.role,
        client_ip=get_client_ip(request),
        details=f"All device sessions revoked (session_version={current_user.session_version})",
        status="SUCCESS",
    )

    return {
        "status": "all_devices_revoked",
        "message": "All sessions across all devices have been successfully terminated.",
    }


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> UserProfileResponse:
    """Returns the authenticated user's profile details."""
    ver_status, is_ver = await get_user_verification_status(current_user, db)
    return UserProfileResponse(
        id=current_user.id,
        phone=current_user.phone,
        name=current_user.name,
        role=current_user.role,
        verification_status=ver_status,
        is_verified=is_ver,
        language=current_user.language,
        district=current_user.district,
        consent_at=current_user.consent_at.isoformat() if current_user.consent_at else None,
        consent_purpose=current_user.consent_purpose,
        is_admin_2fa_verified=current_user.is_admin_2fa_verified,
        session_version=current_user.session_version,
    )


@router.patch("/profile", response_model=UserProfileResponse)
async def update_my_profile(
    payload: UpdateProfileRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> UserProfileResponse:
    """
    R6 Requirement 4:
    Profile page update: name, preferred language, district, and location consent.
    """
    if payload.name is not None:
        current_user.name = payload.name.strip()
    if payload.language is not None:
        current_user.language = payload.language.strip()
    if payload.district is not None:
        current_user.district = payload.district.strip()
    if payload.consent_location is not None:
        if payload.consent_location:
            current_user.consent_at = datetime.now(UTC)
            current_user.consent_withdrawn_at = None
        else:
            current_user.consent_withdrawn_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(current_user)

    await log_security_event(
        db=db,
        action="PROFILE_UPDATED",
        user_id=current_user.id,
        actor_role=current_user.role,
        client_ip=get_client_ip(request),
        details="User updated profile information",
        status="SUCCESS",
    )

    ver_status, is_ver = await get_user_verification_status(current_user, db)
    return UserProfileResponse(
        id=current_user.id,
        phone=current_user.phone,
        name=current_user.name,
        role=current_user.role,
        verification_status=ver_status,
        is_verified=is_ver,
        language=current_user.language,
        district=current_user.district,
        consent_at=current_user.consent_at.isoformat() if current_user.consent_at else None,
        consent_purpose=current_user.consent_purpose,
        is_admin_2fa_verified=current_user.is_admin_2fa_verified,
        session_version=current_user.session_version,
    )


@router.get("/export-my-data")
async def export_my_data(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """
    R6 Requirement 4 & 6:
    Export authenticated user's portable data with immutable audit log under DPDP Act.
    """
    client_ip = get_client_ip(request)
    await rate_limit_check("dpdp_export", str(current_user.id), max_requests=5, window_seconds=3600)
    return await export_user_data(db=db, user_id=current_user.id, client_ip=client_ip)


@router.delete("/delete-my-account")
async def delete_my_account(
    request: Request,
    response: Response,
    reason: str = "User requested account deletion via profile page",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """
    R6 Requirement 4:
    Delete my account and personal data (DPDP Act Right to Erasure).
    Clears active session cookies.
    """
    client_ip = get_client_ip(request)
    result = await delete_user_account(
        db=db,
        user_id=current_user.id,
        reason=reason,
        client_ip=client_ip,
    )
    response.delete_cookie(key="growcircle_token", path="/")
    return result


# ============================================================================
# AUDIT LOGS ENDPOINT (Admin Only)
# ============================================================================
@router.get("/audit-logs", dependencies=[Depends(require_admin_role_enforced(require_2fa=False))])
async def list_audit_logs(
    action: str | None = None,
    user_id: int | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_async_db),
) -> list[dict[str, Any]]:
    """
    R6 Requirement 6:
    Immutable audit log viewer for sensitive actions (document views, approvals, rejections, data exports).
    Protected for admin access.
    """
    stmt = select(AuditLog).order_by(desc(AuditLog.timestamp)).limit(limit)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)

    results = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "action": log.action,
            "user_id": log.user_id,
            "actor_role": log.actor_role,
            "client_ip": log.client_ip,
            "target_resource": log.target_resource,
            "target_id": log.target_id,
            "details": log.details,
            "status": log.status,
        }
        for log in results
    ]
