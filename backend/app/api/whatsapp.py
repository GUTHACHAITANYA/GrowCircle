"""
FastAPI endpoints for WhatsApp Cloud API Webhooks.
Includes Meta webhook subscription verification and message dispatcher.
"""

import hashlib
import hmac
import logging
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.monitoring import metrics_registry
from backend.app.core.rate_limit import RateLimitRule, get_client_ip, rate_limit_check
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
    Responds with hub.challenge when token matches using constant-time comparison.
    """
    expected_token = settings.WHATSAPP_VERIFY_TOKEN

    if hub_mode == "subscribe" and secrets.compare_digest(hub_verify_token or "", expected_token):
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
    client_ip = get_client_ip(request)
    await rate_limit_check("whatsapp_webhook", client_ip, *RateLimitRule.WHATSAPP)
    metrics_registry.record_whatsapp_message()

    raw_body = await request.body()

    # If Meta App Secret is configured in production, verify HMAC-SHA256 signature
    app_secret = getattr(settings, "WHATSAPP_APP_SECRET", "")
    if app_secret:
        sig_header = request.headers.get("X-Hub-Signature-256", "")
        if not sig_header or not sig_header.startswith("sha256="):
            raise HTTPException(status_code=403, detail="Missing or invalid webhook signature")
        expected_sig = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig_header.split("sha256=")[1], expected_sig):
            raise HTTPException(status_code=403, detail="Invalid webhook signature")

    try:
        import json

        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from None

    actions = await whatsapp_handler.handle_inbound_event(db=db, payload=payload)
    return {"status": "EVENT_RECEIVED", "processed_count": str(len(actions))}
