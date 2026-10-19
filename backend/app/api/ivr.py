"""
FastAPI endpoints for Cloud Telephony IVR Webhooks.
Accepts standard x-www-form-urlencoded payloads from Exotel / Twilio,
as well as JSON payloads for test harnesses.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.monitoring import metrics_registry
from backend.app.core.rate_limit import RateLimitRule, get_client_ip, rate_limit_check
from backend.app.db.session import get_async_db
from backend.app.services.telephony.ivr_flow import ivr_flow_service

router = APIRouter(prefix="/ivr", tags=["IVR Telephony"])


async def extract_caller_data(
    request: Request,
) -> tuple[str, str]:
    """
    Extracts phone number and DTMF digits from either Form data, Query params, or JSON.
    """
    phone = ""
    digits = ""

    # Check query params first
    if "phone" in request.query_params:
        phone = request.query_params["phone"]
    if "Digits" in request.query_params:
        digits = request.query_params["Digits"]

    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        phone = str(form.get("From") or form.get("CallFrom") or form.get("phone") or phone)
        digits = str(form.get("Digits") or form.get("digits") or digits)
    elif "application/json" in content_type:
        try:
            body = await request.json()
            phone = str(body.get("From") or body.get("phone") or phone)
            digits = str(body.get("Digits") or body.get("digits") or digits)
        except Exception:
            pass

    return phone.strip(), digits.strip()


@router.post("/missed-call")
async def missed_call_webhook(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
) -> Response:
    """
    Webhook triggered when a farmer/user places a missed call.
    Triggers immediate outbound callback.
    """
    phone, _ = await extract_caller_data(request)
    if not phone and "From" in request.query_params:
        phone = request.query_params["From"]

    caller_id = phone or get_client_ip(request)
    await rate_limit_check("ivr_missed_call", caller_id, *RateLimitRule.IVR_MISSED_CALL)

    metrics_registry.record_ivr_call()

    xml_response = await ivr_flow_service.handle_missed_call(
        db=db, caller_phone=phone or "9999999999"
    )
    return Response(content=xml_response, media_type="application/xml")


@router.post("/callback")
async def callback_answered_webhook(
    request: Request,
    phone: Annotated[str | None, Query(description="Caller phone number")] = None,
    db: AsyncSession = Depends(get_async_db),
) -> Response:
    """
    Executed when the caller answers the callback.
    """
    caller_phone, _ = await extract_caller_data(request)
    target_phone = phone or caller_phone or "9999999999"
    await rate_limit_check("ivr_interactive", target_phone, *RateLimitRule.IVR)

    xml_response = await ivr_flow_service.handle_callback_answered(db=db, phone=target_phone)
    return Response(content=xml_response, media_type="application/xml")


@router.post("/language-selection")
async def language_selection_webhook(
    request: Request,
    phone: Annotated[str | None, Query(description="Caller phone")] = None,
    db: AsyncSession = Depends(get_async_db),
) -> Response:
    """
    Handles DTMF selection for language (1=te, 2=hi, 3=gu).
    """
    caller_phone, digits = await extract_caller_data(request)
    target_phone = phone or caller_phone or "9999999999"
    await rate_limit_check("ivr_interactive", target_phone, *RateLimitRule.IVR)

    xml_response = await ivr_flow_service.handle_language_selection(
        db=db, phone=target_phone, digits=digits or "1"
    )
    return Response(content=xml_response, media_type="application/xml")


@router.post("/district-selection")
async def district_selection_webhook(
    request: Request,
    phone: Annotated[str | None, Query(description="Caller phone")] = None,
    db: AsyncSession = Depends(get_async_db),
) -> Response:
    """
    Handles DTMF selection for district (1=Guntur, 2=NTR, 3=Tirupati, 4=Kurnool).
    """
    caller_phone, digits = await extract_caller_data(request)
    target_phone = phone or caller_phone or "9999999999"
    await rate_limit_check("ivr_interactive", target_phone, *RateLimitRule.IVR)

    xml_response = await ivr_flow_service.handle_district_selection(
        db=db, phone=target_phone, digits=digits or "1"
    )
    return Response(content=xml_response, media_type="application/xml")


@router.post("/crop-menu")
async def crop_menu_webhook(
    request: Request,
    phone: Annotated[str | None, Query(description="Caller phone")] = None,
    db: AsyncSession = Depends(get_async_db),
) -> Response:
    """
    Handles DTMF crop selection, speaks 3 nearest mandis prices under 1 minute,
    and plays post-answer menu (Press 1 to sell, 2 for transport, 9 to repeat).
    """
    caller_phone, digits = await extract_caller_data(request)
    target_phone = phone or caller_phone or "9999999999"
    await rate_limit_check("ivr_interactive", target_phone, *RateLimitRule.IVR)

    xml_response = await ivr_flow_service.handle_crop_selection(
        db=db, phone=target_phone, digits=digits or "1"
    )
    return Response(content=xml_response, media_type="application/xml")


@router.post("/action-selection")
async def action_selection_webhook(
    request: Request,
    phone: Annotated[str | None, Query(description="Caller phone")] = None,
    crop: Annotated[str, Query(description="Crop slug")] = "banana",
    db: AsyncSession = Depends(get_async_db),
) -> Response:
    """
    Handles post-answer choice:
    1: Sell produce
    2: Transport request
    9: Repeat prices
    """
    caller_phone, digits = await extract_caller_data(request)
    target_phone = phone or caller_phone or "9999999999"
    await rate_limit_check("ivr_interactive", target_phone, *RateLimitRule.IVR)

    xml_response = await ivr_flow_service.handle_action_selection(
        db=db, phone=target_phone, crop_id=crop, digits=digits or "9"
    )
    return Response(content=xml_response, media_type="application/xml")
