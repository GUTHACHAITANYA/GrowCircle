"""
FastAPI route handlers for Mandi prices, nearby spatial search, and system health.
"""

import statistics
import time
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.db.session import get_async_db
from backend.app.models.crop import Crop
from backend.app.models.hierarchy import DistrictMaster, MandalMaster, StateMaster
from backend.app.models.ingestion import IngestionLog
from backend.app.models.mandi import Mandi
from backend.app.models.price import Price
from backend.app.models.user import User
from backend.app.schemas.price import (
    HealthResponse,
    HistoryPoint,
    HistoryResponse,
    NearbyMandiOut,
    PriceAggregateOut,
    PriceOut,
)
from backend.app.services.geo import GeoService, haversine_distance_km
from backend.app.services.pincode_service import PincodeService

router = APIRouter()


_AGGREGATES_CACHE: dict[str, tuple[float, PriceAggregateOut]] = {}
_CACHE_TTL_SECONDS = 300.0  # 5 minutes in-memory cache


@router.get("/prices", response_model=list[PriceOut], tags=["Prices"])
async def get_prices(
    crop: Annotated[str | None, Query(description="Crop slug identifier, e.g. 'banana' or 'all'")] = "banana",
    state: Annotated[
        str | None, Query(description="State name or code, e.g. 'andhra-pradesh' or 'AP'")
    ] = None,
    district: Annotated[str | None, Query(description="District name, e.g. 'guntur'")] = None,
    mandal: Annotated[str | None, Query(description="Mandal name, e.g. 'tenali'")] = None,
    mandi: Annotated[str | None, Query(description="Mandi name, canonical name, or numeric ID")] = None,
    variety: Annotated[str | None, Query(description="Crop variety, e.g. 'Robusta'")] = None,
    sort_by: Annotated[str, Query(description="Sort field: 'price', 'distance', 'name', 'date'")] = "price",
    sort_order: Annotated[str, Query(description="Sort order: 'asc' or 'desc'")] = "asc",
    user_lat: Annotated[float | None, Query(description="User latitude for distance sorting", ge=-90.0, le=90.0)] = None,
    user_lng: Annotated[float | None, Query(description="User longitude for distance sorting", ge=-180.0, le=180.0)] = None,
    page: Annotated[int, Query(description="Page number", ge=1)] = 1,
    limit: Annotated[int, Query(description="Page size limit", ge=1, le=100)] = 50,
    response: Response = None,
    db: AsyncSession = Depends(get_async_db),
) -> list[PriceOut]:
    """
    R4 Geographic Browsing for Prices:
    - Filters: State > District > Mandal > Mandi, plus Crop and Variety.
    - Honest fallback: If a mandal has no mandi, shows nearest reporting mandis.
    - Enriched records: Modal price/kg, min/max, arrivals, reported date/age, 30-day sparkline.
    - Sorting: by price, distance (if coordinates known), name, or date.
    - Pagination & caching.
    """
    now_date = datetime.now(IST).date()
    target_crop = crop.lower().strip() if (crop and crop.lower() != "all") else "banana"

    # 1. Honest Mandal Check: If a mandal is chosen, does it have an APMC mandi?
    mandal_has_mandi = True
    mandal_fallback = False
    mandal_status_msg = None

    if mandal and mandal.lower() != "all":
        mandal_query = mandal.replace("-", " ").strip()
        m_count_stmt = select(func.count(Mandi.id)).where(
            func.lower(Mandi.mandal) == mandal_query.lower(),
            Mandi.is_active.is_(True),
        )
        m_count = (await db.execute(m_count_stmt)).scalar() or 0

        if m_count == 0:
            # R4: If a mandal has no mandi, show the nearest reporting mandis and state that no mandi exists in the mandal
            mandal_has_mandi = False
            mandal_fallback = True
            mandal_status_msg = f"No mandi exists in {mandal_query} mandal. Showing nearest reporting mandis."

            # Find centroid of the mandal from MandalMaster or PincodeService
            mandal_obj = (
                await db.execute(
                    select(MandalMaster).where(func.lower(MandalMaster.name) == mandal_query.lower())
                )
            ).scalars().first()

            m_lat, m_lng = 16.3067, 80.4365
            if mandal_obj and mandal_obj.latitude and mandal_obj.longitude:
                m_lat, m_lng = mandal_obj.latitude, mandal_obj.longitude
            else:
                pin_info = PincodeService.lookup_pincode("522001")
                if pin_info:
                    m_lat, m_lng = pin_info["lat"], pin_info["lng"]

            nearby_items = await GeoService.get_nearby_mandis(
                db=db,
                user_lat=m_lat,
                user_lng=m_lng,
                crop_id=target_crop,
                limit=5,
                radius_km=100.0,
                max_age_days=3,
            )

            fallback_prices: list[PriceOut] = []
            for item in nearby_items:
                dist = item.get("distance_km", 0.0)
                status_msg = (
                    f"No mandi exists in {mandal_query} mandal. Showing nearest reporting mandi "
                    f"({dist:.1f} km away, straight-line distance)."
                )
                prov_text = f"Source: {item.get('source_name', 'Agmarknet')} | Reported: {item.get('price_date')} | Straight-line distance: {dist:.1f} km"
                p_date = datetime.strptime(item["price_date"], "%Y-%m-%d").date()

                fallback_prices.append(
                    PriceOut(
                        mandi_id=item["mandi_id"],
                        mandi_name=item["mandi_name"],
                        canonical_name=item.get("canonical_name"),
                        district=item["district"],
                        state=item["state"],
                        mandal=item.get("mandal"),
                        crop_id=target_crop,
                        crop_name_en=target_crop.capitalize(),
                        variety=item.get("variety", "Standard"),
                        grade="FAQ",
                        price_date=p_date,
                        reported_date=p_date,
                        age_label=item.get("age_label", "today"),
                        is_reported_today=item.get("age_days", 0) == 0,
                        min_price_kg=round(item["modal_price_kg"] * 0.9, 1),
                        max_price_kg=round(item["modal_price_kg"] * 1.1, 1),
                        modal_price_kg=item["modal_price_kg"],
                        min_price_quintal=round(item["modal_price_quintal"] * 0.9, 1),
                        max_price_quintal=round(item["modal_price_quintal"] * 1.1, 1),
                        modal_price_quintal=item["modal_price_quintal"],
                        modal_price_ton=item["modal_price_kg"] * 1000.0,
                        arrival_tonnes=item.get("arrival_tonnes", 0.0),
                        distance_km=dist,
                        distance_label="straight-line distance",
                        sparkline_30d=[item["modal_price_kg"]],
                        source=item.get("source_name", "Agmarknet"),
                        source_name=item.get("source_name", "Agmarknet"),
                        fetched_at=datetime.now(UTC),
                        last_updated=datetime.now(UTC),
                        is_stale=item.get("age_days", 0) > 1,
                        provenance_text=prov_text,
                        status_message=status_msg,
                    )
                )

            if response is not None:
                response.headers["X-Reporting-Mandis-Count"] = str(len(fallback_prices))
                response.headers["X-Area-Level"] = "mandal"
                response.headers["X-Area-Name"] = mandal_query
                response.headers["X-Mandal-Has-Mandi"] = "false"
                response.headers["X-Mandal-Fallback"] = "true"
                response.headers["X-Mandal-Status"] = mandal_status_msg
                response.headers["X-Aggregate-Note"] = mandal_status_msg

            return fallback_prices

    # 2. Build Base Query with Optional Hierarchy and Crop Filters
    stmt = (
        select(Price, Mandi, Crop)
        .join(Mandi, Price.mandi_id == Mandi.id)
        .join(Crop, Price.crop_id == Crop.id)
        .where(Price.anomaly_status.in_(["clean", "approved", "auto_cleared"]))
    )

    if crop and crop.lower() != "all":
        stmt = stmt.where(Price.crop_id == crop.lower().strip())

    if settings.APP_MODE == "production":
        stmt = stmt.where(Price.source != "demo")

    if state and state.lower() != "all":
        state_query = state.replace("-", " ").strip()
        stmt = stmt.where(
            or_(
                func.lower(Mandi.state) == state_query.lower(),
                func.lower(Mandi.state_id) == state_query.lower(),
            )
        )

    if district and district.lower() != "all":
        district_query = district.replace("-", " ").strip()
        stmt = stmt.where(func.lower(Mandi.district) == district_query.lower())

    if mandal and mandal.lower() != "all":
        mandal_query = mandal.replace("-", " ").strip()
        stmt = stmt.where(func.lower(Mandi.mandal) == mandal_query.lower())

    if mandi and mandi.lower() != "all":
        mandi_clean = mandi.strip()
        if mandi_clean.isdigit():
            stmt = stmt.where(Mandi.id == int(mandi_clean))
        else:
            mandi_q = mandi_clean.replace("-", " ").lower()
            stmt = stmt.where(
                or_(
                    func.lower(Mandi.name) == mandi_q,
                    func.lower(Mandi.canonical_name) == mandi_q,
                    Mandi.name.ilike(f"%{mandi_q}%"),
                )
            )

    if variety and variety.lower() != "all":
        stmt = stmt.where(func.lower(Price.variety) == variety.strip().lower())

    stmt = stmt.order_by(desc(Price.price_date), Mandi.name)
    result = await db.execute(stmt)
    rows = result.all()

    # Deduplicate rows so each (mandi_id, crop_id, variety) has its latest price record
    latest_rows_map: dict[tuple[int, str, str], tuple[Price, Mandi, Crop]] = {}
    for p_obj, m_obj, c_obj in rows:
        key = (m_obj.id, c_obj.id, p_obj.variety)
        if key not in latest_rows_map:
            latest_rows_map[key] = (p_obj, m_obj, c_obj)

    latest_rows = list(latest_rows_map.values())

    # 3. Batched 30-Day Sparkline Fetch across all displayed mandis
    mandi_ids = list({m.id for _, m, _ in latest_rows})
    sparklines: dict[int, list[float]] = {m_id: [] for m_id in mandi_ids}
    if mandi_ids:
        cutoff_30d = now_date - timedelta(days=30)
        sp_crop = crop.lower().strip() if (crop and crop.lower() != "all") else "banana"
        sp_stmt = (
            select(Price.mandi_id, Price.price_date, Price.modal_price_kg)
            .where(
                Price.mandi_id.in_(mandi_ids),
                Price.crop_id == sp_crop,
                Price.price_date >= cutoff_30d,
            )
        )
        if settings.APP_MODE == "production":
            sp_stmt = sp_stmt.where(Price.source != "demo")
        sp_stmt = sp_stmt.order_by(Price.mandi_id, Price.price_date.asc())
        sp_res = await db.execute(sp_stmt)
        for sp_mandi_id, _, sp_modal_kg in sp_res.all():
            sparklines[sp_mandi_id].append(float(sp_modal_kg))

    # 4. Construct PricesOut List
    prices_out: list[PriceOut] = []
    for price_obj, mandi_obj, crop_obj in latest_rows:
        age_days = (now_date - price_obj.price_date).days
        is_today = (age_days == 0)
        is_stale = (age_days > 1)

        if is_today:
            age_label = "today"
            status_msg = "Reported today"
        elif age_days == 1:
            age_label = "yesterday"
            status_msg = f"No price reported for this mandi today. Last reported: yesterday ({price_obj.price_date})"
        else:
            age_label = f"{age_days} days ago"
            status_msg = f"No price reported for this mandi today. Last reported: {price_obj.price_date} ({age_label})"

        if price_obj.source in ("data.gov.in", "agmarknet_portal_csv"):
            source_display = "Agmarknet / Directorate of Marketing & Inspection (DMI)"
        elif price_obj.source == "ceda_ashoka":
            source_display = "CEDA Agri Market Data (Ashoka University)"
        elif price_obj.source == "demo":
            source_display = "Demo data (synthetic preview)"
        else:
            source_display = price_obj.source

        fetch_time_str = (
            price_obj.fetched_at.strftime("%d %b %Y %H:%M UTC")
            if price_obj.fetched_at
            else "Unknown"
        )
        prov_text = f"Source: {source_display} | Reported: {price_obj.price_date} ({age_label}) | Fetched: {fetch_time_str}"

        # Distance calculation
        dist_km = None
        if user_lat is not None and user_lng is not None and mandi_obj.latitude and mandi_obj.longitude:
            dist_km = haversine_distance_km(user_lat, user_lng, mandi_obj.latitude, mandi_obj.longitude)

        sp_data = sparklines.get(mandi_obj.id, [])
        if not sp_data:
            sp_data = [price_obj.modal_price_kg]

        prices_out.append(
            PriceOut(
                mandi_id=mandi_obj.id,
                mandi_name=mandi_obj.name,
                canonical_name=mandi_obj.canonical_name,
                district=mandi_obj.district,
                state=mandi_obj.state,
                mandal=mandi_obj.mandal,
                crop_id=crop_obj.id,
                crop_name_en=crop_obj.name_en,
                variety=price_obj.variety,
                grade=price_obj.grade,
                price_date=price_obj.price_date,
                reported_date=price_obj.price_date,
                age_label=age_label,
                is_reported_today=is_today,
                min_price_kg=price_obj.min_price_kg,
                max_price_kg=price_obj.max_price_kg,
                modal_price_kg=price_obj.modal_price_kg,
                min_price_quintal=price_obj.min_price_quintal,
                max_price_quintal=price_obj.max_price_quintal,
                modal_price_quintal=price_obj.modal_price_quintal,
                modal_price_ton=price_obj.modal_price_ton,
                original_unit=getattr(price_obj, "original_unit", None) or "quintal",
                original_modal_price=(
                    getattr(price_obj, "original_modal_price", None)
                    if getattr(price_obj, "original_modal_price", None) is not None
                    else price_obj.modal_price_quintal
                ),
                arrival_tonnes=price_obj.arrival_tonnes,
                distance_km=dist_km,
                distance_label="straight-line distance",
                sparkline_30d=sp_data,
                source=price_obj.source,
                source_name=source_display,
                fetched_at=price_obj.fetched_at or price_obj.updated_at,
                last_updated=price_obj.updated_at,
                is_stale=is_stale,
                provenance_text=prov_text,
                status_message=status_msg,
            )
        )

    # 5. Sorting
    if sort_by == "price":
        prices_out.sort(key=lambda p: p.modal_price_kg, reverse=(sort_order == "desc"))
    elif sort_by == "distance":
        prices_out.sort(
            key=lambda p: (p.distance_km if p.distance_km is not None else 999999.0),
            reverse=(sort_order == "desc"),
        )
    elif sort_by == "name":
        prices_out.sort(key=lambda p: p.mandi_name.lower(), reverse=(sort_order == "desc"))
    elif sort_by == "date":
        prices_out.sort(key=lambda p: p.price_date, reverse=(sort_order != "asc"))

    # 6. Area Aggregates Calculation (R4 Rule 3)
    distinct_mandis = {p.mandi_id for p in prices_out}
    reporting_mandis_count = len(distinct_mandis)
    modal_prices = [p.modal_price_kg for p in prices_out]

    median_price = statistics.median(modal_prices) if modal_prices else None
    area_level = "mandal" if mandal else ("district" if district else ("state" if state else "all"))
    area_name = mandal or district or state or "All Mandis"

    if reporting_mandis_count == 0:
        agg_note = f"No mandis reported prices in {area_name} recently."
    elif reporting_mandis_count == 1:
        agg_note = (
            f"Only 1 mandi reported in {area_name} ({prices_out[0].mandi_name}: Rs. {prices_out[0].modal_price_kg:.1f}/kg). "
            f"Showing individual reported price instead of an area average."
        )
    elif reporting_mandis_count == 2:
        agg_note = f"Only 2 mandis reported in {area_name}. Showing individual reported prices instead of an area average."
    else:
        agg_note = f"{reporting_mandis_count} mandis reported in {area_name}. Area median modal price: Rs. {median_price:.1f}/kg."

    if response is not None:
        response.headers["X-Reporting-Mandis-Count"] = str(reporting_mandis_count)
        if median_price is not None:
            response.headers["X-Median-Price-Kg"] = f"{median_price:.2f}"
        response.headers["X-Aggregate-Note"] = agg_note
        response.headers["X-Area-Level"] = area_level
        response.headers["X-Area-Name"] = area_name
        response.headers["X-Mandal-Has-Mandi"] = "true"
        response.headers["X-Mandal-Fallback"] = "false"
        response.headers["X-Total-Count"] = str(len(prices_out))

    # 7. Pagination
    start_idx = (page - 1) * limit
    return prices_out[start_idx : start_idx + limit]


