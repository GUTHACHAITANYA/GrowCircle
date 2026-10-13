"""
Geospatial and PostGIS distance query service.
Finds the nearest mandis to a user location with active recent crop prices.
"""

import math
from typing import Any

from geoalchemy2.functions import ST_Distance, ST_MakePoint, ST_SetSRID
from sqlalchemy import select
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
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Queries the database for mandis nearest to (user_lat, user_lng)
        that have price records for `crop_id`, sorted by physical distance.
        """
        # User geometry point: SRID 4326 (lng, lat)
        user_point = ST_SetSRID(ST_MakePoint(user_lng, user_lat), 4326)

        # Distance calculation in meters (converted to km) using PostGIS geography ST_Distance
        distance_meters_expr = ST_Distance(Mandi.location, user_point, True)

        try:
            # Query joined with Price for the given crop
            stmt = (
                select(
                    Mandi,
                    Price,
                    (distance_meters_expr / 1000.0).label("distance_km"),
                )
                .join(Price, Price.mandi_id == Mandi.id)
                .where(
                    Price.crop_id == crop_id,
                    Mandi.location.is_not(None),
                )
                .order_by("distance_km")
                .limit(limit * 2)  # retrieve candidates to deduplicate by mandi
            )

            result = await db.execute(stmt)
            rows = result.all()

            seen_mandis = set()
            nearby_list = []

            for mandi_obj, price_obj, dist_km in rows:
                if mandi_obj.id in seen_mandis:
                    continue
                seen_mandis.add(mandi_obj.id)

                nearby_list.append(
                    {
                        "mandi_id": mandi_obj.id,
                        "mandi_name": mandi_obj.name,
                        "district": mandi_obj.district,
                        "state": mandi_obj.state,
                        "latitude": mandi_obj.latitude,
                        "longitude": mandi_obj.longitude,
                        "distance_km": round(float(dist_km), 1) if dist_km is not None else None,
                        "crop_id": price_obj.crop_id,
                        "variety": price_obj.variety,
                        "modal_price_kg": price_obj.modal_price_kg,
                        "modal_price_quintal": price_obj.modal_price_quintal,
                        "price_date": price_obj.price_date.isoformat(),
                        "arrival_tonnes": price_obj.arrival_tonnes,
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
                .where(Price.crop_id == crop_id)
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

                candidates.append(
                    {
                        "mandi_id": mandi_obj.id,
                        "mandi_name": mandi_obj.name,
                        "district": mandi_obj.district,
                        "state": mandi_obj.state,
                        "latitude": mandi_obj.latitude,
                        "longitude": mandi_obj.longitude,
                        "distance_km": d,
                        "crop_id": price_obj.crop_id,
                        "variety": price_obj.variety,
                        "modal_price_kg": price_obj.modal_price_kg,
                        "modal_price_quintal": price_obj.modal_price_quintal,
                        "price_date": price_obj.price_date.isoformat(),
                        "arrival_tonnes": price_obj.arrival_tonnes,
                    }
                )

            candidates.sort(key=lambda x: x["distance_km"])
            return candidates[:limit]
