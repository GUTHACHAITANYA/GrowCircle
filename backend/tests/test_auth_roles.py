"""
Integration tests for R6 Authentication, Role Guards, Session Expiry, DPDP Profile, and Audit Logs.
"""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.rate_limit import in_memory_limiter
from backend.app.models.audit_log import AuditLog
from backend.app.models.buyer import BuyerProfile
from backend.app.models.transporter import Transporter
from backend.app.models.user import User
from backend.app.services.security import (
    _LOCKOUT_CACHE,
    _OTP_CACHE,
    create_access_token,
    encrypt_document_data,
)


@pytest.fixture(autouse=True)
def reset_in_memory_auth_state():
    """Clear in-memory OTP stores and rate limiters before each test."""
    _OTP_CACHE.clear()
    _LOCKOUT_CACHE.clear()
    in_memory_limiter.reset()
    yield
    _OTP_CACHE.clear()
    _LOCKOUT_CACHE.clear()
    in_memory_limiter.reset()


@pytest.mark.asyncio
async def test_send_and_verify_otp_lifecycle(client: AsyncClient, db_session: AsyncSession) -> None:
    """R6: Phone + OTP login, auto-registration, token generation, and secure cookie."""
    phone = "9876543210"

    # 1. Send OTP
    send_res = await client.post("/auth/send-otp", json={"phone": phone})
    assert send_res.status_code == 200
    data = send_res.json()
    assert data["status"] == "otp_sent"
    assert "sandbox_otp" in data
    otp = data["sandbox_otp"]
    assert len(otp) == 6

    # 2. Verify OTP
    verify_res = await client.post(
        "/auth/verify-otp",
        json={"phone": phone, "otp": otp, "role": "farmer", "name": "Ramu Farmer"},
    )
    assert verify_res.status_code == 200
    auth_data = verify_res.json()
    assert auth_data["access_token"]
    assert auth_data["role"] == "farmer"
    assert auth_data["name"] == "Ramu Farmer"
    assert auth_data["phone"] == phone

    # Verify cookie was set
    assert "growcircle_token" in verify_res.cookies


@pytest.mark.asyncio
async def test_otp_failure_and_account_lockout(client: AsyncClient) -> None:
    """R6: Account lockout after 5 consecutive failed OTP attempts."""
    phone = "9988776655"

    # Send valid OTP
    await client.post("/auth/send-otp", json={"phone": phone})

    # Attempt 5 consecutive invalid OTPs
    for i in range(5):
        fail_res = await client.post(
            "/auth/verify-otp",
            json={"phone": phone, "otp": "000000", "role": "farmer"},
        )
        assert fail_res.status_code == 400

    # 6th attempt should be blocked with 429 Account Locked
    locked_res = await client.post(
        "/auth/verify-otp",
        json={"phone": phone, "otp": "000000", "role": "farmer"},
    )
    assert locked_res.status_code == 429
    assert "locked" in locked_res.json()["detail"].lower()

    # Sending new OTP to locked phone should also return 429
    send_locked = await client.post("/auth/send-otp", json={"phone": phone})
    assert send_locked.status_code == 429


