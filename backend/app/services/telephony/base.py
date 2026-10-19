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
    async def initiate_masked_call(
        self, caller_phone: str, callee_phone: str, context_id: str
    ) -> str:
        """
        Bridges a phone call between caller and callee through a proxy virtual number (DID)
        so neither party's personal phone number is exposed (DPDP Act privacy).
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

