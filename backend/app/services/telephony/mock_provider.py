"""
Mock Telephony Provider for tests, local emulation, and CI.
Generates compliant TwiML-compatible XML for telephony engines.
"""

import uuid
from xml.sax.saxutils import escape

from backend.app.services.telephony.base import TelephonyProvider


class MockTelephonyProvider(TelephonyProvider):
    """
    In-memory mock telephony provider logging calls and returning clean XML.
    """

    def __init__(self) -> None:
        self.outbound_calls: list[dict[str, str]] = []

    async def initiate_outbound_call(self, to_phone: str, callback_action_url: str) -> str:
        call_id = f"mock-call-{uuid.uuid4().hex[:8]}"
        self.outbound_calls.append(
            {
                "call_id": call_id,
                "to_phone": to_phone,
                "callback_url": callback_action_url,
            }
        )
        return call_id

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
