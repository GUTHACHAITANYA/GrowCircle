"""
Core application configuration using Pydantic Settings.
"""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    APP_MODE: str = "demo"  # 'demo' or 'production'
    DEBUG: bool = True

    # Database URLs
    # Defaults to PostgreSQL PostGIS, with graceful SQLite fallback for isolated unit tests
    DATABASE_URL: str = (
        "postgresql+asyncpg://growcircle:growcircle_dev@localhost:5432/growcircle_db"
    )
    DATABASE_SYNC_URL: str = "postgresql://growcircle:growcircle_dev@localhost:5432/growcircle_db"

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # External APIs
    DATA_GOV_API_KEY: str = ""
    DATA_GOV_RESOURCE_ID: str = "9ef84268-d588-465a-a308-a864a43d0070"

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""

    # Telephony & IVR
    TELEPHONY_PROVIDER: str = "mock"  # 'mock', 'exotel', 'twilio'
    EXOTEL_SID: str = ""
    EXOTEL_TOKEN: str = ""
    EXOTEL_CALLER_ID: str = ""
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    IVR_CALLBACK_BASE_URL: str = "http://localhost:8000"

    # Speech AI (STT & TTS)
    STT_PROVIDER: str = "mock"  # 'mock', 'bhashini', 'sarvam', 'google'
    TTS_PROVIDER: str = "mock"  # 'mock', 'bhashini', 'sarvam', 'google'
    BHASHINI_USER_ID: str = ""
    BHASHINI_API_KEY: str = ""
    BHASHINI_PIPELINE_ID: str = ""
    SARVAM_API_KEY: str = ""
    GOOGLE_SPEECH_API_KEY: str = ""

    # WhatsApp Cloud API
    WHATSAPP_PROVIDER: str = "mock"  # 'mock', 'meta'
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_VERIFY_TOKEN: str = "growcircle_webhook_token_2026"
    WHATSAPP_APP_SECRET: str = ""

    # Security & OTP
    SECRET_KEY: str = "dev-secret-key-growcircle-phase1-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080
    ADMIN_2FA_CODE: str = "654321"
    OTP_CHANNEL: str = "sms"  # 'sms' or 'whatsapp'
    SMS_API_KEY: str = ""
    META_WHATSAPP_TOKEN: str = ""
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "https://growcircle.in",
        "https://app.growcircle.in",
    ]

    # Observability & Monitoring
    SENTRY_DSN: str = ""
    PROMETHEUS_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.APP_MODE not in ("demo", "production"):
            raise ValueError(
                f"Invalid APP_MODE '{self.APP_MODE}'. Must be 'demo' or 'production'."
            )
        if self.ENVIRONMENT in ("production", "staging"):
            if not self.SECRET_KEY or self.SECRET_KEY.startswith("dev-secret-key"):
                raise ValueError(
                    f"Production/staging environment '{self.ENVIRONMENT}' cannot use the insecure default SECRET_KEY."
                )
            if self.DEBUG:
                raise ValueError(
                    f"DEBUG mode must be False in production/staging environment '{self.ENVIRONMENT}'."
                )
        return self


settings = Settings()


