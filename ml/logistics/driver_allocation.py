"""
Driver Matching and Fair Allocation Engine.
Phase ML-5: Smarter Matching and Logistics.

Ranks available, verified drivers by:
1. Distance / Proximity to pickup location
2. Capacity fit (avoids extreme vehicle mismatch)
3. Driver rating (1.0 to 5.0)
4. Reliability (on-time delivery percentage)
5. Fair distribution leveling penalty (prevents trip monopolization and driver fatigue)
"""

from __future__ import annotations

import dataclasses
import logging
import math
from typing import Any

from backend.app.services.geo import haversine_distance_km

logger = logging.getLogger(__name__)

EQUITY_DECAY_SCALE = 6.0  # Tau parameter: recent trips dampening scale


@dataclasses.dataclass
class DriverProfile:
    """Driver and vehicle profile for matching."""

    driver_id: str | int
    name: str
    phone: str
    vehicle_type: str
    vehicle_model: str
    capacity_kg: float
    current_latitude: float
    current_longitude: float
    reliability_rating: float  # 1.0 to 5.0
    on_time_rate: float  # 0.0 to 1.0
    trips_completed_total: int
    recent_trips_count: int  # trips completed in the last 7 days
    is_verified: bool = True
    is_available: bool = True


class DriverMatchingEngine:
    """
    Ranks drivers with multi-attribute scoring and anti-monopoly fair distribution.
    """

    @classmethod
    def rank_drivers(
        cls,
        drivers: list[DriverProfile],
        pickup_lat: float,
        pickup_lng: float,
        load_weight_kg: float,
        apply_fairness_leveling: bool = True,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Filters and scores available compliant drivers.
        Returns top ranked drivers with full scoring explanations.
        """
        qualified: list[dict[str, Any]] = []

        for d in drivers:
            if not d.is_verified or not d.is_available:
                continue
            if d.capacity_kg < load_weight_kg:
                # Cannot physically transport the load
                continue

            dist_km = haversine_distance_km(
                d.current_latitude, d.current_longitude, pickup_lat, pickup_lng
            )
            # Max search radius 60 km
            if dist_km > 60.0:
                continue

            # 1. Proximity score (0.0 to 1.0)
            proximity_score = max(0.0, 1.0 - (dist_km / 60.0))

            # 2. Capacity fit score (1.0 for snug fit; slight penalty if grossly oversized)
            excess_ratio = (d.capacity_kg - load_weight_kg) / d.capacity_kg
            capacity_fit_score = max(0.5, 1.0 - (0.35 * excess_ratio))

            # 3. Rating score (0.0 to 1.0)
            rating_score = min(1.0, max(0.0, d.reliability_rating / 5.0))

            # 4. Reliability score (0.0 to 1.0)
            reliability_score = min(1.0, max(0.0, d.on_time_rate))

            # Base qualification composite score
            base_score = (
                0.35 * proximity_score
                + 0.25 * capacity_fit_score
                + 0.20 * rating_score
                + 0.20 * reliability_score
            )

            # 5. Anti-monopoly equity & fatigue multiplier
            if apply_fairness_leveling:
                # Exponential decay based on recent trip count
                fatigue_dampener = math.exp(-d.recent_trips_count / EQUITY_DECAY_SCALE)
                # Blended: 50% guaranteed floor + 50% scaled by fairness
                equity_multiplier = 0.50 + (0.50 * fatigue_dampener)
            else:
                fatigue_dampener = 1.0
                equity_multiplier = 1.0

            final_score = base_score * equity_multiplier

            qualified.append({
                "driver_id": d.driver_id,
                "name": d.name,
                "phone": d.phone,
                "vehicle_type": d.vehicle_type,
                "vehicle_model": d.vehicle_model,
                "capacity_kg": d.capacity_kg,
                "distance_to_pickup_km": round(dist_km, 1),
                "reliability_rating": round(d.reliability_rating, 2),
                "on_time_rate": round(d.on_time_rate, 2),
                "recent_trips_count": d.recent_trips_count,
                "total_trips": d.trips_completed_total,
                "base_score": round(base_score, 4),
                "equity_multiplier": round(equity_multiplier, 4),
                "final_score": round(final_score, 4),
                "leveling_applied": apply_fairness_leveling,
            })

        # Rank descending by final score
        qualified.sort(key=lambda x: x["final_score"], reverse=True)
        return qualified[:limit]

    @classmethod
    def calculate_gini_coefficient(cls, trip_counts: list[int]) -> float:
        """
        Calculates Gini coefficient of trip distribution across drivers.
        0.0 = perfect equality; 1.0 = total monopoly.
        """
        if not trip_counts or sum(trip_counts) == 0:
            return 0.0
        sorted_counts = sorted(trip_counts)
        n = len(sorted_counts)
        cum_sum = sum((i + 1) * count for i, count in enumerate(sorted_counts))
        total = sum(sorted_counts)
        gini = (2 * cum_sum) / (n * total) - (n + 1) / n
        return round(float(max(0.0, gini)), 3)
