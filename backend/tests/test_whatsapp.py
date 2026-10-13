"""
Tests for WhatsApp Cloud API Door:
Webhook verification, Voice notes in (text+audio reply), Location sharing, and 7 AM daily broadcast.
"""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.user import User
from backend.app.services.whatsapp.handler import whatsapp_handler
from backend.app.services.whatsapp.mock_provider import MockWhatsAppProvider


@pytest.mark.asyncio
async def test_whatsapp_webhook_verification_handshake(client: AsyncClient) -> None:
    """Verifies Meta webhook verification GET handshake."""
    token = settings.WHATSAPP_VERIFY_TOKEN
    challenge = "random_meta_challenge_12345"

    # 1. Valid handshake
    res_valid = await client.get(
        "/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": token,
            "hub.challenge": challenge,
        },
    )
    assert res_valid.status_code == 200
    assert res_valid.text == challenge

    # 2. Invalid token rejected with 403
    res_invalid = await client.get(
        "/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_token",
            "hub.challenge": challenge,
        },
    )
    assert res_invalid.status_code == 403


@pytest.mark.asyncio
async def test_whatsapp_voice_note_triggers_text_and_audio_reply(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """An incoming voice note is transcribed and answered with both text and voice note."""
    mock_provider = MockWhatsAppProvider()
    whatsapp_handler.provider = mock_provider

    sender_phone = "919848011222"
    user = User(
        phone=sender_phone,
        language="te",
        district="guntur",
        role="farmer",
        consent_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": sender_phone,
                                    "id": "wamid.HBgLM...",
                                    "timestamp": "1728800000",
                                    "type": "audio",
                                    "audio": {"id": "audio_file_id_01"},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    response = await client.post("/whatsapp/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "EVENT_RECEIVED"

    # Check mock provider captured both text message and voice note
    assert len(mock_provider.sent_messages) == 2
    types_sent = [m["type"] for m in mock_provider.sent_messages]
    assert "text" in types_sent
    assert "audio" in types_sent

    # Verify text contains Telugu brand name and price info
    text_msg = next(m for m in mock_provider.sent_messages if m["type"] == "text")
    assert "గ్రో సర్కిల్" in text_msg["text"]
    assert "గుంటూరు" in text_msg["text"]


@pytest.mark.asyncio
async def test_whatsapp_location_sharing_replies_nearest_mandis(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """An incoming GPS location pin receives the 3 nearest mandis in user language."""
    mock_provider = MockWhatsAppProvider()
    whatsapp_handler.provider = mock_provider

    sender_phone = "919848022333"
    user = User(
        phone=sender_phone,
        language="te",
        district="guntur",
        role="farmer",
        consent_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": sender_phone,
                                    "type": "location",
                                    "location": {
                                        "latitude": 16.3067,
                                        "longitude": 80.4365,
                                    },
                                }
                            ]
                        }
                    }
                ]
            }
        ],
    }

    response = await client.post("/whatsapp/webhook", json=payload)
    assert response.status_code == 200

    assert len(mock_provider.sent_messages) == 1
    msg = mock_provider.sent_messages[0]
    assert msg["type"] == "text"
    assert "3 Nearest Mandis" in msg["text"]
    assert "గుంటూరు" in msg["text"]


@pytest.mark.asyncio
async def test_whatsapp_text_message_query(client: AsyncClient, db_session: AsyncSession) -> None:
    """An incoming text query receives price info."""
    _ = db_session
    mock_provider = MockWhatsAppProvider()
    whatsapp_handler.provider = mock_provider

    sender_phone = "919848033444"
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": sender_phone,
                                    "type": "text",
                                    "text": {"body": "banana price in guntur"},
                                }
                            ]
                        }
                    }
                ]
            }
        ],
    }

    response = await client.post("/whatsapp/webhook", json=payload)
    assert response.status_code == 200

    assert len(mock_provider.sent_messages) == 1
    assert "Banana" in mock_provider.sent_messages[0]["text"]


def test_whatsapp_7am_broadcast_celery_task() -> None:
    """Verifies that the scheduled 7 AM Celery job delivers template alerts."""
    from unittest.mock import MagicMock, patch

    from backend.app.jobs.tasks import broadcast_daily_whatsapp_prices
    from backend.app.models.mandi import Mandi
    from backend.app.models.price import Price
    from backend.app.models.user import User

    mock_provider = MockWhatsAppProvider()

    mock_db = MagicMock()
    mock_user = User(
        id=1,
        phone="919848099887",
        language="te",
        district="guntur",
        role="farmer",
        consent_at=datetime.now(UTC),
    )
    mock_db.scalars.return_value.all.return_value = [mock_user]

    mock_mandi = Mandi(
        id=1,
        name="Guntur Fruit Market",
        district="Guntur",
        state="Andhra Pradesh",
    )
    mock_price = Price(
        id=1,
        mandi_id=1,
        crop_id="banana",
        variety="Robusta",
        grade="FAQ",
        price_date=datetime.now(UTC).date(),
        modal_price_kg=25.0,
    )
    mock_db.execute.return_value.all.return_value = [(mock_price, mock_mandi)]

    with (
        patch(
            "backend.app.services.whatsapp.handler.get_whatsapp_provider",
            return_value=mock_provider,
        ),
        patch("backend.app.jobs.tasks.get_sync_db", return_value=mock_db),
    ):
        result = broadcast_daily_whatsapp_prices()
        assert result["status"] == "success"
        assert result["sent"] == 1
        assert len(mock_provider.sent_messages) == 1
        msg = mock_provider.sent_messages[0]
        assert msg["type"] == "template"
        assert msg["template_name"] == "daily_mandi_price_alert"
        assert msg["language_code"] == "te"
