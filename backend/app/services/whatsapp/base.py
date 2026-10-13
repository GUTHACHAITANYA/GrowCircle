"""
Abstract Base Interface for WhatsApp Cloud API providers.
"""

from abc import ABC, abstractmethod


class WhatsAppProvider(ABC):
    """Abstract interface for sending WhatsApp messages, media, and templates."""

    @abstractmethod
    async def send_text_message(self, to_phone: str, text: str) -> bool:
        """Sends an outbound WhatsApp text message."""

    @abstractmethod
    async def send_voice_note(
        self, to_phone: str, audio_bytes: bytes, caption: str | None = None
    ) -> bool:
        """Sends an outbound WhatsApp audio voice note."""

    @abstractmethod
    async def send_template_message(
        self,
        to_phone: str,
        template_name: str,
        language_code: str,
        components: list[dict],
    ) -> bool:
        """Sends an approved WhatsApp Business template message."""
