"""
Tests for Languages API and Honest Coverage tracking (R5).
Verifies:
1. All 22 scheduled Indian languages plus English (23 total) are present.
2. Honest coverage table has fields: ui_ready, voice_stt_ready, voice_tts_ready, reviewed_by_native_speaker.
3. Language preference updates user profile for shared use across IVR, WhatsApp, and Web.
4. Coverage report lists fully reviewed languages vs partly translated drafts with fallbacks.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.models.user import User
from backend.app.services.security import create_access_token


@pytest.mark.asyncio
async def test_get_all_23_languages(client: AsyncClient):
    """GET /languages returns all 22 scheduled languages plus English with honest coverage fields."""
    resp = await client.get("/languages")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data) == 23
    codes = [item["code"] for item in data]

    # Scheduled 22 languages
    scheduled_22 = [
        "as", "bn", "brx", "doi", "gu", "hi", "kn", "ks", "kok", "mai",
        "ml", "mni", "mr", "ne", "or", "pa", "sa", "sat", "sd", "ta", "te", "ur"
    ]
    for sc in scheduled_22:
        assert sc in codes, f"Missing scheduled language: {sc}"
    assert "en" in codes, "Missing English"

    # Check honest coverage fields on all entries
    for lang in data:
        assert "ui_ready" in lang
        assert "voice_stt_ready" in lang
        assert "voice_tts_ready" in lang
        assert "reviewed_by_native_speaker" in lang
        assert "fallback_code" in lang
        assert "is_rtl" in lang

    # RTL languages
    rtl_langs = {l["code"] for l in data if l["is_rtl"]}
    assert "ur" in rtl_langs
    assert "ks" in rtl_langs
    assert "sd" in rtl_langs


@pytest.mark.asyncio
async def test_languages_coverage_report(client: AsyncClient):
    """GET /languages/coverage-report produces honest coverage report with fallback details."""
    resp = await client.get("/languages/coverage-report")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_languages"] == 23
    assert data["scheduled_languages_count"] == 22
    assert data["english_included"] is True
    assert len(data["fully_reviewed_languages"]) >= 4  # en, te, hi, gu
    assert "te" in data["fully_reviewed_languages"]
    assert "hi" in data["fully_reviewed_languages"]
    assert "gu" in data["fully_reviewed_languages"]
    assert "en" in data["fully_reviewed_languages"]

    # Machine translated / partly translated
    assert "mr" in data["partly_translated_languages"]
    assert "bn" in data["partly_translated_languages"]
    assert "ta" in data["partly_translated_languages"]


@pytest.mark.asyncio
async def test_update_user_language_preference(client: AsyncClient, db_session):
    """PATCH /languages/preference saves choice in user profile for web, IVR, and WhatsApp."""
    phone = "9848099887"
    user = User(phone=phone, language="te", district="guntur", role="farmer")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(user_id=user.id, phone=user.phone, role=user.role)

    # 1. Update to Marathi (mr)
    resp = await client.patch(
        "/languages/preference",
        json={"language": "mr"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["language"] == "mr"

    # Verify DB persisted
    updated_user = await db_session.scalar(select(User).where(User.id == user.id))
    assert updated_user.language == "mr"

    # 2. Update without token but with phone
    resp2 = await client.patch(
        "/languages/preference",
        json={"language": "bn", "phone": phone},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "success"
    assert data2["language"] == "bn"

    # 3. Invalid language returns 400
    bad_resp = await client.patch(
        "/languages/preference",
        json={"language": "invalid_xyz"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bad_resp.status_code == 400
