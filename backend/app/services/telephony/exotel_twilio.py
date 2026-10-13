"""
Exotel and Twilio cloud telephony adapters for production Indian deployments.
"""

import logging
from xml.sax.saxutils import escape

import httpx

from backend.app.core.config import settings
from backend.app.services.telephony.base import TelephonyProvider

logger = logging.getLogger(__name__)


class ExotelTelephonyProvider(TelephonyProvider):
    """
    Exotel Cloud Telephony Adapter for India (DID, Virtual Numbers, DLT compliant).
    Docs: https://support.exotel.com/support/solutions/articles/3000023070
    """

    def __init__(self) -> None:
        self.sid = settings.EXOTEL_SID
        self.token = settings.EXOTEL_TOKEN
        self.caller_id = settings.EXOTEL_CALLER_ID

    async def initiate_outbound_call(self, to_phone: str, callback_action_url: str) -> str:
        if not self.sid or not self.token or not self.caller_id:
            logger.warning("Exotel credentials unconfigured, returning simulation ID.")
            return "simulated-exotel-call"

        url = f"https://api.exotel.com/v1/Accounts/{self.sid}/Calls/connect.json"
        data = {
            "From": to_phone,
            "CallerId": self.caller_id,
            "Url": callback_action_url,
            "CallType": "trans",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, data=data, auth=(self.sid, self.token))
            resp.raise_for_status()
            res_json = resp.json()
            return res_json.get("Call", {}).get("Sid", "exotel-call")

    def render_ivr_response(
        self,
        say_text: str | None = None,
        audio_url: str | None = None,
        gather_action_url: str | None = None,
        num_digits: int = 1,
        hangup: bool = False,
    ) -> str:
        parts = ['<?xml version="1.0" encoding="UTF-8"?>', "<Response>"]
        if gather_action_url:
            parts.append(
                f'<Gather action="{escape(gather_action_url)}" method="POST" numDigits="{num_digits}" timeout="5">'
            )
            if audio_url:
                parts.append(f"<Play>{escape(audio_url)}</Play>")
            if say_text:
                parts.append(f"<Say>{escape(say_text)}</Say>")
            parts.append("</Gather>")
        else:
            if audio_url:
                parts.append(f"<Play>{escape(audio_url)}</Play>")
            if say_text:
                parts.append(f"<Say>{escape(say_text)}</Say>")
        if hangup:
            parts.append("<Hangup/>")
        parts.append("</Response>")
        return "\n".join(parts)


class TwilioTelephonyProvider(TelephonyProvider):
    """
    Twilio Telephony Adapter.
    """

    def __init__(self) -> None:
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_PHONE_NUMBER

    async def initiate_outbound_call(self, to_phone: str, callback_action_url: str) -> str:
        if not self.account_sid or not self.auth_token or not self.from_number:
            logger.warning("Twilio credentials unconfigured, returning simulation ID.")
            return "simulated-twilio-call"

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Calls.json"
        data = {
            "To": to_phone,
            "From": self.from_number,
            "Url": callback_action_url,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, data=data, auth=(self.account_sid, self.auth_token))
            resp.raise_for_status()
            res_json = resp.json()
            return res_json.get("sid", "twilio-call")

    def render_ivr_response(
        self,
        say_text: str | None = None,
        audio_url: str | None = None,
        gather_action_url: str | None = None,
        num_digits: int = 1,
        hangup: bool = False,
    ) -> str:
        parts = ['<?xml version="1.0" encoding="UTF-8"?>', "<Response>"]
        if gather_action_url:
            parts.append(
                f'<Gather action="{escape(gather_action_url)}" method="POST" numDigits="{num_digits}" timeout="5">'
            )
            if audio_url:
                parts.append(f"<Play>{escape(audio_url)}</Play>")
            if say_text:
                parts.append(f"<Say>{escape(say_text)}</Say>")
            parts.append("</Gather>")
        else:
            if audio_url:
                parts.append(f"<Play>{escape(audio_url)}</Play>")
            if say_text:
                parts.append(f"<Say>{escape(say_text)}</Say>")
        if hangup:
            parts.append("<Hangup/>")
        parts.append("</Response>")
        return "\n".join(parts)
