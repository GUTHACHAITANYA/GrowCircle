"""
Transport Matching, Vehicle Classification, Guide Rate, and Pooling v1 Service.
Phase 4: Transport.
"""

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.transporter import Transporter
from backend.app.services.matching import haversine_distance_km

VEHICLE_CONFIGS = {
    "goods_auto": {
        "label": "Goods Auto (<500 kg)",
        "models": "Piaggio Ape / Bajaj Maxima / Mahindra Alfa",
        "min_weight_kg": 0.0,
        "max_weight_kg": 500.0,
        "base_rate": 150.0,
        "rate_per_km": 18.0,
    },
    "mini_truck": {
        "label": "Mini-Truck (500 kg - 1.5 t)",
        "models": "Tata Ace / Mahindra Bolero Maxx Pik-up",
        "min_weight_kg": 500.0,
        "max_weight_kg": 1500.0,
        "base_rate": 350.0,
        "rate_per_km": 25.0,
    },
    "large_truck": {
        "label": "Larger Truck (>1.5 t)",
        "models": "Ashok Leyland Dost / Tata 407 / Eicher Pro",
        "min_weight_kg": 1500.0,
        "max_weight_kg": 10000.0,
        "base_rate": 700.0,
        "rate_per_km": 38.0,
    },
}

GUIDE_RATE_DISCLAIMER = (
    "Guide rate only (indicative estimate based on regional distance and vehicle type). "
    "Transporter and farmer/buyer agree directly on final freight charges."
)


def classify_vehicle_for_weight(weight_kg: float) -> str:
    """
    Classifies the required vehicle type for a given load weight:
    - under 500 kg -> 'goods_auto'
    - 500 kg to 1.5 t (1500 kg) -> 'mini_truck'
    - above 1.5 t -> 'large_truck'
    """
    if weight_kg < 500.0:
        return "goods_auto"
    elif weight_kg <= 1500.0:
        return "mini_truck"
    else:
        return "large_truck"


def calculate_guide_rate(distance_km: float, vehicle_type: str) -> float:
    """
    Calculates the indicative guide rate:
    base_fare + (distance_km * rate_per_km)
    """
    config = VEHICLE_CONFIGS.get(vehicle_type, VEHICLE_CONFIGS["mini_truck"])
    base = config["base_rate"]
    rate_km = config["rate_per_km"]

    # Minimum 2 km billable distance
    effective_dist = max(distance_km, 2.0)
    total_rate = base + (effective_dist * rate_km)
    return round(total_rate, 2)


