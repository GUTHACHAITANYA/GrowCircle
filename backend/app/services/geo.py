"""
Geospatial and PostGIS distance query service.
Finds the nearest mandis to a user location with active recent crop prices.
"""

from datetime import UTC, datetime, timedelta
import math
from typing import Any
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

from geoalchemy2.functions import ST_Distance, ST_MakePoint, ST_SetSRID
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.mandi import Mandi
from backend.app.models.price import Price


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great circle distance between two points in km."""
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)


class GeoService:
    @staticmethod
    async def get_nearby_mandis(
        db: AsyncSession,
        user_lat: float,
        user_lng: float,
        crop_id: str = "banana",
        limit: int = 5,
        radius_km: float | None = None,
        max_age_days: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Queries the database for mandis nearest to (user_lat, user_lng)
        that have price records for `crop_id`, sorted by physical distance.
        Enforces:
        - Only verified mandis (location_verified=True).
        - Prices within max_age_days (default 3 days).
        - Maximum search radius_km if provided.
        - Labels distance as straight-line distance.
        """
        now_date = datetime.now(IST).date()
        cutoff_date = now_date - timedelta(days=max_age_days)

        # User geometry point: SRID 4326 (lng, lat)
        user_point = ST_SetSRID(ST_MakePoint(user_lng, user_lat), 4326)

        # Distance calculation in meters (converted to km) using PostGIS geography ST_Distance
        distance_meters_expr = ST_Distance(Mandi.location, user_point, True)

        try:
            # Query joined with Price for the given crop within max_age_days
            stmt = (
                select(
                    Mandi,
                    Price,
                    (distance_meters_expr / 1000.0).label("distance_km"),
                )
                .join(Price, Price.mandi_id == Mandi.id)
                .where(
                    Price.crop_id == crop_id.lower().strip(),
                    Price.price_date >= cutoff_date,
                    Mandi.is_active == True,
                    Mandi.location_verified == True,
                    Mandi.latitude.is_not(None),
                    Mandi.longitude.is_not(None),
                    Mandi.location.is_not(None),
                )
                .order_by("distance_km", desc(Price.price_date))
                .limit(limit * 4)  # retrieve candidates to deduplicate by mandi
            )

            result = await db.execute(stmt)
            rows = result.all()

            seen_mandis = set()
            nearby_list = []

            for mandi_obj, price_obj, dist_km in rows:
                if mandi_obj.id in seen_mandis:
                    continue
                seen_mandis.add(mandi_obj.id)

                dist_val = round(float(dist_km), 1) if dist_km is not None else 0.0
                if radius_km is not None and dist_val > radius_km:
                    continue

                age_days = (now_date - price_obj.price_date).days
                if age_days <= 0:
                    age_label = "Today"
                elif age_days == 1:
                    age_label = "Yesterday"
                else:
                    age_label = f"{age_days} days ago"

                nearby_list.append(
                    {
                        "mandi_id": mandi_obj.id,
                        "mandi_name": mandi_obj.name,
                        "canonical_name": mandi_obj.canonical_name or mandi_obj.name,
                        "district": mandi_obj.district,
                        "state": mandi_obj.state,
                        "mandal": mandi_obj.mandal,
                        "latitude": mandi_obj.latitude,
                        "longitude": mandi_obj.longitude,
                        "distance_km": dist_val,
                        "distance_label": "straight-line distance",
                        "crop_id": price_obj.crop_id,
                        "variety": price_obj.variety,
                        "modal_price_kg": price_obj.modal_price_kg,
                        "modal_price_quintal": price_obj.modal_price_quintal,
                        "price_date": price_obj.price_date.isoformat(),
                        "age_days": max(0, age_days),
                        "age_label": age_label,
                        "arrival_tonnes": price_obj.arrival_tonnes,
                        "is_stale": age_days > 1,
                        "source_name": price_obj.source or "Agmarknet",
                    }
                )

                if len(nearby_list) >= limit:
                    break

            return nearby_list

        except Exception:
            # Python Haversine fallback if PostGIS extension is not available in mock/sqlite test
            stmt_fallback = (
                select(Mandi, Price)
                .join(Price, Price.mandi_id == Mandi.id)
                .where(
                    Price.crop_id == crop_id.lower().strip(),
                    Price.price_date >= cutoff_date,
                    Mandi.is_active == True,
                    Mandi.location_verified == True,
                    Mandi.latitude.is_not(None),
                    Mandi.longitude.is_not(None),
                )
                .order_by(desc(Price.price_date))
            )
            result = await db.execute(stmt_fallback)
            rows = result.all()

            candidates = []
            seen_mandis = set()

            for mandi_obj, price_obj in rows:
                if mandi_obj.id in seen_mandis:
                    continue
                seen_mandis.add(mandi_obj.id)

                if mandi_obj.latitude is not None and mandi_obj.longitude is not None:
                    d = haversine_distance_km(
                        user_lat, user_lng, mandi_obj.latitude, mandi_obj.longitude
                    )
                else:
                    d = 9999.0

                if radius_km is not None and d > radius_km:
                    continue

                age_days = (now_date - price_obj.price_date).days
                if age_days <= 0:
                    age_label = "Today"
                elif age_days == 1:
                    age_label = "Yesterday"
                else:
                    age_label = f"{age_days} days ago"

                candidates.append(
                    {
                        "mandi_id": mandi_obj.id,
                        "mandi_name": mandi_obj.name,
                        "canonical_name": mandi_obj.canonical_name or mandi_obj.name,
                        "district": mandi_obj.district,
                        "state": mandi_obj.state,
                        "mandal": mandi_obj.mandal,
                        "latitude": mandi_obj.latitude,
                        "longitude": mandi_obj.longitude,
                        "distance_km": d,
                        "distance_label": "straight-line distance",
                        "crop_id": price_obj.crop_id,
                        "variety": price_obj.variety,
                        "modal_price_kg": price_obj.modal_price_kg,
                        "modal_price_quintal": price_obj.modal_price_quintal,
                        "price_date": price_obj.price_date.isoformat(),
                        "age_days": max(0, age_days),
                        "age_label": age_label,
                        "arrival_tonnes": price_obj.arrival_tonnes,
                        "arrivals_tonnes": price_obj.arrival_tonnes,
                        "is_stale": age_days > 1,
                        "source_name": price_obj.source or "Agmarknet",
                    }
                )

            candidates.sort(key=lambda x: x["distance_km"])
            return candidates[:limit]
