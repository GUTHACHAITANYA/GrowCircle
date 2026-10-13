"""
Pytest configuration and async fixtures for FastAPI testing.
Uses an isolated in-memory SQLite database with mock Geo functions for testing.
"""

from collections.abc import AsyncGenerator
from datetime import date

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.db.base import Base
from backend.app.db.session import get_async_db
from backend.app.main import app
from backend.app.models.crop import Crop
from backend.app.models.ingestion import IngestionLog
from backend.app.models.inquiry import Inquiry
from backend.app.models.mandi import Mandi
from backend.app.models.price import Price
from backend.app.models.user import User

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
)


@event.listens_for(test_engine.sync_engine, "connect")
def register_sqlite_geo_mocks(dbapi_connection: object, _connection_record: object) -> None:
    """Register mock ST functions so SQLite accepts PostGIS model inserts without errors."""
    if hasattr(dbapi_connection, "create_function"):
        dbapi_connection.create_function("GeomFromEWKT", 1, lambda val: val)
        dbapi_connection.create_function("ST_GeomFromEWKT", 1, lambda val: val)
        dbapi_connection.create_function("AsEWKB", 1, lambda val: val)
        dbapi_connection.create_function("ST_AsEWKB", 1, lambda val: val)


TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Creates tables and seeds test data."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        # Clean existing test data
        await session.execute(delete(Inquiry))
        await session.execute(delete(User))
        await session.execute(delete(Price))
        await session.execute(delete(Mandi))
        await session.execute(delete(Crop))
        await session.execute(delete(IngestionLog))
        await session.commit()

        # Seed Banana Crop
        crop = Crop(
            id="banana",
            name_en="Banana",
            name_te="అరటిపండు",
            name_hi="केला",
            name_gu="કેળા",
            icon="banana",
            category="fruit",
        )
        session.add(crop)

        # Seed Mandis
        mandi_guntur = Mandi(
            name="Guntur",
            district="Guntur",
            state="Andhra Pradesh",
            latitude=16.3067,
            longitude=80.4365,
        )
        mandi_vja = Mandi(
            name="Vijayawada",
            district="NTR",
            state="Andhra Pradesh",
            latitude=16.5062,
            longitude=80.6480,
        )
        mandi_mad = Mandi(
            name="Madanapalle",
            district="Annamayya",
            state="Andhra Pradesh",
            latitude=13.5500,
            longitude=78.5000,
        )
        session.add_all([mandi_guntur, mandi_vja, mandi_mad])
        await session.flush()

        # Seed Price records
        today = date.today()
        p1 = Price(
            mandi_id=mandi_guntur.id,
            crop_id="banana",
            variety="Amruthapani",
            grade="FAQ",
            price_date=today,
            min_price_quintal=2200.0,
            max_price_quintal=2800.0,
            modal_price_quintal=2500.0,
            min_price_kg=22.0,
            max_price_kg=28.0,
            modal_price_kg=25.0,
            modal_price_ton=25000.0,
            arrival_tonnes=45.0,
            source="data.gov.in",
        )
        p2 = Price(
            mandi_id=mandi_vja.id,
            crop_id="banana",
            variety="Karpura",
            grade="FAQ",
            price_date=today,
            min_price_quintal=2400.0,
            max_price_quintal=3000.0,
            modal_price_quintal=2700.0,
            min_price_kg=24.0,
            max_price_kg=30.0,
            modal_price_kg=27.0,
            modal_price_ton=27000.0,
            arrival_tonnes=60.0,
            source="data.gov.in",
        )
        p3 = Price(
            mandi_id=mandi_mad.id,
            crop_id="banana",
            variety="Robusta",
            grade="FAQ",
            price_date=today,
            min_price_quintal=1400.0,
            max_price_quintal=1800.0,
            modal_price_quintal=1600.0,
            min_price_kg=14.0,
            max_price_kg=18.0,
            modal_price_kg=16.0,
            modal_price_ton=16000.0,
            arrival_tonnes=80.0,
            source="data.gov.in",
        )
        session.add_all([p1, p2, p3])

        # Seed Ingestion Log
        log = IngestionLog(
            source="data.gov.in",
            records_fetched=3,
            records_upserted=3,
            records_failed=0,
            status="success",
        )
        session.add(log)
        await session.commit()

        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Test client overriding the get_async_db dependency."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_async_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
