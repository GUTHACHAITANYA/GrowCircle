"""
FastAPI endpoints for WhatsApp Cloud API Webhooks.
Includes Meta webhook subscription verification and message dispatcher.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.db.session import get_async_db
from backend.app.services.whatsapp.handler import whatsapp_handler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Cloud API"])


@router.get("/webhook")
async def verify_whatsapp_webhook(
    hub_mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    hub_verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    hub_challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
) -> Response:
    """
    Meta WhatsApp Cloud API Webhook verification handshake.
    Responds with hub.challenge when token matches.
    """
    expected_token = settings.WHATSAPP_VERIFY_TOKEN

    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        logger.info("WhatsApp webhook verified successfully.")
        return Response(content=hub_challenge or "", media_type="text/plain")

    logger.warning("WhatsApp webhook verification failed: invalid verify_token.")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.post("/webhook")
async def handle_whatsapp_webhook_event(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """
    Receives incoming WhatsApp Cloud API events:
    - Audio / Voice notes
    - Location sharing
    - Text messages
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from None

    actions = await whatsapp_handler.handle_inbound_event(db=db, payload=payload)
    return {"status": "EVENT_RECEIVED", "processed_count": str(len(actions))}
