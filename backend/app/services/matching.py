"""
Rule-Based Matching Engine for Direct Selling.
1. Matches farmer listings with nearby verified buyers (distance, quantity, grade, reliability).
2. Matches institutional buyer needs with nearby active farmer listings within 50 km.
3. Solves the 'Group Supply' problem: aggregates multiple smaller farmer supplies
   to fulfill large bulk institutional requirements (e.g. college hostels, hospitals).
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.buyer import BuyerProfile
from backend.app.models.buyer_need import BuyerNeed
from backend.app.models.listing import Listing
from backend.app.services.geo import haversine_distance_km


class MatchingService:
    """
    Transparent rule-based matching engine prior to ML ranking models.
    """

    @classmethod
    async def match_buyers_for_listing(
        cls,
        db: AsyncSession,
        listing: Listing,
        max_distance_km: float = 50.0,
    ) -> list[dict[str, Any]]:
        """
        Ranks verified nearby buyers interested in the listed crop.
        """
        # Fetch verified buyers
        stmt = (
            select(BuyerProfile)
            .where(BuyerProfile.verification_status == "verified")
        )
        result = await db.execute(stmt)
        buyers = result.scalars().all()

        # Batch-fetch all active needs for this crop in 1 query to prevent N+1 database roundtrips
        buyer_ids = [b.id for b in buyers]
        needs_by_buyer: dict[int, BuyerNeed] = {}
        if buyer_ids:
            needs_stmt = select(BuyerNeed).where(
                BuyerNeed.buyer_id.in_(buyer_ids),
                BuyerNeed.crop_id == listing.crop_id,
                BuyerNeed.status == "active",
            )
            needs_res = await db.execute(needs_stmt)
            for need_obj in needs_res.scalars().all():
                if need_obj.buyer_id not in needs_by_buyer:
                    needs_by_buyer[need_obj.buyer_id] = need_obj

        matches = []
        for buyer in buyers:
            dist = haversine_distance_km(
                listing.latitude, listing.longitude, buyer.latitude, buyer.longitude
            )
            if dist > max_distance_km:
                continue

            # Look up pre-fetched active need without issuing individual SQL queries
            need = needs_by_buyer.get(buyer.id)


            # 1. Distance score (weight: 0.40)
            dist_score = max(0.0, 1.0 - (dist / max_distance_km))

            # 2. Quantity score (weight: 0.25)
            if need and need.quantity_kg > 0:
                q_ratio = min(listing.quantity_kg, need.quantity_kg) / max(
                    listing.quantity_kg, need.quantity_kg
                )
            else:
                q_ratio = 0.6  # Buyer general interest
            qty_score = q_ratio

            # 3. Grade score (weight: 0.15)
            if need:
                if need.preferred_grade == "any" or need.preferred_grade == listing.grade:
                    grade_score = 1.0
                else:
                    grade_score = 0.5
            else:
                grade_score = 0.8

            # 4. Reliability score (weight: 0.20)
            rel_score = min(5.0, buyer.reliability_score) / 5.0

            composite_score = round(
                (0.40 * dist_score)
                + (0.25 * qty_score)
                + (0.15 * grade_score)
                + (0.20 * rel_score),
                3,
            )

            matches.append(
                {
                    "buyer_id": buyer.id,
                    "business_name": buyer.business_name,
                    "business_type": buyer.business_type,
                    "district": buyer.district,
                    "distance_km": dist,
                    "reliability_score": buyer.reliability_score,
                    "has_active_need": need is not None,
                    "need_quantity_kg": need.quantity_kg if need else None,
                    "match_score": composite_score,
                }
            )

        matches.sort(key=lambda x: x["match_score"], reverse=True)
        return matches

    @classmethod
    async def match_farmers_for_buyer_need(
        cls,
        db: AsyncSession,
        need: BuyerNeed,
        max_distance_km: float = 50.0,
    ) -> list[dict[str, Any]]:
        """
        Ranks individual active farmer listings within 50 km matching buyer requirements.
        """
        stmt = (
            select(Listing)
            .where(
                Listing.crop_id == need.crop_id,
                Listing.status == "active",
            )
        )
        result = await db.execute(stmt)
        listings = result.scalars().all()

        matched_listings = []
        for listing_obj in listings:
            dist = haversine_distance_km(
                need.latitude, need.longitude, listing_obj.latitude, listing_obj.longitude
            )
            if dist > max_distance_km:
                continue

            # Scoring
            dist_score = max(0.0, 1.0 - (dist / max_distance_km))
            qty_score = min(listing_obj.quantity_kg, need.quantity_kg) / max(
                listing_obj.quantity_kg, need.quantity_kg
            )
            grade_score = 1.0 if need.preferred_grade in ["any", listing_obj.grade] else 0.5
            farmer_rel = 5.0  # default baseline farmer reliability
            rel_score = farmer_rel / 5.0

            score = round(
                (0.40 * dist_score) + (0.25 * qty_score) + (0.15 * grade_score) + (0.20 * rel_score),
                3,
            )

            matched_listings.append(
                {
                    "listing_id": listing_obj.id,
                    "farmer_id": listing_obj.farmer_id,
                    "variety": listing_obj.variety,
                    "quantity_kg": listing_obj.quantity_kg,
                    "grade": listing_obj.grade,
                    "expected_price_kg": listing_obj.expected_price_kg,
                    "harvest_date": listing_obj.harvest_date.isoformat(),
                    "district": listing_obj.district,
                    "distance_km": dist,
                    "match_score": score,
                    "media_checklist": listing_obj.media_checklist,
                }
            )

        matched_listings.sort(key=lambda x: x["match_score"], reverse=True)
        return matched_listings

    @classmethod
    async def aggregate_group_supply(
        cls,
        db: AsyncSession,
        need: BuyerNeed,
        max_distance_km: float = 50.0,
    ) -> dict[str, Any]:
        """
        Groups supply from multiple neighboring farmers within 50 km
        to satisfy bulk institutional demand.
        """
        candidates = await cls.match_farmers_for_buyer_need(
            db=db, need=need, max_distance_km=max_distance_km
        )

        bundled_listings = []
        accumulated_qty = 0.0
        total_cost = 0.0

        for cand in candidates:
            needed_remaining = need.quantity_kg - accumulated_qty
            if needed_remaining <= 0:
                break

            allocated_qty = min(cand["quantity_kg"], needed_remaining)
            bundled_listings.append(
                {
                    **cand,
                    "allocated_quantity_kg": allocated_qty,
                }
            )
            accumulated_qty += allocated_qty
            total_cost += allocated_qty * cand["expected_price_kg"]

        avg_price = (
            round(total_cost / accumulated_qty, 2) if accumulated_qty > 0 else 0.0
        )

        return {
            "need_id": need.id,
            "crop_id": need.crop_id,
            "target_quantity_kg": need.quantity_kg,
            "bundled_quantity_kg": accumulated_qty,
            "is_fully_fulfilled": accumulated_qty >= need.quantity_kg,
            "farmers_count": len(bundled_listings),
            "weighted_average_price_kg": avg_price,
            "bundled_listings": bundled_listings,
        }