async def suggest_drivers_for_deal(
    db: AsyncSession,
    pickup_lat: float,
    pickup_lng: float,
    dropoff_lat: float,
    dropoff_lng: float,
    load_weight_kg: float,
    limit: int = 3,
    check_date: date | None = None,
) -> dict[str, Any]:
    """
    Suggests 3 available, verified drivers near the pickup point matched to the load.
    Enforces automatic expiry checks (hides drivers with any expired document).
    """
    ref_date = check_date or date.today()
    matched_vehicle_type = classify_vehicle_for_weight(load_weight_kg)
    trip_distance_km = haversine_distance_km(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)
    guide_fare = calculate_guide_rate(trip_distance_km, matched_vehicle_type)

    # Query verified & available transporters matching the vehicle type
    stmt = (
        select(Transporter)
        .where(
            Transporter.vehicle_type == matched_vehicle_type,
            Transporter.capacity_kg >= load_weight_kg,
            Transporter.is_verified.is_(True),
            Transporter.available_today.is_(True),
            # Automatic document expiry checks: all 4 must be valid on check_date
            Transporter.license_expiry >= ref_date,
            Transporter.rc_expiry >= ref_date,
            Transporter.insurance_expiry >= ref_date,
            Transporter.fitness_expiry >= ref_date,
        )
    )
    result = await db.execute(stmt)
    drivers = result.scalars().all()

    # Score and rank drivers by proximity to pickup point and reliability
    ranked_drivers: list[dict[str, Any]] = []
    for d in drivers:
        dist_to_pickup = haversine_distance_km(
            d.current_latitude, d.current_longitude, pickup_lat, pickup_lng
        )
        ranked_drivers.append(
            {
                "transporter_id": d.id,
                "name": d.name,
                "phone": d.phone,
                "vehicle_type": d.vehicle_type,
                "vehicle_model": d.vehicle_model,
                "capacity_kg": d.capacity_kg,
                "distance_to_pickup_km": round(dist_to_pickup, 1),
                "reliability_rating": round(d.reliability_rating, 1),
                "trips_completed": d.trips_completed,
            }
        )

    # Sort by nearest to pickup, breaking ties with reliability rating
    ranked_drivers.sort(key=lambda x: (x["distance_to_pickup_km"], -x["reliability_rating"]))
    top_suggestions = ranked_drivers[:limit]

    return {
        "load_weight_kg": load_weight_kg,
        "matched_vehicle_type": matched_vehicle_type,
        "vehicle_description": VEHICLE_CONFIGS[matched_vehicle_type]["label"],
        "trip_distance_km": round(trip_distance_km, 1),
        "guide_rate": guide_fare,
        "rate_label": "Guide Rate (Indicative)",
        "disclaimer": GUIDE_RATE_DISCLAIMER,
        "suggested_drivers": top_suggestions,
        "total_available_compliant_drivers": len(ranked_drivers),
    }


