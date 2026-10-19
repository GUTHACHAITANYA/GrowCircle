"""
GrowCircle Telegram Bot Door.
Processes text queries ('banana price') and location coordinates,
returning the 3 nearest mandis in the user's saved language.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.geo import GeoService

logger = logging.getLogger(__name__)

BRAND_TRANSLATIONS = {
    "en": {
        "name": "GrowCircle",
        "tagline": "Farm to everyone, full circle",
        "nearest": "Nearest Mandis for Banana today:",
    },
    "te": {
        "name": "గ్రో సర్కిల్",
        "tagline": "రైతు నుండి ప్రతిఒక్కరికీ, సంపూర్ణ వలయం",
        "nearest": "నేటి అరటిపండు ధరలు - సమీప మండీలు:",
    },
    "hi": {
        "name": "ग्रो सर्कल",
        "tagline": "खेत से हर घर तक, पूरा घेरा",
        "nearest": "आज के केले के भाव - नजदीकी मंडियां:",
    },
    "gu": {
        "name": "ગ્રો સર્કલ",
        "tagline": "ખેતરથી દરેક સુધી, સંપૂર્ણ વર્તુળ",
        "nearest": "આજના કેળાના ભાવ - નજીકના માર્કેટ યાર્ડ:",
    },
}


class TelegramBotHandler:
    """
    Handles Telegram Bot text and location events.
    Includes mockable test interface for CI.
    """

    @classmethod
    async def handle_message(
        cls,
        db: AsyncSession,
        user_id: str,
        text: str | None = None,
        location: dict[str, float] | None = None,
        language: str = "te",
    ) -> str:
        """
        Processes a Telegram event and returns the formatted response string.
        """
        _ = user_id  # Reserved for tracking user session / language preference
        lang = language if language in BRAND_TRANSLATIONS else "te"
        b_info = BRAND_TRANSLATIONS[lang]

        # 1. Location Sharing Handler (GPS coords provided)
        if location and "latitude" in location and "longitude" in location:
            lat = location["latitude"]
            lng = location["longitude"]

            nearby = await GeoService.get_nearby_mandis(
                db=db,
                user_lat=lat,
                user_lng=lng,
                crop_id="banana",
                limit=3,
            )

            if not nearby:
                return (
                    f"*{b_info['name']}*\n"
                    f"_{b_info['tagline']}_\n\n"
                    f"No active banana mandi prices found near your location."
                )

            lines = [
                f"*{b_info['name']}*",
                f"_{b_info['tagline']}_\n",
                f"*{b_info['nearest']}*\n",
            ]

            for idx, m in enumerate(nearby, start=1):
                dist_str = f"{m['distance_km']} km" if m.get("distance_km") is not None else ""
                lines.append(
                    f"{idx}. *{m['mandi_name']}* ({m['district']}) - {dist_str}\n"
                    f"   *₹{m['modal_price_kg']}/kg* (₹{int(m['modal_price_quintal'])}/qtl)\n"
                    f"   Updated: {m['price_date']}\n"
                )

            lines.append("Always verified Agmarknet data • No login needed")
            return "\n".join(lines)

        # 2. Text Query Handler
        text_clean = (text or "").lower().strip()

        if "/start" in text_clean:
            return (
                f"*{b_info['name']}*\n"
                f"_{b_info['tagline']}_\n\n"
                f"Welcome! Send *'banana price'* or share your *Location* to see the 3 nearest mandi rates."
            )

        if any(term in text_clean for term in ["banana", "price", "ధర", "भाव", "ભાવ"]):
            # Default to Guntur center coordinates (16.3067, 80.4365) if no GPS provided
            nearby = await GeoService.get_nearby_mandis(
                db=db,
                user_lat=16.3067,
                user_lng=80.4365,
                crop_id="banana",
                limit=3,
            )

            lines = [
                f"*{b_info['name']}*",
                f"_{b_info['tagline']}_\n",
                f"*{b_info['nearest']}*\n",
            ]

            for idx, m in enumerate(nearby, start=1):
                dist_str = f"~{m['distance_km']} km" if m.get("distance_km") is not None else ""
                lines.append(
                    f"{idx}. *{m['mandi_name']}* ({m['district']}) {dist_str}\n"
                    f"   *₹{m['modal_price_kg']}/kg* (₹{int(m['modal_price_quintal'])}/quintal)\n"
                    f"   {m['price_date']}\n"
                )

            lines.append("Share your location anytime to see your nearest mandis!")
            return "\n".join(lines)

        return (
            f"*{b_info['name']}*\n"
            f"Please type *'banana price'* or share your *location* to get today's rates."
        )

