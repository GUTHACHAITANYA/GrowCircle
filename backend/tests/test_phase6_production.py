"""
Test suite for Phase 6 production readiness:
- OWASP security headers
- Prometheus metrics endpoint
- Rate limiting enforcement (HTTP 429)
- DPDP Act consent, export, and right to erasure
- Grievance Redressal officer details
- Pilot kit feedback submissions
- Privacy-friendly analytics dashboard
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.rate_limit import in_memory_limiter
from backend.app.models.user import User


@pytest.fixture(autouse=True)
def reset_rate_limits() -> None:
    """Reset rate limiter buckets before each test."""
    in_memory_limiter.reset()


@pytest.mark.asyncio
async def test_owasp_security_headers(client: AsyncClient) -> None:
    """Verifies that all mandatory OWASP defense-in-depth headers are present."""
    res = await client.get("/health")
    assert res.status_code == 200

    headers = res.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("x-xss-protection") == "1; mode=block"
    assert "strict-transport-security" in headers
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "content-security-policy" in headers
    assert "server" not in headers  # Server signature stripped


@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint(client: AsyncClient) -> None:
    """Verifies standard Prometheus text metrics exposition."""
    # Trigger requests to record metrics
    await client.get("/prices?crop=banana&state=andhra-pradesh&district=guntur")

    res = await client.get("/metrics")
    assert res.status_code == 200
    assert "text/plain" in res.headers["content-type"]
    body = res.text

    assert "growcircle_requests_total" in body
    assert "growcircle_request_duration_seconds_avg" in body
    assert "growcircle_ivr_calls_total" in body
    assert "growcircle_whatsapp_messages_total" in body
    assert "growcircle_rate_limit_hits_total" in body


@pytest.mark.asyncio
async def test_rate_limiting_enforcement(client: AsyncClient) -> None:
    """Verifies that exceeding rate limits triggers HTTP 429 with Retry-After header."""
    phone = "9876543210"

    # Rule for OTP is 3 requests per 10 minutes
    res1 = await client.post("/auth/send-otp", json={"phone": phone})
    assert res1.status_code == 200

    res2 = await client.post("/auth/send-otp", json={"phone": phone})
    assert res2.status_code == 200

    res3 = await client.post("/auth/send-otp", json={"phone": phone})
    assert res3.status_code == 200

    # 4th request must be rejected with 429
    res4 = await client.post("/auth/send-otp", json={"phone": phone})
    assert res4.status_code == 429
    assert "Retry-After" in res4.headers
    assert "Rate limit exceeded" in res4.json()["detail"]


@pytest.mark.asyncio
async def test_dpdp_grievance_officer_contact(client: AsyncClient) -> None:
    """Verifies statutory Grievance Redressal Officer contact details under DPDP Act 2023."""
    res = await client.get("/dpdp/grievance")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "active"
    officer = data["officer"]
    assert officer["name"] == "Radhika Varma"
    assert officer["email"] == "grievance@growcircle.in"
    assert officer["statutory_acknowledgment_hours"] == 72
    assert officer["statutory_resolution_days"] == 30


@pytest.mark.asyncio
async def test_dpdp_consent_and_export_lifecycle(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Tests DPDP explicit consent recording and data export."""
    # Create test user
    user = User(
        phone="9988776655",
        language="te",
        district="Guntur",
        role="farmer",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # 1. Grant explicit consent
    res_consent = await client.post(
        "/dpdp/consent",
        json={
            "user_id": user.id,
            "version": "1.0",
            "purpose": "mandi_prices_and_marketplace",
        },
    )
    assert res_consent.status_code == 200
    assert res_consent.json()["status"] == "consent_recorded"

    # 2. Export portable data
    res_export = await client.get(f"/dpdp/export?user_id={user.id}")
    assert res_export.status_code == 200
    export_data = res_export.json()
    assert "export_timestamp" in export_data
    assert export_data["user_profile"]["phone"] == "9988776655"
    assert export_data["user_profile"]["language"] == "te"
    assert "listings" in export_data
    assert "farm_diary" in export_data


@pytest.mark.asyncio
async def test_dpdp_right_to_erasure_deletion(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Tests DPDP Section 12 Right to Erasure / Account Deletion."""
    user = User(
        phone="9123456789",
        language="en",
        district="Guntur",
        role="consumer",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    res_del = await client.post(
        "/dpdp/delete-account",
        json={"user_id": user.id, "reason": "Moving to another state"},
    )
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "success"

    # Verify DB state: phone is anonymized and is_deleted is true
    await db_session.refresh(user)
    assert user.is_deleted is True
    assert "deleted_" in user.phone
    assert user.consent_withdrawn_at is not None


@pytest.mark.asyncio
async def test_pilot_kit_feedback_flow(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    """Verifies feedback submission via web, voice note, or IVR keypress."""
    # 1. Web feedback submission
    res_web = await client.post(
        "/feedback",
        json={
            "channel": "web",
            "phone": "9876543210",
            "rating": 5,
            "category": "price_accuracy",
            "message": "Guntur mandi prices were 100% accurate today. Saved 2 hours travel.",
        },
    )
    assert res_web.status_code == 201
    assert res_web.json()["status"] == "success"

    # 2. IVR voice feedback
    res_ivr = await client.post(
        "/feedback",
        json={
            "channel": "ivr",
            "rating": 4,
            "voice_audio_url": "https://storage.growcircle.in/feedback/audio_102.mp3",
        },
    )
    assert res_ivr.status_code == 201

    # 3. List feedbacks
    res_list = await client.get("/feedback", headers=admin_headers)
    assert res_list.status_code == 200
    feedbacks = res_list.json()
    assert len(feedbacks) >= 2


@pytest.mark.asyncio
async def test_privacy_friendly_analytics_dashboard(client: AsyncClient) -> None:
    """Verifies privacy-friendly analytics endpoint returns operational metrics."""
    res = await client.get("/analytics/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert "weekly_active_users_by_door" in data
    assert "deals_summary" in data
    assert "logistics_summary" in data
    assert "mandi_data_freshness" in data
    assert data["mandi_data_freshness"]["is_fresh"] is True