@router.get("/prices/aggregates", response_model=PriceAggregateOut, tags=["Prices"])
async def get_price_aggregates(
    crop: Annotated[str, Query(description="Crop slug identifier")] = "banana",
    state: Annotated[str | None, Query(description="State name or code")] = None,
    district: Annotated[str | None, Query(description="District name")] = None,
    mandal: Annotated[str | None, Query(description="Mandal name")] = None,
    mandi: Annotated[str | None, Query(description="Mandi name or ID")] = None,
    variety: Annotated[str | None, Query(description="Crop variety")] = None,
    db: AsyncSession = Depends(get_async_db),
) -> PriceAggregateOut:
    """
    R4 Area Aggregates:
    - Median modal price per kg & quintal
    - Number of reporting mandis
    - Integrity alert: If only 1 or 2 mandis reported, flags that it is NOT a broad area average.
    - Caches queries for 5 minutes.
    """
    cache_key = f"{state}:{district}:{mandal}:{mandi}:{crop}:{variety}".lower()
    now_ts = time.time()
    if cache_key in _AGGREGATES_CACHE:
        cached_ts, cached_out = _AGGREGATES_CACHE[cache_key]
        if now_ts - cached_ts < _CACHE_TTL_SECONDS:
            return cached_out

    # Check if mandal has any mandi
    mandal_has_mandi = True
    mandal_status_msg = None
    if mandal and mandal.lower() != "all":
        m_q = mandal.replace("-", " ").strip().lower()
        m_count = (
            await db.execute(
                select(func.count(Mandi.id)).where(func.lower(Mandi.mandal) == m_q, Mandi.is_active.is_(True))
            )
        ).scalar() or 0
        if m_count == 0:
            mandal_has_mandi = False
            mandal_status_msg = f"No mandi exists in {mandal} mandal. Showing nearest reporting mandis."

    # Query matching prices
    stmt = (
        select(Price, Mandi)
        .join(Mandi, Price.mandi_id == Mandi.id)
        .where(
            Price.crop_id == crop.lower().strip(),
            Price.anomaly_status.in_(["clean", "approved", "auto_cleared"]),
        )
    )

    if settings.APP_MODE == "production":
        stmt = stmt.where(Price.source != "demo")

    if state and state.lower() != "all":
        st_clean = state.replace("-", " ").strip().lower()
        stmt = stmt.where(or_(func.lower(Mandi.state) == st_clean, func.lower(Mandi.state_id) == st_clean))

    if district and district.lower() != "all":
        stmt = stmt.where(func.lower(Mandi.district) == district.replace("-", " ").strip().lower())

    if mandal and mandal.lower() != "all" and mandal_has_mandi:
        stmt = stmt.where(func.lower(Mandi.mandal) == mandal.replace("-", " ").strip().lower())

    if mandi and mandi.lower() != "all":
        m_clean = mandi.strip()
        if m_clean.isdigit():
            stmt = stmt.where(Mandi.id == int(m_clean))
        else:
            stmt = stmt.where(or_(func.lower(Mandi.name) == m_clean.lower(), func.lower(Mandi.canonical_name) == m_clean.lower()))

    if variety and variety.lower() != "all":
        stmt = stmt.where(func.lower(Price.variety) == variety.strip().lower())

    stmt = stmt.order_by(desc(Price.price_date))
    rows = (await db.execute(stmt)).all()

    # Deduplicate to latest price per mandi
    latest_by_mandi: dict[int, Price] = {}
    for p_obj, m_obj in rows:
        if m_obj.id not in latest_by_mandi:
            latest_by_mandi[m_obj.id] = p_obj

    prices_list = list(latest_by_mandi.values())
    reporting_count = len(prices_list)
    modal_kg_values = [p.modal_price_kg for p in prices_list]
    arrivals = [p.arrival_tonnes for p in prices_list]

    median_kg = round(float(statistics.median(modal_kg_values)), 1) if modal_kg_values else None
    median_quintal = round(median_kg * 100.0, 1) if median_kg is not None else None
    min_kg = round(float(min(modal_kg_values)), 1) if modal_kg_values else None
    max_kg = round(float(max(modal_kg_values)), 1) if modal_kg_values else None
    avg_arr = round(float(sum(arrivals) / len(arrivals)), 1) if arrivals else 0.0

    area_level = "mandal" if mandal else ("district" if district else ("state" if state else "all"))
    area_name = mandal or district or state or "All Regions"
    is_reliable = reporting_count >= 3

    if reporting_count == 0:
        note = f"No mandis reported prices in {area_name} recently."
    elif reporting_count == 1:
        note = (
            f"Only 1 mandi reported in {area_name} (₹{median_kg}/kg). "
            f"Showing individual reported price instead of an area average."
        )
    elif reporting_count == 2:
        note = f"Only 2 mandis reported in {area_name}. Showing individual reported prices instead of an area average."
    else:
        note = f"{reporting_count} mandis reported in {area_name}. Area median modal price: ₹{median_kg}/kg."

    result = PriceAggregateOut(
        state=state,
        district=district,
        mandal=mandal,
        mandi=mandi,
        crop=crop,
        variety=variety,
        reporting_mandis_count=reporting_count,
        total_records=len(rows),
        median_modal_price_kg=median_kg,
        median_modal_price_quintal=median_quintal,
        min_modal_price_kg=min_kg,
        max_modal_price_kg=max_kg,
        avg_arrival_tonnes=avg_arr,
        is_area_average_reliable=is_reliable,
        area_level=area_level,
        area_name=area_name,
        note=note,
        mandal_has_mandi=mandal_has_mandi,
        mandal_status_message=mandal_status_msg,
    )

    _AGGREGATES_CACHE[cache_key] = (now_ts, result)
    return result


