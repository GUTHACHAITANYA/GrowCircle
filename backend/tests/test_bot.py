"""
Tests for Telegram Bot Door:
- Text query 'banana price'
- GPS location sharing
- Multilingual responses
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.bot.telegram_bot import TelegramBotHandler


@pytest.mark.asyncio
async def test_bot_start_command(db_session: AsyncSession) -> None:
    reply = await TelegramBotHandler.handle_message(
        db=db_session,
        user_id="user_123",
        text="/start",
        language="te",
    )
    assert "గ్రో సర్కిల్" in reply
    assert "banana price" in reply.lower() or "ధర" in reply


@pytest.mark.asyncio
async def test_bot_banana_price_text_query(db_session: AsyncSession) -> None:
    reply = await TelegramBotHandler.handle_message(
        db=db_session,
        user_id="user_123",
        text="banana price",
        language="te",
    )
    assert "గ్రో సర్కిల్" in reply
    assert "Guntur" in reply
    assert "₹25" in reply or "₹25.0" in reply


@pytest.mark.asyncio
async def test_bot_location_sharing(db_session: AsyncSession) -> None:
    # User shares location near Guntur (16.3067, 80.4365)
    reply = await TelegramBotHandler.handle_message(
        db=db_session,
        user_id="user_123",
        location={"latitude": 16.3067, "longitude": 80.4365},
        language="en",
    )
    assert "GrowCircle" in reply
    assert "Guntur" in reply
    assert "₹25" in reply or "₹25.0" in reply
    assert "km" in reply
