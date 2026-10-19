"""
OTP Provider Factory module.
Requirement 1: SMS or WhatsApp OTP provider behind an interface, with mock provider only in demo mode.
"""

from backend.app.core.config import settings
from backend.app.services.otp.base import OtpProvider
from backend.app.services.otp.mock_provider import MockOtpProvider
from backend.app.services.otp.sms_provider import SmsOtpProvider
from backend.app.services.otp.whatsapp_provider import WhatsAppOtpProvider


def get_otp_provider() -> OtpProvider:
    """
    Returns appropriate OTP provider:
    - MockOtpProvider in demo mode or test/development
    - SmsOtpProvider / WhatsAppOtpProvider in staging and production
    """
    if settings.APP_MODE == "demo" or settings.ENVIRONMENT in ("development", "test"):
        return MockOtpProvider()

    # If WhatsApp is preferred
    if getattr(settings, "OTP_CHANNEL", "sms").lower() == "whatsapp":
        return WhatsAppOtpProvider()

    return SmsOtpProvider()


def is_real_otp_provider_configured() -> bool:
    """
    Returns True only when a real SMS or WhatsApp provider is configured and active.
    Returns False in demo mode or development/test environments.
    """
    if settings.APP_MODE == "demo" or settings.ENVIRONMENT in ("development", "test"):
        return False

    channel = getattr(settings, "OTP_CHANNEL", "sms").lower()
    if channel == "whatsapp":
        return bool(getattr(settings, "META_WHATSAPP_TOKEN", "").strip())
    return bool(getattr(settings, "SMS_API_KEY", "").strip())


def get_otp_provider_status() -> dict[str, object]:
    """Returns runtime status of OTP provider for client UI messaging."""
    is_real = is_real_otp_provider_configured()
    channel = getattr(settings, "OTP_CHANNEL", "sms").lower()
    return {
        "is_real_provider": is_real,
        "provider_type": channel if is_real else "mock",
        "app_mode": settings.APP_MODE,
        "environment": settings.ENVIRONMENT,
        "message": (
            f"Active live {channel.upper()} OTP Gateway"
            if is_real
            else "Demo mode — verification code simulated"
        ),
    }


__all__ = [
    "OtpProvider",
    "MockOtpProvider",
    "SmsOtpProvider",
    "WhatsAppOtpProvider",
    "get_otp_provider",
    "is_real_otp_provider_configured",
    "get_otp_provider_status",
]

