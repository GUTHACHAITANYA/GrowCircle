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
from backend.app.models.anomaly import AnomalyReview
from backend.app.models.audit_log import AuditLog
from backend.app.models.buyer import BuyerProfile
from backend.app.models.buyer_need import BuyerNeed
from backend.app.models.crop import Crop
from backend.app.models.deal import Deal
from backend.app.models.farm_diary import FarmDiaryEntry, FarmSeason
from backend.app.models.feedback import Feedback
from backend.app.models.ground_truth import GroundTruthCheck
from backend.app.models.hierarchy import DistrictMaster, MandalMaster, StateMaster
from backend.app.models.ingestion import IngestionLog
from backend.app.models.inquiry import Inquiry
from backend.app.models.language import Language
from backend.app.models.listing import Listing
from backend.app.models.mandi import Mandi
from backend.app.models.offer import Offer
from backend.app.models.price import Price
from backend.app.models.price_alert import PriceAlert
from backend.app.models.rating import Rating
from backend.app.models.transporter import Transporter
from backend.app.models.trip import Trip
from backend.app.models.trip_rating import TripRating
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
        # Clean existing test data in reverse foreign-key dependency order
        await session.execute(delete(Feedback))
        await session.execute(delete(GroundTruthCheck))
        await session.execute(delete(AnomalyReview))
        await session.execute(delete(AuditLog))
        await session.execute(delete(PriceAlert))
        await session.execute(delete(FarmDiaryEntry))
        await session.execute(delete(FarmSeason))
        await session.execute(delete(TripRating))
        await session.execute(delete(Trip))
        await session.execute(delete(Transporter))
        await session.execute(delete(Rating))
        await session.execute(delete(Deal))
        await session.execute(delete(Offer))
        await session.execute(delete(Listing))
        await session.execute(delete(BuyerNeed))
        await session.execute(delete(BuyerProfile))
        await session.execute(delete(Inquiry))
        await session.execute(delete(Language))
        await session.execute(delete(User))
        await session.execute(delete(Price))
        await session.execute(delete(Mandi))
        await session.execute(delete(MandalMaster))
        await session.execute(delete(DistrictMaster))
        await session.execute(delete(StateMaster))
        await session.execute(delete(Crop))
        await session.execute(delete(IngestionLog))
        await session.commit()

        # Seed Crops (Banana, Tomato, Onion, Chilli)
        crop_banana = Crop(
            id="banana",
            name_en="Banana",
            name_te="అరటిపండు",
            name_hi="केला",
            name_gu="કેળા",
            icon="banana",
            category="fruit",
        )
        crop_tomato = Crop(
            id="tomato",
            name_en="Tomato",
            name_te="టమాటా",
            name_hi="टमाटर",
            name_gu="ટામેટા",
            icon="tomato",
            category="vegetable",
        )
        crop_onion = Crop(
            id="onion",
            name_en="Onion",
            name_te="ఉల్లిపాయ",
            name_hi="प्याज",
            name_gu="ડુંગળી",
            icon="onion",
            category="vegetable",
        )
        crop_chilli = Crop(
            id="chilli",
            name_en="Green Chilli",
            name_te="పచ్చిమిర్చి",
            name_hi="हरी मिर्च",
            name_gu="લીલા મરચા",
            icon="chilli",
            category="vegetable",
        )
        session.add_all([crop_banana, crop_tomato, crop_onion, crop_chilli])

        # Seed Mandis
        mandi_guntur = Mandi(
            name="Guntur",
            canonical_name="Guntur",
            district="Guntur",
            state="Andhra Pradesh",
            latitude=16.3067,
            longitude=80.4365,
            location_verified=True,
            geocode_confidence=1.0,
            geocode_source="verified_seed",
        )
        mandi_vja = Mandi(
            name="Vijayawada",
            canonical_name="Vijayawada",
            district="NTR",
            state="Andhra Pradesh",
            latitude=16.5062,
            longitude=80.6480,
            location_verified=True,
            geocode_confidence=1.0,
            geocode_source="verified_seed",
        )
        mandi_mad = Mandi(
            name="Madanapalle",
            canonical_name="Madanapalle",
            district="Annamayya",
            state="Andhra Pradesh",
            latitude=13.5500,
            longitude=78.5000,
            location_verified=True,
            geocode_confidence=1.0,
            geocode_source="verified_seed",
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


@pytest_asyncio.fixture(scope="function")
async def admin_headers(db_session: AsyncSession) -> dict[str, str]:
    """Generates an authenticated 2FA-verified Admin Bearer authorization header."""
    from backend.app.models.user import User
    from backend.app.services.security import create_access_token

    admin = User(
        phone="9999900099",
        name="Admin Test",
        role="admin",
        language="en",
        is_admin_2fa_verified=True,
    )
    db_session.add(admin)
    await db_session.flush()
    token = create_access_token(admin.id, admin.phone, "admin", is_admin_2fa=True)
    return {"Authorization": f"Bearer {token}"}
