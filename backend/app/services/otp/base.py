"""
Abstract base class for OTP providers (SMS, WhatsApp, and Mock).
"""

from abc import ABC, abstractmethod


class OtpProvider(ABC):
    @abstractmethod
    async def send_otp(self, phone: str, otp: str) -> bool:
        """
        Dispatches a numeric one-time password to the specified phone number.
        Returns True on successful dispatch, False otherwise.
        """
        pass