@router.get("/nearby-mandis", response_model=list[NearbyMandiOut], tags=["Geospatial"])
async def get_nearby_mandis(
    lat: Annotated[float, Query(description="User GPS Latitude (WGS84)", ge=-90.0, le=90.0)],
    lng: Annotated[float, Query(description="User GPS Longitude (WGS84)", ge=-180.0, le=180.0)],
    crop: Annotated[str, Query(description="Crop slug identifier")] = "banana",
    limit: Annotated[int, Query(description="Number of nearby mandis to return", ge=1, le=10)] = 5,
    radius_km: Annotated[float | None, Query(description="Maximum search radius in km")] = None,
    max_age_days: Annotated[int, Query(description="Maximum price age in days", ge=1, le=30)] = 3,
    response: Response = None,
    db: AsyncSession = Depends(get_async_db),
) -> list[NearbyMandiOut]:
    """
    Computes distance using PostGIS ST_Distance (or Haversine fallback) to find the nearest mandis
    with recent prices for the requested crop within radius_km (default 100km).
    Only returns mandis with prices reported within max_age_days (default 3 days).
    Labels distance as straight-line distance.
    """
    raw_nearby = await GeoService.get_nearby_mandis(
        db=db,
        user_lat=lat,
        user_lng=lng,
        crop_id=crop.lower().strip(),
        limit=limit,
        radius_km=radius_km,
        max_age_days=max_age_days,
    )

    output: list[NearbyMandiOut] = []

    for item in raw_nearby:
        output.append(
            NearbyMandiOut(
                mandi_id=item["mandi_id"],
                mandi_name=item["mandi_name"],
                canonical_name=item.get("canonical_name"),
                district=item["district"],
                state=item["state"],
                mandal=item.get("mandal"),
                latitude=item["latitude"],
                longitude=item["longitude"],
                distance_km=item["distance_km"],
                distance_label=item.get("distance_label", "straight-line distance"),
                crop_id=item["crop_id"],
                variety=item["variety"],
                modal_price_kg=item["modal_price_kg"],
                modal_price_quintal=item["modal_price_quintal"],
                price_date=item["price_date"],
                age_days=item.get("age_days", 0),
                age_label=item.get("age_label", "Today"),
                arrival_tonnes=item["arrival_tonnes"],
                is_stale=item.get("is_stale", False),
                source_name=item.get("source_name", "Agmarknet"),
            )
        )

    if response is not None:
        response.headers["X-Distance-Type"] = "straight-line distance"
        response.headers["X-Reported-Count"] = str(len(output))
        response.headers["X-Radius-Km"] = str(radius_km if radius_km is not None else "unlimited")

    return output


