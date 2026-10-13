"""
Mock WhatsApp Provider for local testing, CI, and credential-less sandboxes.
Records all sent text, voice notes, and templates in memory.
"""

from backend.app.services.whatsapp.base import WhatsAppProvider


class MockWhatsAppProvider(WhatsAppProvider):
    """
    Mock implementation recording all outbound WhatsApp traffic.
    """

    def __init__(self) -> None:
        self.sent_messages: list[dict] = []

    async def send_text_message(self, to_phone: str, text: str) -> bool:
        self.sent_messages.append({"type": "text", "to": to_phone, "text": text})
        return True

    async def send_voice_note(
        self, to_phone: str, audio_bytes: bytes, caption: str | None = None
    ) -> bool:
        self.sent_messages.append(
            {
                "type": "audio",
                "to": to_phone,
                "audio_bytes_len": len(audio_bytes),
                "caption": caption,
            }
        )
        return True

    async def send_template_message(
        self,
        to_phone: str,
        template_name: str,
        language_code: str,
        components: list[dict],
    ) -> bool:
        self.sent_messages.append(
            {
                "type": "template",
                "to": to_phone,
                "template_name": template_name,
                "language_code": language_code,
                "components": components,
            }
        )
        return True

    def clear(self) -> None:
        self.sent_messages.clear()
