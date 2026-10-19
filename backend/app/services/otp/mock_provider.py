"""
Mock OTP Provider for demo, development, and automated test environments.
Captures dispatched OTPs in memory for instant inspection.
"""

import logging
from typing import ClassVar

from backend.app.services.otp.base import OtpProvider

logger = logging.getLogger(__name__)


class MockOtpProvider(OtpProvider):
    # In-memory history of sent OTPs: list of {"phone": str, "otp": str}
    sent_messages: ClassVar[list[dict[str, str]]] = []

    async def send_otp(self, phone: str, otp: str) -> bool:
        clean_phone = phone.strip().replace(" ", "").replace("+", "")
        record = {"phone": clean_phone, "otp": otp}
        self.sent_messages.append(record)
        logger.info(f"[MockOtpProvider] Dispatched OTP '{otp}' to {clean_phone}")
        return True

    @classmethod
    def get_last_otp(cls, phone: str) -> str | None:
        clean_phone = phone.strip().replace(" ", "").replace("+", "")
        for msg in reversed(cls.sent_messages):
            if msg["phone"] == clean_phone:
                return msg["otp"]
        return None

    @classmethod
    def clear(cls) -> None:
        cls.sent_messages.clear()