@router.get("/pincode-lookup", tags=["Geospatial"])
async def pincode_lookup(
    pincode: Annotated[str, Query(description="6-digit Indian Postal PIN code", min_length=6, max_length=6)],
) -> dict[str, Any]:
    """
    Looks up geographic coordinates and administrative boundaries for an Indian pincode.
    Used for non-blocking location fallback when GPS is denied or unavailable.
    """
    res = PincodeService.lookup(pincode)
    if not res:
        raise HTTPException(status_code=404, detail=f"PIN code '{pincode}' not found or unrecognized")
    return res


@router.get("/hierarchy/states", tags=["Hierarchy"])
async def get_hierarchy_states(db: AsyncSession = Depends(get_async_db)) -> list[dict[str, Any]]:
    """Lists states in the LGD hierarchy master, falling back to distinct states from Mandi table."""
    result = await db.execute(select(StateMaster).order_by(StateMaster.name))
    states = result.scalars().all()
    if states:
        return [{"id": s.id, "name": s.name, "lgd_code": s.lgd_code} for s in states]

    m_states = (await db.execute(select(func.distinct(Mandi.state)).order_by(Mandi.state))).scalars().all()
    return [{"id": s[:2].upper(), "name": s, "lgd_code": None} for s in m_states if s]


@router.get("/hierarchy/districts", tags=["Hierarchy"])
async def get_hierarchy_districts(
    state_id: Annotated[str | None, Query(description="State ID code, e.g. AP")] = None,
    state_code: Annotated[str | None, Query(description="State code alias, e.g. AP")] = None,
    state: Annotated[str | None, Query(description="State name, e.g. 'Andhra Pradesh'")] = None,
    db: AsyncSession = Depends(get_async_db),
) -> list[dict[str, Any]]:
    """Lists districts for the selected state."""
    target_state = state_id or state_code or state
    stmt = select(DistrictMaster).order_by(DistrictMaster.name)

    if target_state and target_state.lower() != "all":
        st_clean = target_state.replace("-", " ").strip()
        st_obj = (
            await db.execute(
                select(StateMaster).where(
                    or_(
                        func.lower(StateMaster.id) == st_clean.lower(),
                        func.lower(StateMaster.name) == st_clean.lower(),
                    )
                )
            )
        ).scalars().first()

        if st_obj:
            stmt = stmt.where(DistrictMaster.state_id == st_obj.id)
        else:
            stmt = stmt.where(
                or_(
                    DistrictMaster.state_id.ilike(f"%{st_clean[:2]}%"),
                    DistrictMaster.name.ilike(f"%{st_clean}%"),
                )
            )

    districts = (await db.execute(stmt)).scalars().all()
    if districts:
        return [
            {"id": d.id, "name": d.name, "lgd_code": d.lgd_code, "state_id": d.state_id}
            for d in districts
        ]

    # Fallback to distinct districts from Mandi table
    d_stmt = select(func.distinct(Mandi.district)).order_by(Mandi.district)
    if target_state and target_state.lower() != "all":
        d_stmt = d_stmt.where(
            or_(
                Mandi.state.ilike(f"%{st_clean}%"),
                Mandi.state_id.ilike(f"%{st_clean[:2]}%"),
            )
        )
    m_districts = (await db.execute(d_stmt)).scalars().all()
    return [
        {"id": idx + 1, "name": d, "lgd_code": None, "state_id": target_state or "AP"}
        for idx, d in enumerate(m_districts)
        if d
    ]


