"""
Crop Planning & Crash Risk Guidance API Endpoint (Phase ML-3).
Exposes GET /crop-plan?district=..&month=..&farmer_id=..
Ranks candidate crops by expected profit per acre and downside risk ranges.
Incorporates farmer diary data when available and ANGRAU/KVK agronomic suitability.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.config import settings
from backend.app.db.session import get_async_db
from backend.app.models.farm_diary import FarmSeason
from backend.app.models.user import User
from backend.app.schemas.crop_plan import CropPlanResponseSchema
from backend.app.services.security import get_optional_current_user
from ml.planning.planner_engine import CropPlanningEngine

logger = logging.getLogger(__name__)

router = APIRouter()

# Global engine instance
_crop_planning_engine: CropPlanningEngine | None = None


def get_planner_engine() -> CropPlanningEngine:
    global _crop_planning_engine
    if _crop_planning_engine is None:
        _crop_planning_engine = CropPlanningEngine()
    return _crop_planning_engine


@router.get("/crop-plan", response_model=CropPlanResponseSchema, tags=["Crop Planning"])
async def get_crop_plan(
    district: str = Query("Guntur", description="District name, e.g. 'Guntur', 'Annamayya', 'Kurnool', 'Krishna'"),
    month: int = Query(..., ge=1, le=12, description="Target planting month (1=Jan, 12=Dec)"),
    farmer_id: int | None = Query(None, description="Optional registered farmer ID to blend personal historical diary logs"),
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """
    Returns 3 to 5 agronomically suitable crops for a district and planting month,
    ranked by expected net profit per acre with explicit downside risk scenarios.

    Always shows cost/yield/price ranges (never single numbers), Cobweb crowding risk score,
    and official ANGRAU/KVK agronomic suitability references.
    """
    engine = get_planner_engine()

    # 1. Check for farmer diary historical records
    farmer_diary_summary: dict[str, dict[str, float]] | None = None
    if farmer_id is not None:
        if settings.ENVIRONMENT in ("production", "staging"):
            if not current_user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required to blend personal farm diary records.",
                )
            if current_user.id != farmer_id and current_user.role != "admin":
                raise HTTPException(
                    status_code=403,
                    detail="Unauthorized: Cannot access another farmer's diary records.",
                )
        else:
            if current_user and current_user.id != farmer_id and current_user.role != "admin":
                raise HTTPException(
                    status_code=403,
                    detail="Unauthorized: Cannot access another farmer's diary records.",
                )

        try:
            stmt = (
                select(FarmSeason)
                .where(FarmSeason.farmer_id == farmer_id)
                .options(selectinload(FarmSeason.entries))
            )
            result = await db.execute(stmt)
            seasons = result.scalars().all()

            if seasons:
                crop_costs: dict[str, list[float]] = {}
                crop_yields: dict[str, list[float]] = {}

                for s in seasons:
                    area = max(s.area_acres, 0.1)
                    cost_sum = sum(e.amount_inr for e in s.entries if e.entry_type == "cost")
                    yield_kg_sum = sum(e.quantity_kg for e in s.entries if e.entry_type == "yield_log")

                    if cost_sum > 0:
                        crop_costs.setdefault(s.crop_id, []).append(cost_sum / area)

                    effective_kg = yield_kg_sum if yield_kg_sum > 0 else s.expected_yield_kg
                    if effective_kg > 0:
                        crop_yields.setdefault(s.crop_id, []).append((effective_kg / 1000.0) / area)

                diary_summary: dict[str, dict[str, float]] = {}
                all_crops = set(crop_costs.keys()) | set(crop_yields.keys())
                for c in all_crops:
                    entry: dict[str, float] = {}
                    if c in crop_costs and crop_costs[c]:
                        entry["cost_per_acre"] = round(sum(crop_costs[c]) / len(crop_costs[c]), 2)
                    if c in crop_yields and crop_yields[c]:
                        entry["yield_tonnes_acre"] = round(sum(crop_yields[c]) / len(crop_yields[c]), 2)
                    if entry:
                        diary_summary[c] = entry

                if diary_summary:
                    farmer_diary_summary = diary_summary
        except Exception as exc:
            logger.warning("Failed to extract farmer diary summary for farmer_id=%s: %s", farmer_id, exc)

    try:
        plan_res = engine.generate_plan(
            district=district,
            planting_month=month,
            farmer_diary_summary=farmer_diary_summary,
            farmer_id=farmer_id,
        )
        return plan_res.to_dict()
    except Exception as exc:
        logger.error("Error generating crop plan for district=%s, month=%s: %s", district, month, exc)
        raise HTTPException(
            status_code=500,
            detail=f"Unable to generate crop plan for {district} in month {month}: {str(exc)}",
        ) from exc
