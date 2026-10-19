"""
Tests for IVR Telephony Door:
Missed call > callback > Language menu > District keypad > Crop prices > Action choices (1: sell, 2: transport, 9: repeat).
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.inquiry import Inquiry
from backend.app.models.user import User


@pytest.mark.asyncio
async def test_ivr_missed_call_initiates_callback(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A missed call triggers outbound callback call and registers user."""
    caller_phone = "9848022338"
    response = await client.post(
        "/ivr/missed-call",
        params={"From": caller_phone},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "<Hangup/>" in response.text

    # Verify user saved in DB
    user = await db_session.scalar(select(User).where(User.phone == caller_phone))
    assert user is not None
    assert user.role == "farmer"


@pytest.mark.asyncio
async def test_ivr_callback_first_call_language_menu(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Callback for first-time caller without saved language prompts language menu."""
    _ = db_session
    caller_phone = "9848011223"
    # Initiate missed call first
    await client.post("/ivr/missed-call", params={"From": caller_phone})

    # Caller answers callback
    response = await client.post("/ivr/callback", params={"phone": caller_phone})
    assert response.status_code == 200
    assert "<Gather" in response.text
    assert "/ivr/language-selection" in response.text
    assert "Telugu" in response.text
    assert "1" in response.text


@pytest.mark.asyncio
async def test_ivr_language_selection_and_district_prompt(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Selecting language saves preference and prompts for district."""
    caller_phone = "9848033445"
    await client.post("/ivr/missed-call", params={"From": caller_phone})

    # Select Telugu (DTMF '1')
    response = await client.post(
        "/ivr/language-selection",
        params={"phone": caller_phone, "Digits": "1"},
    )
    assert response.status_code == 200
    assert "/ivr/district-selection" in response.text

    # Verify language saved as 'te'
    user = await db_session.scalar(select(User).where(User.phone == caller_phone))
    assert user is not None
    assert user.language == "te"


@pytest.mark.asyncio
async def test_ivr_district_selection_saves_district(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Selecting district saves district and proceeds to crop menu."""
    caller_phone = "9848044556"
    await client.post("/ivr/missed-call", params={"From": caller_phone})
    await client.post("/ivr/language-selection", params={"phone": caller_phone, "Digits": "1"})

    # Select Guntur (DTMF '1')
    response = await client.post(
        "/ivr/district-selection",
        params={"phone": caller_phone, "Digits": "1"},
    )
    assert response.status_code == 200
    assert "/ivr/crop-menu" in response.text

    # Verify district saved
    user = await db_session.scalar(select(User).where(User.phone == caller_phone))
    assert user is not None
    assert user.district == "guntur"


@pytest.mark.asyncio
async def test_ivr_pincode_keypad_entry_saves_district(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Entering 6-digit PIN code via keypad resolves district and proceeds to crop menu."""
    caller_phone = "9848044777"
    await client.post("/ivr/missed-call", params={"From": caller_phone})
    await client.post("/ivr/language-selection", params={"phone": caller_phone, "Digits": "1"})

    # Key in PIN code 522001
    response = await client.post(
        "/ivr/district-selection",
        params={"phone": caller_phone, "Digits": "522001"},
    )
    assert response.status_code == 200
    assert "/ivr/crop-menu" in response.text

    # Verify district resolved to guntur
    user = await db_session.scalar(select(User).where(User.phone == caller_phone))
    assert user is not None
    assert user.district == "guntur"


@pytest.mark.asyncio
async def test_ivr_crop_menu_speaks_prices_and_post_menu(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Selecting Banana speaks 3 nearest mandis and offers post-answer menu."""
    caller_phone = "9848055667"
    # Seed user with saved language and district
    user = User(phone=caller_phone, language="te", district="guntur", role="farmer")
    db_session.add(user)
    await db_session.commit()

    # DTMF '1' for Banana
    response = await client.post(
        "/ivr/crop-menu",
        params={"phone": caller_phone, "Digits": "1"},
    )
    assert response.status_code == 200
    assert "<Gather" in response.text
    assert "/ivr/action-selection" in response.text

    # Content verification: speaks nearest mandis and action instructions
    body = response.text
    assert "అరటిపండు" in body  # Telugu crop name
    assert "గుంటూరు" in body  # Mandi name
    assert "1" in body  # Action 1 to sell
    assert "2" in body  # Action 2 for transport
    assert "9" in body  # Action 9 to repeat


@pytest.mark.asyncio
async def test_ivr_action_selection_creates_sell_inquiry(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Pressing 1 records a sell intent inquiry in database."""
    caller_phone = "9848066778"
    user = User(phone=caller_phone, language="te", district="guntur", role="farmer")
    db_session.add(user)
    await db_session.commit()

    # DTMF '1' to sell
    response = await client.post(
        "/ivr/action-selection",
        params={"phone": caller_phone, "crop": "banana", "Digits": "1"},
    )
    assert response.status_code == 200
    assert "<Hangup/>" in response.text
    assert "అమ్మకం" in response.text  # Sell ack

    # Check Inquiry record in DB
    inquiry = await db_session.scalar(select(Inquiry).where(Inquiry.phone == caller_phone))
    assert inquiry is not None
    assert inquiry.intent == "sell"
    assert inquiry.crop_id == "banana"
    assert inquiry.channel == "ivr"
    assert inquiry.status == "pending"


@pytest.mark.asyncio
async def test_ivr_action_selection_creates_transport_inquiry(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Pressing 2 records a transport intent inquiry in database."""
    caller_phone = "9848077889"
    user = User(phone=caller_phone, language="te", district="guntur", role="farmer")
    db_session.add(user)
    await db_session.commit()

    # DTMF '2' for transport
    response = await client.post(
        "/ivr/action-selection",
        params={"phone": caller_phone, "crop": "banana", "Digits": "2"},
    )
    assert response.status_code == 200
    assert "<Hangup/>" in response.text
    assert "రవాణా" in response.text  # Transport ack

    inquiry = await db_session.scalar(select(Inquiry).where(Inquiry.phone == caller_phone))
    assert inquiry is not None
    assert inquiry.intent == "transport"


@pytest.mark.asyncio
async def test_ivr_action_selection_repeats_prices(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Pressing 9 repeats the price announcement."""
    caller_phone = "9848088990"
    user = User(phone=caller_phone, language="te", district="guntur", role="farmer")
    db_session.add(user)
    await db_session.commit()

    # DTMF '9' to repeat
    response = await client.post(
        "/ivr/action-selection",
        params={"phone": caller_phone, "crop": "banana", "Digits": "9"},
    )
    assert response.status_code == 200
    assert "<Gather" in response.text
    assert "/ivr/action-selection" in response.text
    assert "అరటిపండు" in response.text
