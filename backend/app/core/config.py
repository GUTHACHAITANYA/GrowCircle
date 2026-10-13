"""
Core application configuration using Pydantic Settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
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

    # Security
    SECRET_KEY: str = "dev-secret-key-growcircle-phase1-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