@router.get("/hierarchy/mandals", tags=["Hierarchy"])
async def get_hierarchy_mandals(
    district_id: Annotated[int | None, Query(description="District unique ID")] = None,
    district: Annotated[str | None, Query(description="District name, e.g. 'Guntur'")] = None,
    db: AsyncSession = Depends(get_async_db),
) -> list[dict[str, Any]]:
    """Lists sub-districts/mandals with centroid coordinates for nearest mandi search."""
    stmt = select(MandalMaster).order_by(MandalMaster.name)
    if district_id is not None:
        stmt = stmt.where(MandalMaster.district_id == district_id)
    elif district and district.lower() != "all":
        d_clean = district.replace("-", " ").strip()
        d_obj = (
            await db.execute(
                select(DistrictMaster).where(func.lower(DistrictMaster.name) == d_clean.lower())
            )
        ).scalars().first()
        if d_obj:
            stmt = stmt.where(MandalMaster.district_id == d_obj.id)

    mandals = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": m.id,
            "name": m.name,
            "lgd_code": m.lgd_code,
            "district_id": m.district_id,
            "latitude": m.latitude,
            "longitude": m.longitude,
        }
        for m in mandals
    ]


@router.get("/hierarchy/mandis", tags=["Hierarchy"])
async def get_hierarchy_mandis(
    state: Annotated[str | None, Query(description="State name or code")] = None,
    district: Annotated[str | None, Query(description="District name")] = None,
    mandal: Annotated[str | None, Query(description="Mandal name")] = None,
    db: AsyncSession = Depends(get_async_db),
) -> list[dict[str, Any]]:
    """Lists mandis dynamically filtered by optional State, District, and Mandal."""
    stmt = select(Mandi).where(Mandi.is_active.is_(True)).order_by(Mandi.name)

    if state and state.lower() != "all":
        st_clean = state.replace("-", " ").strip().lower()
        stmt = stmt.where(or_(func.lower(Mandi.state) == st_clean, func.lower(Mandi.state_id) == st_clean))

    if district and district.lower() != "all":
        stmt = stmt.where(func.lower(Mandi.district) == district.replace("-", " ").strip().lower())

    if mandal and mandal.lower() != "all":
        stmt = stmt.where(func.lower(Mandi.mandal) == mandal.replace("-", " ").strip().lower())

    mandis = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": m.id,
            "name": m.name,
            "canonical_name": m.canonical_name,
            "district": m.district,
            "mandal": m.mandal,
            "state": m.state,
            "latitude": m.latitude,
            "longitude": m.longitude,
            "location_verified": m.location_verified,
        }
        for m in mandis
    ]


