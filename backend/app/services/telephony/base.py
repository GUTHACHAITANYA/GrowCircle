"""
Base abstract interface for Cloud Telephony providers (Exotel, Twilio, Mock).
"""

from abc import ABC, abstractmethod


class TelephonyProvider(ABC):
    """Abstract provider for telephony call initiation and IVR markup rendering."""

    @abstractmethod
    async def initiate_outbound_call(self, to_phone: str, callback_action_url: str) -> str:
        """
        Triggers an outbound callback call to the given phone number.
        Returns a call ID / transaction identifier.
        """

    @abstractmethod
    def render_ivr_response(
        self,
        say_text: str | None = None,
        audio_url: str | None = None,
        gather_action_url: str | None = None,
        num_digits: int = 1,
        hangup: bool = False,
    ) -> str:
        """
        Renders telephony response markup (TwiML / provider XML).
        """
