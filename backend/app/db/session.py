"""
Database engines and session factories (Async & Sync).
"""

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import settings

# Async Engine (for FastAPI routes)
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)


@event.listens_for(async_engine.sync_engine, "connect")
def register_async_sqlite_geo_mocks(dbapi_connection: object, _connection_record: object) -> None:
    if hasattr(dbapi_connection, "create_function"):
        dbapi_connection.create_function("GeomFromEWKT", 1, lambda val: val)
        dbapi_connection.create_function("ST_GeomFromEWKT", 1, lambda val: val)
        dbapi_connection.create_function("AsEWKB", 1, lambda val: val)
        dbapi_connection.create_function("ST_AsEWKB", 1, lambda val: val)


AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# Sync Engine (for Celery workers, scripts, and Alembic)
sync_engine = create_engine(
    settings.DATABASE_SYNC_URL,
    echo=False,
    pool_pre_ping=True,
)


@event.listens_for(sync_engine, "connect")
def register_sync_sqlite_geo_mocks(dbapi_connection: object, _connection_record: object) -> None:
    if hasattr(dbapi_connection, "create_function"):
        dbapi_connection.create_function("GeomFromEWKT", 1, lambda val: val)
        dbapi_connection.create_function("ST_GeomFromEWKT", 1, lambda val: val)
        dbapi_connection.create_function("AsEWKB", 1, lambda val: val)
        dbapi_connection.create_function("ST_AsEWKB", 1, lambda val: val)


SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for yielding an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_db() -> Session:
    """Helper for sync context (Celery workers and CLI scripts). Caller is responsible for closing."""
    return SyncSessionLocal()
