"""
FastAPI route handlers for Mandi prices, nearby spatial search, and system health.
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_db
from backend.app.models.crop import Crop
from backend.app.models.ingestion import IngestionLog
from backend.app.models.mandi import Mandi
from backend.app.models.price import Price
from backend.app.schemas.price import (
    HealthResponse,
    HistoryPoint,
    HistoryResponse,
    NearbyMandiOut,
    PriceOut,
)
from backend.app.services.geo import GeoService

router = APIRouter()


@router.get("/prices", response_model=list[PriceOut], tags=["Prices"])
async def get_prices(
    crop: Annotated[str, Query(description="Crop slug identifier, e.g. 'banana'")] = "banana",
    state: Annotated[
        str | None, Query(description="State name, e.g. 'andhra-pradesh' or 'Andhra Pradesh'")
    ] = None,
    district: Annotated[str | None, Query(description="District name, e.g. 'guntur'")] = None,
    db: AsyncSession = Depends(get_async_db),
) -> list[PriceOut]:
    """
    Returns latest prices for the given crop, filtered optionally by state and district.
    Never invents data: always returns actual dates and last_updated timestamps.
    """
    stmt = (
        select(Price, Mandi, Crop)
        .join(Mandi, Price.mandi_id == Mandi.id)
        .join(Crop, Price.crop_id == Crop.id)
        .where(Price.crop_id == crop.lower().strip())
    )

    if state:
        # Match case-insensitively, handling hyphenated slugs like 'andhra-pradesh'
        state_query = state.replace("-", " ").strip()
        stmt = stmt.where(func.lower(Mandi.state) == state_query.lower())

    if district:
        district_query = district.replace("-", " ").strip()
        stmt = stmt.where(func.lower(Mandi.district) == district_query.lower())

    stmt = stmt.order_by(desc(Price.price_date), Mandi.name)
    result = await db.execute(stmt)
    rows = result.all()

    now_date = datetime.now(UTC).date()
    prices_out: list[PriceOut] = []

    for price_obj, mandi_obj, crop_obj in rows:
        is_stale = (now_date - price_obj.price_date).days > 1
        prices_out.append(
            PriceOut(
                mandi_id=mandi_obj.id,
                mandi_name=mandi_obj.name,
                district=mandi_obj.district,
                state=mandi_obj.state,
                crop_id=crop_obj.id,
                crop_name_en=crop_obj.name_en,
                variety=price_obj.variety,
                grade=price_obj.grade,
                price_date=price_obj.price_date,
                min_price_kg=price_obj.min_price_kg,
                max_price_kg=price_obj.max_price_kg,
                modal_price_kg=price_obj.modal_price_kg,
                min_price_quintal=price_obj.min_price_quintal,
                max_price_quintal=price_obj.max_price_quintal,
                modal_price_quintal=price_obj.modal_price_quintal,
                modal_price_ton=price_obj.modal_price_ton,
                arrival_tonnes=price_obj.arrival_tonnes,
                source=price_obj.source,
                last_updated=price_obj.updated_at,
                is_stale=is_stale,
            )
        )

    return prices_out


@router.get("/nearby-mandis", response_model=list[NearbyMandiOut], tags=["Geospatial"])
async def get_nearby_mandis(
    lat: Annotated[float, Query(description="User GPS Latitude (WGS84)", ge=-90.0, le=90.0)],
    lng: Annotated[float, Query(description="User GPS Longitude (WGS84)", ge=-180.0, le=180.0)],
    crop: Annotated[str, Query(description="Crop slug identifier")] = "banana",
    limit: Annotated[int, Query(description="Number of nearby mandis to return", ge=1, le=10)] = 3,
    db: AsyncSession = Depends(get_async_db),
) -> list[NearbyMandiOut]:
    """
    Computes geodesic distance using PostGIS ST_Distance to find the nearest mandis
    with recent prices for the requested crop.
    """
    raw_nearby = await GeoService.get_nearby_mandis(
        db=db,
        user_lat=lat,
        user_lng=lng,
        crop_id=crop.lower().strip(),
        limit=limit,
    )

    now_date = datetime.now(UTC).date()
    output: list[NearbyMandiOut] = []

    for item in raw_nearby:
        item_date = datetime.strptime(item["price_date"], "%Y-%m-%d").date()
        is_stale = (now_date - item_date).days > 1
        output.append(
            NearbyMandiOut(
                mandi_id=item["mandi_id"],
                mandi_name=item["mandi_name"],
                district=item["district"],
                state=item["state"],
                latitude=item["latitude"],
                longitude=item["longitude"],
                distance_km=item["distance_km"],
                crop_id=item["crop_id"],
                variety=item["variety"],
                modal_price_kg=item["modal_price_kg"],
                modal_price_quintal=item["modal_price_quintal"],
                price_date=item["price_date"],
                arrival_tonnes=item["arrival_tonnes"],
                is_stale=is_stale,
            )
        )

    return output


@router.get("/history", response_model=HistoryResponse, tags=["Analytics"])
async def get_price_history(
    mandi_id: Annotated[int, Query(description="Mandi unique ID")],
    crop: Annotated[str, Query(description="Crop identifier")] = "banana",
    days: Annotated[int, Query(description="Number of historical days", ge=1, le=90)] = 30,
    db: AsyncSession = Depends(get_async_db),
) -> HistoryResponse:
    """
    Returns daily historical modal prices for trend charts and forecasts.
    """
    mandi = await db.scalar(select(Mandi).where(Mandi.id == mandi_id))
    if not mandi:
        raise HTTPException(status_code=404, detail="Mandi not found")

    cutoff_date = datetime.now(UTC).date() - timedelta(days=days)

    stmt = (
        select(Price)
        .where(
            Price.mandi_id == mandi_id,
            Price.crop_id == crop.lower().strip(),
            Price.price_date >= cutoff_date,
        )
        .order_by(Price.price_date.asc())
    )

    result = await db.execute(stmt)
    prices = result.scalars().all()

    points = [
        HistoryPoint(
            date=p.price_date.isoformat(),
            modal_price_kg=p.modal_price_kg,
            modal_price_quintal=p.modal_price_quintal,
            arrival_tonnes=p.arrival_tonnes,
        )
        for p in prices
    ]

    return HistoryResponse(
        mandi_id=mandi.id,
        mandi_name=mandi.name,
        crop_id=crop,
        days=days,
        history=points,
    )


@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check(
    db: AsyncSession = Depends(get_async_db),
) -> HealthResponse:
    """
    Health check verifying database connectivity, latest Agmarknet fetch timestamp,
    and alerting when data is older than 24 hours.
    """
    db_status = "connected"
    last_fetch_str = None
    is_stale_alert = False
    alert_msg = None

    try:
        # Check latest ingestion log
        log = await db.scalar(
            select(IngestionLog).order_by(desc(IngestionLog.fetch_timestamp)).limit(1)
        )
        if log:
            last_fetch_str = log.fetch_timestamp.isoformat()
            if log.status == "failure":
                is_stale_alert = True
                alert_msg = f"Last fetch failed: {log.error_message}"

        # Check latest price date in DB
        latest_date = await db.scalar(
            select(func.max(Price.price_date)).where(Price.crop_id == "banana")
        )
        if latest_date:
            now_date = datetime.now(UTC).date()
            if (now_date - latest_date).days > 1:
                is_stale_alert = True
                alert_msg = f"Data staleness alert: Latest Banana price is from {latest_date} (> 24 hours old)"
        else:
            is_stale_alert = True
            alert_msg = "No price data recorded yet in database."

    except Exception as ex:
        db_status = f"unhealthy: {ex}"
        is_stale_alert = True
        alert_msg = "Database connection error"

    return HealthResponse(
        status="healthy" if not is_stale_alert and db_status == "connected" else "degraded",
        service="growcircle-engine",
        version="0.1.0",
        database=db_status,
        last_successful_fetch_time=last_fetch_str,
        is_stale_alert=is_stale_alert,
        alert_message=alert_msg,
    )