def plan_pooled_trips_v1(
    deals_data: list[dict[str, Any]],
    max_pickup_cluster_km: float = 15.0,
) -> list[dict[str, Any]]:
    """
    Pooling v1 (rule-based):
    Groups nearby loads going to the same buyer/institution into one trip.

    deals_data format:
    [
      {
        "deal_id": 1,
        "buyer_id": 10,
        "farmer_name": "Ramesh",
        "quantity_kg": 400.0,
        "pickup_lat": 16.24,
        "pickup_lng": 80.64,
        "pickup_address": "Tenali Farm 1",
        "dropoff_lat": 16.30,
        "dropoff_lng": 80.43,
        "dropoff_address": "ANU Hostel Mess",
      }, ...
    ]
    """
    if not deals_data:
        return []

    # 1. Group deals by destination buyer / coordinates (within 5 km)
    buyer_groups: dict[int, list[dict[str, Any]]] = {}
    for deal in deals_data:
        b_id = deal.get("buyer_id", 0)
        buyer_groups.setdefault(b_id, []).append(deal)

    pooled_plans: list[dict[str, Any]] = []

    for _buyer_id, deals in buyer_groups.items():
        if len(deals) < 2:
            # Single deal, not poolable
            d = deals[0]
            dist = haversine_distance_km(
                d["pickup_lat"], d["pickup_lng"], d["dropoff_lat"], d["dropoff_lng"]
            )
            v_type = classify_vehicle_for_weight(d["quantity_kg"])
            fare = calculate_guide_rate(dist, v_type)
            pooled_plans.append(
                {
                    "is_pooled": False,
                    "deal_ids": [d["deal_id"]],
                    "total_weight_kg": d["quantity_kg"],
                    "vehicle_type": v_type,
                    "pickup_stops": [
                        {
                            "deal_id": d["deal_id"],
                            "farmer_name": d.get("farmer_name", "Farmer"),
                            "latitude": d["pickup_lat"],
                            "longitude": d["pickup_lng"],
                            "quantity_kg": d["quantity_kg"],
                        }
                    ],
                    "dropoff_address": d.get("dropoff_address", "Institution"),
                    "total_distance_km": round(dist, 1),
                    "combined_guide_rate": fare,
                    "individual_fares_sum": fare,
                    "estimated_savings": 0.0,
                }
            )
            continue

        # Check pickup proximity among deals
        # Anchor on the first deal
        anchor = deals[0]
        cluster: list[dict[str, Any]] = [anchor]
        unclustered: list[dict[str, Any]] = []

        for d in deals[1:]:
            dist_to_anchor = haversine_distance_km(
                anchor["pickup_lat"], anchor["pickup_lng"], d["pickup_lat"], d["pickup_lng"]
            )
            if dist_to_anchor <= max_pickup_cluster_km:
                cluster.append(d)
            else:
                unclustered.append(d)

        # Build pooled trip for the cluster
        total_cluster_weight = sum(item["quantity_kg"] for item in cluster)
        pooled_vehicle_type = classify_vehicle_for_weight(total_cluster_weight)

        # Approximate combined route: pickup stops sequentially, then to dropoff
        # Stop 1 -> Stop 2 ... -> Dropoff
        route_dist = 0.0
        for i in range(len(cluster) - 1):
            route_dist += haversine_distance_km(
                cluster[i]["pickup_lat"],
                cluster[i]["pickup_lng"],
                cluster[i + 1]["pickup_lat"],
                cluster[i + 1]["pickup_lng"],
            )
        # Last pickup to dropoff
        route_dist += haversine_distance_km(
            cluster[-1]["pickup_lat"],
            cluster[-1]["pickup_lng"],
            cluster[0]["dropoff_lat"],
            cluster[0]["dropoff_lng"],
        )

        pooled_fare = calculate_guide_rate(route_dist, pooled_vehicle_type)

        # Sum of individual fares if shipped separately
        individual_fares_sum = sum(
            calculate_guide_rate(
                haversine_distance_km(
                    x["pickup_lat"], x["pickup_lng"], x["dropoff_lat"], x["dropoff_lng"]
                ),
                classify_vehicle_for_weight(x["quantity_kg"]),
            )
            for x in cluster
        )

        savings = max(0.0, round(individual_fares_sum - pooled_fare, 2))

        pooled_plans.append(
            {
                "is_pooled": True,
                "deal_ids": [item["deal_id"] for item in cluster],
                "total_weight_kg": total_cluster_weight,
                "vehicle_type": pooled_vehicle_type,
                "pickup_stops": [
                    {
                        "deal_id": item["deal_id"],
                        "farmer_name": item.get("farmer_name", "Farmer"),
                        "latitude": item["pickup_lat"],
                        "longitude": item["pickup_lng"],
                        "quantity_kg": item["quantity_kg"],
                    }
                    for item in cluster
                ],
                "dropoff_address": cluster[0].get("dropoff_address", "Institution"),
                "total_distance_km": round(route_dist, 1),
                "combined_guide_rate": pooled_fare,
                "individual_fares_sum": round(individual_fares_sum, 2),
                "estimated_savings": savings,
            }
        )

        # Process any unclustered deals
        for un in unclustered:
            dist = haversine_distance_km(
                un["pickup_lat"], un["pickup_lng"], un["dropoff_lat"], un["dropoff_lng"]
            )
            v_type = classify_vehicle_for_weight(un["quantity_kg"])
            fare = calculate_guide_rate(dist, v_type)
            pooled_plans.append(
                {
                    "is_pooled": False,
                    "deal_ids": [un["deal_id"]],
                    "total_weight_kg": un["quantity_kg"],
                    "vehicle_type": v_type,
                    "pickup_stops": [
                        {
                            "deal_id": un["deal_id"],
                            "farmer_name": un.get("farmer_name", "Farmer"),
                            "latitude": un["pickup_lat"],
                            "longitude": un["pickup_lng"],
                            "quantity_kg": un["quantity_kg"],
                        }
                    ],
                    "dropoff_address": un.get("dropoff_address", "Institution"),
                    "total_distance_km": round(dist, 1),
                    "combined_guide_rate": fare,
                    "individual_fares_sum": fare,
                    "estimated_savings": 0.0,
                }
            )

    return pooled_plans
