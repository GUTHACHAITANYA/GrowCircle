"""
WhatsApp Webhook Message Processing Handler.
Handles voice notes (transcribe > text + voice note reply),
location sharing (3 nearest mandis), and text queries.
Reuses Phase 1 GeoService and SpeechManager exclusively.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.user import User
from backend.app.services.geo import GeoService
from backend.app.services.speech.adapters.mock_speech import (
    create_minimal_wav_bytes,
)
from backend.app.services.speech.manager import speech_manager
from backend.app.services.speech.pronunciation import (
    DISTRICT_KEYPAD_MAP,
    build_mandi_prices_spoken_summary,
)
from backend.app.services.whatsapp.base import WhatsAppProvider
from backend.app.services.whatsapp.meta_provider import (
    MetaWhatsAppCloudProvider,
)
from backend.app.services.whatsapp.mock_provider import MockWhatsAppProvider

logger = logging.getLogger(__name__)

BRAND_HEADERS = {
    "en": "*GrowCircle* | _Farm to everyone, full circle_\n",
    "te": "*గ్రో సర్కిల్* | _రైతు నుండి ప్రతిఒక్కరికీ, సంపూర్ణ వలయం_\n",
    "hi": "*ग्रो सर्कल* | _खेत से हर घर तक, पूरा घेरा_\n",
    "gu": "*ગ્રો સર્કલ* | _ખેતરથી દરેક સુધી, સંપૂર્ણ વર્તુળ_\n",
}


def get_whatsapp_provider() -> WhatsAppProvider:
    if settings.WHATSAPP_PROVIDER.lower().strip() == "meta":
        return MetaWhatsAppCloudProvider()
    return MockWhatsAppProvider()


class WhatsAppWebhookHandler:
    """
    Processes incoming Meta WhatsApp events and dispatches responses.
    """

    def __init__(self, provider: WhatsAppProvider | None = None) -> None:
        self.provider = provider or get_whatsapp_provider()

    async def get_or_create_user(self, db: AsyncSession, phone: str) -> User:
        clean_phone = phone.strip().replace(" ", "").replace("+", "")
        user = await db.scalar(select(User).where(User.phone == clean_phone))
        if not user:
            user = User(
                phone=clean_phone,
                language="te",
                district="guntur",
                role="farmer",
                consent_at=datetime.now(UTC),
            )
            db.add(user)
            await db.commit()
        return user

    async def handle_inbound_event(self, db: AsyncSession, payload: dict) -> list[dict]:
        """
        Parses Meta webhook envelope and processes messages.
        Returns a list of actions executed.
        """
        actions_taken = []
        entries = payload.get("entry", [])

        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])

                for msg in messages:
                    from_phone = msg.get("from", "")
                    msg_type = msg.get("type", "")

                    user = await self.get_or_create_user(db, from_phone)
                    lang = user.language or "te"
                    header = BRAND_HEADERS.get(lang, BRAND_HEADERS["te"])

                    # 1. Voice Note / Audio Message
                    if msg_type in ["audio", "voice"]:
                        # Extract / mock audio bytes
                        audio_bytes = create_minimal_wav_bytes(duration_sec=2.0)

                        # Transcribe via STT
                        transcription = await speech_manager.transcribe(audio_bytes, language=lang)
                        extracted = speech_manager.extract_intent_and_entities(transcription.text)
                        crop_id = extracted["crop_id"] or "banana"
                        district_key = extracted["district"] or user.district or "guntur"

                        # Lookup coordinates
                        lat, lng = 16.3067, 80.4365
                        for d_info in DISTRICT_KEYPAD_MAP.values():
                            if d_info["key"] == district_key:
                                lat = float(d_info["lat"])
                                lng = float(d_info["lng"])
                                break

                        # Fetch nearest mandis via Phase 1 GeoService
                        nearby = await GeoService.get_nearby_mandis(
                            db=db,
                            user_lat=lat,
                            user_lng=lng,
                            crop_id=crop_id,
                            limit=3,
                        )

                        # Synthesize voice note + text summary
                        audio_res, spoken_summary = (
                            await speech_manager.get_or_synthesize_mandi_prices(
                                mandis_data=nearby,
                                crop_id=crop_id,
                                district=district_key,
                                language=lang,
                                unit="kg",
                            )
                        )

                        text_body = (
                            f"{header}\n"
                            f"🎙️ *Voice Query Processed:*\n_{transcription.text}_\n\n"
                            f"📊 *Today's Mandi Prices:*\n{spoken_summary}\n\n"
                            f"_Reply 'SELL' to connect with buyers or 'TRANSPORT' for mini-trucks._"
                        )

                        # Reply with BOTH text and audio voice note
                        await self.provider.send_text_message(from_phone, text_body)
                        await self.provider.send_voice_note(from_phone, audio_res.audio_bytes)

                        actions_taken.append(
                            {
                                "action": "voice_note_processed",
                                "to": from_phone,
                                "transcription": transcription.text,
                            }
                        )

                    # 2. Location Sharing Message
                    elif msg_type == "location":
                        loc = msg.get("location", {})
                        lat = float(loc.get("latitude", 16.3067))
                        lng = float(loc.get("longitude", 80.4365))

                        # Fetch nearest mandis via Phase 1 PostGIS GeoService
                        nearby = await GeoService.get_nearby_mandis(
                            db=db,
                            user_lat=lat,
                            user_lng=lng,
                            crop_id="banana",
                            limit=3,
                        )

                        spoken_summary = build_mandi_prices_spoken_summary(
                            mandis_data=nearby,
                            crop_id="banana",
                            lang=lang,
                        )

                        text_body = (
                            f"{header}\n"
                            f"📍 *3 Nearest Mandis for Banana:*\n\n{spoken_summary}\n\n"
                            f"_Reply 'SELL' to list your crop or 'TRANSPORT' for transport._"
                        )

                        await self.provider.send_text_message(from_phone, text_body)
                        actions_taken.append(
                            {
                                "action": "location_processed",
                                "to": from_phone,
                                "coords": (lat, lng),
                            }
                        )

                    # 3. Text Message
                    elif msg_type == "text":
                        body = msg.get("text", {}).get("body", "").strip()
                        extracted = speech_manager.extract_intent_and_entities(body)
                        crop_id = extracted["crop_id"] or "banana"
                        district_key = extracted["district"] or user.district or "guntur"

                        lat, lng = 16.3067, 80.4365
                        for d_info in DISTRICT_KEYPAD_MAP.values():
                            if d_info["key"] == district_key:
                                lat = float(d_info["lat"])
                                lng = float(d_info["lng"])
                                break

                        nearby = await GeoService.get_nearby_mandis(
                            db=db,
                            user_lat=lat,
                            user_lng=lng,
                            crop_id=crop_id,
                            limit=3,
                        )

                        spoken_summary = build_mandi_prices_spoken_summary(
                            mandis_data=nearby,
                            crop_id=crop_id,
                            lang=lang,
                        )

                        text_body = (
                            f"{header}\n"
                            f"🌾 *Prices for {crop_id.capitalize()}:*\n\n{spoken_summary}\n\n"
                            f"_Share your location 📎 or send a voice note for nearest mandis._"
                        )

                        await self.provider.send_text_message(from_phone, text_body)
                        actions_taken.append(
                            {
                                "action": "text_processed",
                                "to": from_phone,
                                "query": body,
                            }
                        )

        return actions_taken


whatsapp_handler = WhatsAppWebhookHandler()
