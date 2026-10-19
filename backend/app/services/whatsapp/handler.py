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
from backend.app.models.transporter import Transporter
from backend.app.models.trip import Trip
from backend.app.models.user import User
from backend.app.services.geo import GeoService
from backend.app.services.pincode_service import PincodeService
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
                            f"*Voice Query Processed:*\n_{transcription.text}_\n\n"
                            f"*Today's Mandi Prices:*\n{spoken_summary}\n\n"
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

                        # Fetch nearest mandis via Phase 1 PostGIS GeoService (up to 5, within 100km, max 3 days)
                        nearby = await GeoService.get_nearby_mandis(
                            db=db,
                            user_lat=lat,
                            user_lng=lng,
                            crop_id="banana",
                            limit=5,
                            radius_km=100.0,
                            max_age_days=3,
                        )

                        spoken_summary = build_mandi_prices_spoken_summary(
                            mandis_data=nearby,
                            crop_id="banana",
                            lang=lang,
                        )

                        count = len(nearby)
                        title_count = "3" if count == 3 else f"{count}"
                        radius_note = (
                            f"\n_Only {count} mandis reported within 100 km (straight-line distance)._"
                            if count < 5 and count > 0
                            else "\n_Straight-line distance._"
                        )
                        text_body = (
                            f"{header}\n"
                            f"*{title_count} Nearest Mandis for Banana (straight-line distance):*\n\n{spoken_summary}{radius_note}\n\n"
                            f"_Reply 'SELL' to list your crop or 'TRANSPORT' for transport._"
                        )

                        await self.provider.send_text_message(from_phone, text_body)
                        actions_taken.append(
                            {
                                "action": "location_processed",
                                "to": from_phone,
                                "coords": (lat, lng),
                                "mandis_count": count,
                            }
                        )

                    # 3. Text Message
                    elif msg_type == "text":
                        body = msg.get("text", {}).get("body", "").strip()
                        upper_body = body.upper()

                        # Check if sender is a registered transporter for driver mobile flow
                        trans_stmt = select(Transporter).where(Transporter.user_id == user.id)
                        transporter = (await db.execute(trans_stmt)).scalar_one_or_none()

                        if transporter and (
                            upper_body.startswith("PICKUP")
                            or upper_body.startswith("DELIVER")
                            or upper_body.startswith("AVAILABLE")
                            or upper_body == "TRIPS"
                        ):
                            if upper_body.startswith("PICKUP"):
                                parts = body.split()
                                otp = parts[1] if len(parts) > 1 else ""
                                trip_stmt = (
                                    select(Trip)
                                    .where(
                                        Trip.transporter_id == transporter.id,
                                        Trip.status.in_(["assigned", "arrived_pickup"]),
                                    )
                                    .order_by(Trip.id.desc())
                                )
                                trip = (await db.execute(trip_stmt)).scalar_one_or_none()
                                if trip and trip.pickup_otp == otp.strip():
                                    trip.status = "in_transit"
                                    trip.pickup_confirmed_at = datetime.now(UTC)
                                    await db.commit()
                                    reply = (
                                        f"{header}\n*Pickup Verified!*\n"
                                        f"Trip #{trip.id} is now in transit with {trip.total_weight_kg:.0f} kg load to "
                                        f"{trip.dropoff_address or 'destination'}.\nDrive safely!"
                                    )
                                else:
                                    reply = (
                                        f"{header}\n[Invalid OTP] Invalid pickup OTP. "
                                        "Please verify the 4-digit code with the farmer upon loading."
                                    )
                            elif upper_body.startswith("DELIVER"):
                                parts = body.split()
                                otp = parts[1] if len(parts) > 1 else ""
                                trip_stmt = (
                                    select(Trip)
                                    .where(
                                        Trip.transporter_id == transporter.id,
                                        Trip.status == "in_transit",
                                    )
                                    .order_by(Trip.id.desc())
                                )
                                trip = (await db.execute(trip_stmt)).scalar_one_or_none()
                                if trip and trip.delivery_otp == otp.strip():
                                    trip.status = "delivered"
                                    trip.delivery_confirmed_at = datetime.now(UTC)
                                    transporter.trips_completed += 1
                                    await db.commit()
                                    reply = (
                                        f"{header}\n*Delivery Completed!*\n"
                                        f"Trip #{trip.id} delivered successfully. Handover authorized."
                                    )
                                else:
                                    reply = (
                                        f"{header}\n[Invalid OTP] Invalid delivery OTP. "
                                        "Please verify the code with the receiving buyer at the dock."
                                    )
                            elif upper_body.startswith("AVAILABLE"):
                                if "NO" in upper_body or "OFF" in upper_body:
                                    transporter.available_today = False
                                    await db.commit()
                                    reply = (
                                        f"{header}\n*Status Updated: OFFLINE*\n"
                                        "You will not receive new load dispatch suggestions today."
                                    )
                                else:
                                    transporter.available_today = True
                                    await db.commit()
                                    reply = (
                                        f"{header}\n*Status Updated: AVAILABLE TODAY*\n"
                                        f"Your {transporter.vehicle_model} is ready for load requests near {transporter.service_area_districts or 'Guntur'}."
                                    )
                            else:  # TRIPS
                                trip_stmt = (
                                    select(Trip)
                                    .where(Trip.transporter_id == transporter.id)
                                    .order_by(Trip.id.desc())
                                    .limit(3)
                                )
                                recent_trips = (await db.execute(trip_stmt)).scalars().all()
                                if not recent_trips:
                                    reply = f"{header}\nNo active trips assigned right now."
                                else:
                                    lines = [f"{header}\n*Your Recent Trips:*"]
                                    for tr in recent_trips:
                                        lines.append(
                                            f"• Trip #{tr.id}: {tr.status.upper()} | {tr.total_weight_kg:.0f} kg | "
                                            f"Guide Rate: ₹{tr.guide_rate:.0f}"
                                        )
                                    reply = "\n".join(lines)

                            await self.provider.send_text_message(from_phone, reply)
                            actions_taken.append(
                                {
                                    "action": "driver_command_processed",
                                    "to": from_phone,
                                    "command": body,
                                }
                            )
                            continue

                        # 3a. 6-digit Indian PIN code lookup (R3)
                        clean_digits = "".join(ch for ch in body if ch.isdigit())
                        if len(clean_digits) == 6:
                            pin_info = PincodeService.lookup_pincode(clean_digits)
                            if pin_info:
                                lat = pin_info["lat"]
                                lng = pin_info["lng"]
                                # Privacy (DPDP Act): store district-level only
                                user.district = pin_info["district"].lower()
                                await db.commit()

                                nearby = await GeoService.get_nearby_mandis(
                                    db=db,
                                    user_lat=lat,
                                    user_lng=lng,
                                    crop_id="banana",
                                    limit=5,
                                    radius_km=100.0,
                                    max_age_days=3,
                                )
                                spoken_summary = build_mandi_prices_spoken_summary(
                                    mandis_data=nearby,
                                    crop_id="banana",
                                    lang=lang,
                                )
                                count = len(nearby)
                                radius_note = (
                                    f"\n_Only {count} mandis reported within 100 km (straight-line distance)._"
                                    if count < 5 and count > 0
                                    else "\n_Straight-line distance._"
                                )
                                text_body = (
                                    f"{header}\n"
                                    f"*Nearest Mandis for PIN {clean_digits} ({pin_info['mandal']}, {pin_info['district']}) (straight-line distance):*\n\n"
                                    f"{spoken_summary}{radius_note}\n\n"
                                    f"_Reply 'SELL' to list your crop or 'TRANSPORT' for transport._"
                                )
                                await self.provider.send_text_message(from_phone, text_body)
                                actions_taken.append(
                                    {
                                        "action": "pincode_processed",
                                        "to": from_phone,
                                        "pincode": clean_digits,
                                        "coords": (lat, lng),
                                        "mandis_count": count,
                                    }
                                )
                                continue

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
                            f"*Prices for {crop_id.capitalize()}:*\n\n{spoken_summary}\n\n"
                            f"_Share your location or send a voice note for nearest mandis._"
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
