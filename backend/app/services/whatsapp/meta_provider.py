"""
Meta WhatsApp Cloud API production adapter.
Docs: https://developers.facebook.com/docs/whatsapp/cloud-api
"""

import logging

import httpx

from backend.app.core.config import settings
from backend.app.services.whatsapp.base import WhatsAppProvider

logger = logging.getLogger(__name__)

META_GRAPH_BASE_URL = "https://graph.facebook.com/v18.0"


class MetaWhatsAppCloudProvider(WhatsAppProvider):
    """
    Official Meta WhatsApp Cloud API Provider.
    """

    def __init__(self) -> None:
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def send_text_message(self, to_phone: str, text: str) -> bool:
        if not self.phone_number_id or not self.access_token:
            logger.warning("WhatsApp credentials unconfigured; skipping live API call.")
            return True

        url = f"{META_GRAPH_BASE_URL}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=self._headers())
            resp.raise_for_status()
            return True

    async def send_voice_note(
        self, to_phone: str, audio_bytes: bytes, caption: str | None = None
    ) -> bool:
        _ = caption
        if not self.phone_number_id or not self.access_token:
            logger.warning("WhatsApp credentials unconfigured; skipping live audio upload.")
            return True

        # In production Meta Cloud API:
        # 1. Upload audio to https://graph.facebook.com/v18.0/{phone_number_id}/media
        # 2. Send message with type="audio" and id=media_id
        upload_url = f"{META_GRAPH_BASE_URL}/{self.phone_number_id}/media"
        files = {"file": ("voice_note.ogg", audio_bytes, "audio/ogg")}
        data = {"messaging_product": "whatsapp", "type": "audio/ogg"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            upload_resp = await client.post(
                upload_url,
                files=files,
                data=data,
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            upload_resp.raise_for_status()
            media_id = upload_resp.json().get("id")

            # Send message
            msg_url = f"{META_GRAPH_BASE_URL}/{self.phone_number_id}/messages"
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to_phone,
                "type": "audio",
                "audio": {"id": media_id},
            }
            msg_resp = await client.post(msg_url, json=payload, headers=self._headers())
            msg_resp.raise_for_status()
            return True

    async def send_template_message(
        self,
        to_phone: str,
        template_name: str,
        language_code: str,
        components: list[dict],
    ) -> bool:
        if not self.phone_number_id or not self.access_token:
            logger.warning("WhatsApp credentials unconfigured; skipping live template send.")
            return True

        url = f"{META_GRAPH_BASE_URL}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": components,
            },
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=self._headers())
            resp.raise_for_status()
            return True
