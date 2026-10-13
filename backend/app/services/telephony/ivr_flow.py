"""
IVR Telephony Flow Engine.
Implements missed call callback, language/district prompts, spoken nearest mandis,
and post-price action menus (1: sell, 2: transport, 9: repeat).
Reuses Phase 1 GeoService and database queries exclusively.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.inquiry import Inquiry
from backend.app.models.user import User
from backend.app.services.geo import GeoService
from backend.app.services.speech.manager import speech_manager
from backend.app.services.speech.pronunciation import (
    DISTRICT_KEYPAD_MAP,
    PRERECORDED_PHRASES,
)
from backend.app.services.telephony.base import TelephonyProvider
from backend.app.services.telephony.exotel_twilio import (
    ExotelTelephonyProvider,
    TwilioTelephonyProvider,
)
from backend.app.services.telephony.mock_provider import MockTelephonyProvider

logger = logging.getLogger(__name__)


def get_telephony_provider() -> TelephonyProvider:
    provider = settings.TELEPHONY_PROVIDER.lower().strip()
    if provider == "exotel":
        return ExotelTelephonyProvider()
    elif provider == "twilio":
        return TwilioTelephonyProvider()
    return MockTelephonyProvider()


class IVRFlowService:
    """
    Manages the conversational telephone lifecycle for farmers and buyers.
    """

    def __init__(self, provider: TelephonyProvider | None = None) -> None:
        self.provider = provider or get_telephony_provider()

    async def handle_missed_call(self, db: AsyncSession, caller_phone: str) -> str:
        """
        Triggered when a caller places a missed call.
        Saves or retrieves caller and triggers outbound callback.
        """
        clean_phone = caller_phone.strip().replace(" ", "").replace("+", "")

        user = await db.scalar(select(User).where(User.phone == clean_phone))
        if not user:
            user = User(
                phone=clean_phone,
                language="",  # Empty marks first-call language prompt required
                district=None,
                role="farmer",
            )
            db.add(user)
            await db.commit()

        base_url = settings.IVR_CALLBACK_BASE_URL.rstrip("/")
        callback_url = f"{base_url}/ivr/callback?phone={clean_phone}"

        call_id = await self.provider.initiate_outbound_call(clean_phone, callback_url)
        logger.info("Outbound callback initiated for %s: %s", clean_phone, call_id)

        # Immediate hangup for missed call webhook
        return self.provider.render_ivr_response(hangup=True)

    async def handle_callback_answered(self, db: AsyncSession, phone: str) -> str:
        """
        Executed when caller answers the callback.
        Checks if language or district are set; routes accordingly.
        """
        clean_phone = phone.strip().replace(" ", "").replace("+", "")
        user = await db.scalar(select(User).where(User.phone == clean_phone))
        lang = user.language if user and user.language else ""

        # 1. First-call language menu (1=te, 2=hi, 3=gu)
        if not lang or lang not in ["te", "hi", "gu", "en"]:
            text = (
                "Welcome to GrowCircle. "
                + PRERECORDED_PHRASES["language_menu"]["en"]
                + " "
                + PRERECORDED_PHRASES["language_menu"]["te"]
            )
            return self.provider.render_ivr_response(
                say_text=text,
                gather_action_url=f"/ivr/language-selection?phone={clean_phone}",
                num_digits=1,
            )

        # 2. District selection required if not saved
        if not user or not user.district:
            prompt_text = (
                PRERECORDED_PHRASES["welcome"].get(lang, "")
                + " "
                + PRERECORDED_PHRASES["district_prompt"].get(lang, "")
            )
            return self.provider.render_ivr_response(
                say_text=prompt_text,
                gather_action_url=f"/ivr/district-selection?phone={clean_phone}",
                num_digits=1,
            )

        # 3. Both saved: Welcome + Crop Menu
        prompt_text = (
            PRERECORDED_PHRASES["welcome"].get(lang, "")
            + " "
            + PRERECORDED_PHRASES["crop_menu"].get(lang, "")
        )
        return self.provider.render_ivr_response(
            say_text=prompt_text,
            gather_action_url=f"/ivr/crop-menu?phone={clean_phone}",
            num_digits=1,
        )

    async def handle_language_selection(self, db: AsyncSession, phone: str, digits: str) -> str:
        """
        Processes DTMF language choice (1=te, 2=hi, 3=gu).
        """
        clean_phone = phone.strip().replace(" ", "").replace("+", "")
        lang_map = {"1": "te", "2": "hi", "3": "gu"}
        chosen_lang = lang_map.get(digits.strip(), "te")

        user = await db.scalar(select(User).where(User.phone == clean_phone))
        if user:
            user.language = chosen_lang
            await db.commit()

        # If district still not set, ask for district
        if not user or not user.district:
            district_prompt = PRERECORDED_PHRASES["district_prompt"].get(chosen_lang, "")
            return self.provider.render_ivr_response(
                say_text=district_prompt,
                gather_action_url=f"/ivr/district-selection?phone={clean_phone}",
                num_digits=1,
            )

        # District already set -> proceed to crop menu
        crop_prompt = PRERECORDED_PHRASES["crop_menu"].get(chosen_lang, "")
        return self.provider.render_ivr_response(
            say_text=crop_prompt,
            gather_action_url=f"/ivr/crop-menu?phone={clean_phone}",
            num_digits=1,
        )

    async def handle_district_selection(self, db: AsyncSession, phone: str, digits: str) -> str:
        """
        Processes DTMF district choice (1=Guntur, 2=NTR, 3=Tirupati, 4=Kurnool).
        """
        clean_phone = phone.strip().replace(" ", "").replace("+", "")
        district_entry = DISTRICT_KEYPAD_MAP.get(digits.strip(), DISTRICT_KEYPAD_MAP["1"])
        district_key = district_entry["key"]

        user = await db.scalar(select(User).where(User.phone == clean_phone))
        lang = "te"
        if user:
            user.district = district_key
            lang = user.language or "te"
            await db.commit()

        crop_prompt = PRERECORDED_PHRASES["crop_menu"].get(lang, "")
        return self.provider.render_ivr_response(
            say_text=crop_prompt,
            gather_action_url=f"/ivr/crop-menu?phone={clean_phone}",
            num_digits=1,
        )

    async def handle_crop_selection(self, db: AsyncSession, phone: str, digits: str) -> str:
        """
        Queries Phase 1 GeoService for the 3 nearest mandis and speaks prices.
        Appends post-answer menu: 'Press 1 to sell, 2 for transport, 9 to repeat'.
        """
        clean_phone = phone.strip().replace(" ", "").replace("+", "")
        crop_map = {"1": "banana"}
        crop_id = crop_map.get(digits.strip(), "banana")

        user = await db.scalar(select(User).where(User.phone == clean_phone))
        lang = user.language if user and user.language else "te"
        district_key = user.district if user and user.district else "guntur"

        # Coordinates for district
        lat = 16.3067
        lng = 80.4365
        for d_info in DISTRICT_KEYPAD_MAP.values():
            if d_info["key"] == district_key:
                lat = float(d_info["lat"])
                lng = float(d_info["lng"])
                break

        # Reusing Phase 1 GeoService spatial calculation
        nearby = await GeoService.get_nearby_mandis(
            db=db,
            user_lat=lat,
            user_lng=lng,
            crop_id=crop_id,
            limit=3,
        )

        # Synthesize spoken summary under 1 minute with cache
        _, spoken_text = await speech_manager.get_or_synthesize_mandi_prices(
            mandis_data=nearby,
            crop_id=crop_id,
            district=district_key,
            language=lang,
            unit="kg",
        )

        post_menu = PRERECORDED_PHRASES["post_action_menu"].get(lang, "")
        full_speech = f"{spoken_text} {post_menu}"

        return self.provider.render_ivr_response(
            say_text=full_speech,
            gather_action_url=f"/ivr/action-selection?phone={clean_phone}&crop={crop_id}",
            num_digits=1,
        )

    async def handle_action_selection(
        self, db: AsyncSession, phone: str, crop_id: str, digits: str
    ) -> str:
        """
        Handles post-answer DTMF choices:
        1: Sell produce
        2: Transport request
        9: Repeat prices
        """
        clean_phone = phone.strip().replace(" ", "").replace("+", "")
        choice = digits.strip()

        user = await db.scalar(select(User).where(User.phone == clean_phone))
        lang = user.language if user and user.language else "te"
        district = user.district if user and user.district else "guntur"

        if choice == "9":
            # Repeat prices
            return await self.handle_crop_selection(db, clean_phone, digits="1")

        if choice == "1":
            # Log sell lead
            inquiry = Inquiry(
                phone=clean_phone,
                channel="ivr",
                intent="sell",
                crop_id=crop_id,
                district=district,
                language=lang,
                status="pending",
            )
            db.add(inquiry)
            await db.commit()
            ack_text = PRERECORDED_PHRASES["sell_acknowledged"].get(lang, "")
            return self.provider.render_ivr_response(say_text=ack_text, hangup=True)

        if choice == "2":
            # Log transport lead
            inquiry = Inquiry(
                phone=clean_phone,
                channel="ivr",
                intent="transport",
                crop_id=crop_id,
                district=district,
                language=lang,
                status="pending",
            )
            db.add(inquiry)
            await db.commit()
            ack_text = PRERECORDED_PHRASES["transport_acknowledged"].get(lang, "")
            return self.provider.render_ivr_response(say_text=ack_text, hangup=True)

        # Default fallback
        return self.provider.render_ivr_response(
            say_text="Thank you for using GrowCircle.", hangup=True
        )


ivr_flow_service = IVRFlowService()