@pytest.mark.asyncio
async def test_role_based_access_control_and_admin_protection(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """
    R6 Requirement 3:
    - Visitor can view prices without login.
    - Protected endpoints return 401 without login.
    - Admin endpoints return 403 for non-admin roles (farmer, buyer, driver).
    - Admin endpoints return 200 for admin.
    """
    # 1. Unauthenticated visitor views prices -> 200 OK
    public_res = await client.get("/prices")
    assert public_res.status_code == 200

    # 2. Unauthenticated visitor accesses protected endpoint -> 401 Unauthorized
    unauth_res = await client.get("/auth/me")
    assert unauth_res.status_code == 401

    unauth_admin_res = await client.get("/admin/buyers/pending")
    assert unauth_admin_res.status_code == 401

    # 3. Create users for each role
    farmer = User(phone="9111111111", role="farmer", name="Farmer Raj", language="te")
    buyer_user = User(phone="9222222222", role="buyer", name="Buyer Suresh", language="en")
    driver_user = User(phone="9333333333", role="driver", name="Driver Mahesh", language="te")
    admin_user = User(phone="9444444444", role="admin", name="Admin Sita", language="en")
    db_session.add_all([farmer, buyer_user, driver_user, admin_user])
    await db_session.commit()

    farmer_token = create_access_token(farmer.id, farmer.phone, "farmer")
    buyer_token = create_access_token(buyer_user.id, buyer_user.phone, "buyer")
    driver_token = create_access_token(driver_user.id, driver_user.phone, "driver")
    admin_token = create_access_token(admin_user.id, admin_user.phone, "admin")

    # 4. Farmer tries to access admin endpoints -> 403 Forbidden
    res_f1 = await client.get(
        "/admin/buyers/pending", headers={"Authorization": f"Bearer {farmer_token}"}
    )
    assert res_f1.status_code == 403

    res_f2 = await client.get(
        "/transport/admin/transporters/pending", headers={"Authorization": f"Bearer {farmer_token}"}
    )
    assert res_f2.status_code == 403

    res_f3 = await client.get(
        "/auth/audit-logs", headers={"Authorization": f"Bearer {farmer_token}"}
    )
    assert res_f3.status_code == 403

    # 5. Buyer tries to access admin endpoints -> 403 Forbidden
    res_b1 = await client.get(
        "/admin/buyers/pending", headers={"Authorization": f"Bearer {buyer_token}"}
    )
    assert res_b1.status_code == 403

    # 6. Driver tries to access admin endpoints -> 403 Forbidden
    res_d1 = await client.get(
        "/transport/admin/transporters/pending", headers={"Authorization": f"Bearer {driver_token}"}
    )
    assert res_d1.status_code == 403

    # 7. Admin accesses admin endpoints -> 200 OK
    res_a1 = await client.get(
        "/admin/buyers/pending", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_a1.status_code == 200

    res_a2 = await client.get(
        "/transport/admin/transporters/pending", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_a2.status_code == 200

    res_a3 = await client.get(
        "/auth/audit-logs", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_a3.status_code == 200


@pytest.mark.asyncio
async def test_admin_2fa_verification(client: AsyncClient, db_session: AsyncSession) -> None:
    """R6: Admin 2FA verification unlocks administrative access."""
    admin = User(phone="9555555555", role="admin", is_admin_2fa_verified=False)
    farmer = User(phone="9666666666", role="farmer")
    db_session.add_all([admin, farmer])
    await db_session.commit()

    farmer_token = create_access_token(farmer.id, farmer.phone, "farmer")
    admin_token = create_access_token(admin.id, admin.phone, "admin")

    # Farmer cannot access 2FA endpoint -> 403
    res_f = await client.post(
        "/auth/admin-2fa",
        json={"code": "654321"},
        headers={"Authorization": f"Bearer {farmer_token}"},
    )
    assert res_f.status_code == 403

    # Admin with wrong code -> 400
    res_wrong = await client.post(
        "/auth/admin-2fa",
        json={"code": "111111"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_wrong.status_code == 400

    # Admin with correct code -> 200 & verified
    res_correct = await client.post(
        "/auth/admin-2fa",
        json={"code": "654321"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_correct.status_code == 200
    data = res_correct.json()
    assert data["status"] == "success"
    assert data["is_admin_2fa_verified"] is True
    assert "access_token" in data


@pytest.mark.asyncio
async def test_logout_and_log_out_of_all_devices(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """R6: Single session logout and 'Log out of all devices' session revocation."""
    user = User(phone="9777777777", role="farmer", session_version=1)
    db_session.add(user)
    await db_session.commit()

    token1 = create_access_token(user.id, user.phone, user.role, session_version=1)
    headers = {"Authorization": f"Bearer {token1}"}

    # 1. Normal logout clears cookies
    logout_res = await client.post("/auth/logout", headers=headers)
    assert logout_res.status_code == 200
    assert logout_res.json()["status"] == "logged_out"

    # 2. Verify token1 still works with DB session version 1
    me_res = await client.get("/auth/me", headers=headers)
    assert me_res.status_code == 200

    # 3. 'Log out of all devices' increments session_version
    logout_all_res = await client.post("/auth/logout-all", headers=headers)
    assert logout_all_res.status_code == 200
    assert logout_all_res.json()["status"] == "all_devices_revoked"

    # 4. token1 should now be rejected with 401 Session Revoked
    revoked_res = await client.get("/auth/me", headers=headers)
    assert revoked_res.status_code == 401
    assert "revoked" in revoked_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_profile_update_and_dpdp_export_and_deletion(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """R6: Profile details, DPDP export, and account deletion with audit logging."""
    user = User(
        phone="9888888888",
        role="farmer",
        name="Anil Kumar",
        language="te",
        district="Guntur",
    )
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.id, user.phone, user.role)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Get profile
    profile_res = await client.get("/auth/me", headers=headers)
    assert profile_res.status_code == 200
    assert profile_res.json()["name"] == "Anil Kumar"

    # 2. Update profile
    patch_res = await client.patch(
        "/auth/profile",
        json={"name": "Anil K. Varma", "language": "hi", "district": "Krishna", "consent_location": True},
        headers=headers,
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["name"] == "Anil K. Varma"
    assert updated["language"] == "hi"
    assert updated["district"] == "Krishna"
    assert updated["consent_at"] is not None

    # 3. Export portable data package
    export_res = await client.get("/auth/export-my-data", headers=headers)
    assert export_res.status_code == 200
    export_data = export_res.json()
    assert "user_profile" in export_data
    assert export_data["user_profile"]["phone"] == "9888888888"

    # 4. Delete account
    del_res = await client.delete("/auth/delete-my-account", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"

    # 5. Accessing with old token should now fail
    after_del = await client.get("/auth/me", headers=headers)
    assert after_del.status_code == 401


@pytest.mark.asyncio
async def test_audit_logs_for_sensitive_actions(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """R6 Requirement 6: Audit log for sensitive actions (document view, approval, rejection, data export)."""
    admin = User(phone="9999900000", role="admin")
    buyer_user = User(phone="9999911111", role="buyer")
    db_session.add_all([admin, buyer_user])
    await db_session.commit()

    # Create pending buyer with encrypted documents
    buyer_profile = BuyerProfile(
        user_id=buyer_user.id,
        business_name="Green Agro Ltd",
        business_type="institution",
        address="Main Bazaar, Guntur",
        district="Guntur",
        state="Andhra Pradesh",
        latitude=16.3067,
        longitude=80.4365,
        encrypted_gst_number=encrypt_document_data("37AAAAA0000A1Z5"),
        encrypted_document_ref=encrypt_document_data("https://storage/kyc.pdf"),
        verification_status="pending",
    )
    db_session.add(buyer_profile)
    await db_session.commit()

    admin_token = create_access_token(admin.id, admin.phone, "admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Admin views document queue -> Logs DOCUMENT_VIEW
    view_res = await client.get("/admin/buyers/pending", headers=admin_headers)
    assert view_res.status_code == 200

    # 2. Admin approves buyer -> Logs APPROVAL
    approve_res = await client.post(
        f"/admin/buyers/{buyer_profile.id}/verify",
        json={"decision": "verified", "notes": "Documents verified"},
        headers=admin_headers,
    )
    assert approve_res.status_code == 200

    # 3. Check audit logs via admin endpoint
    audit_res = await client.get("/auth/audit-logs", headers=admin_headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    actions = [l["action"] for l in logs]
    assert "DOCUMENT_VIEW" in actions
    assert "APPROVAL" in actions