@router.get("/crops", tags=["Commodities"])
async def get_crops(db: AsyncSession = Depends(get_async_db)) -> list[dict[str, Any]]:
    """Returns available agricultural commodities with multilingual titles."""
    result = await db.execute(select(Crop).order_by(Crop.name_en))
    crops = result.scalars().all()
    return [
        {
            "id": c.id,
            "name_en": c.name_en,
            "name_te": c.name_te,
            "name_hi": c.name_hi,
            "name_gu": c.name_gu,
            "icon": c.icon,
            "category": c.category,
        }
        for c in crops
    ]


@router.get("/varieties", tags=["Commodities"])
async def get_varieties(
    crop: Annotated[str, Query(description="Crop slug identifier, e.g. 'banana'")] = "banana",
    db: AsyncSession = Depends(get_async_db),
) -> list[str]:
    """Returns distinct reported crop varieties from real price data."""
    stmt = (
        select(func.distinct(Price.variety))
        .where(Price.crop_id == crop.lower().strip())
        .order_by(Price.variety)
    )
    result = await db.execute(stmt)
    varieties = result.scalars().all()
    clean = [v for v in varieties if v and v.strip()]
    return clean or ["Standard / FAQ"]


@router.get("/user/preferences", tags=["User"])
async def get_user_preferences(
    phone: Annotated[str | None, Query(description="User phone number")] = None,
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Returns saved geographic browsing filters for logged-in user profile."""
    if not phone:
        return {"state": "Andhra Pradesh", "district": "Guntur", "crop": "banana"}

    clean_p = phone.strip().replace(" ", "").replace("+", "")
    user = (await db.execute(select(User).where(User.phone == clean_p))).scalars().first()
    if not user:
        return {"state": "Andhra Pradesh", "district": "Guntur", "crop": "banana"}

    return {
        "state": "Andhra Pradesh",
        "district": user.district.capitalize() if user.district else "Guntur",
        "crop": "banana",
        "language": user.language or "te",
    }


@router.post("/user/preferences", tags=["User"])
async def save_user_preferences(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Updates saved geographic browsing filters for logged-in user profile."""
    phone = payload.get("phone")
    if phone:
        clean_p = str(phone).strip().replace(" ", "").replace("+", "")
        user = (await db.execute(select(User).where(User.phone == clean_p))).scalars().first()
        if user:
            if "district" in payload and payload["district"]:
                user.district = str(payload["district"]).lower()
            if "language" in payload and payload["language"]:
                user.language = str(payload["language"]).lower()
            await db.commit()
    return {"status": "saved", "preferences": payload}



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

    cutoff_date = datetime.now(IST).date() - timedelta(days=days)

    stmt = (
        select(Price)
        .where(
            Price.mandi_id == mandi_id,
            Price.crop_id == crop.lower().strip(),
            Price.price_date >= cutoff_date,
        )
    )

    if settings.APP_MODE == "production":
        stmt = stmt.where(Price.source != "demo")

    stmt = stmt.order_by(Price.price_date.asc())

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

    reporting_drop_alert = False
    reporting_mandis_count: int | None = None

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
            now_date = datetime.now(IST).date()
            if (now_date - latest_date).days > 1:
                is_stale_alert = True
                alert_msg = f"Data staleness alert: Latest Banana price is from {latest_date} (> 24 hours old)"

            # Check reporting drop status
            from ml.anomaly.reporting_drops import reporting_drop_detector

            active_mandis = (
                await db.scalar(
                    select(func.count(func.distinct(Price.mandi_id))).where(
                        Price.price_date == latest_date
                    )
                )
            ) or 0
            reporting_mandis_count = active_mandis
            rpt_res = reporting_drop_detector.evaluate_reporting(latest_date, active_mandis)
            reporting_drop_alert = rpt_res.is_outage_alert
            if reporting_drop_alert and not alert_msg:
                alert_msg = rpt_res.alert_message
        else:
            is_stale_alert = True
            alert_msg = "No price data recorded yet in database."

    except Exception as ex:
        db_status = f"unhealthy: {ex}"
        is_stale_alert = True
        alert_msg = "Database connection error"

    is_degraded = is_stale_alert or reporting_drop_alert or db_status != "connected"

    return HealthResponse(
        status="healthy" if not is_degraded else "degraded",
        service="growcircle-engine",
        version="0.1.0",
        database=db_status,
        last_successful_fetch_time=last_fetch_str,
        is_stale_alert=is_stale_alert,
        alert_message=alert_msg,
        reporting_drop_alert=reporting_drop_alert,
        reporting_mandis_count=reporting_mandis_count,
    )
