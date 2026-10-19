"""
FastAPI Router for ML-5: Smarter Matching and Logistics.

Endpoints:
- POST /logistics/rank-listings: Buyer-farmer ranking with LambdaRank/Rule A/B gating and smallholder audit
- POST /logistics/rate-guide: Fair transport rate guide with confidence intervals
- POST /logistics/pool-routes: Google OR-Tools multi-stop VRP pooling with spoilage and savings report
- POST /logistics/rank-drivers: Driver matching with anti-monopoly fair distribution
- GET  /logistics/data-sufficiency: Honest statistical data threshold documentation
- GET  /logistics/audit-logs: Structured decision audit trail
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

from backend.app.schemas.logistics_ml import (
    DriverMatchRequest,
    DriverMatchResponse,
    PoolingRequest,
    PoolingResponse,
    RankedCandidateResult,
    RankingCandidateItem,
    RankingRequest,
    RankingResponse,
    RateGuideRequest,
    RateGuideResponse,
)
from backend.app.services.security import require_admin_role_enforced
from ml.logistics.driver_allocation import DriverMatchingEngine, DriverProfile
from ml.logistics.ranking_engine import (
    DataSufficiencyChecker,
    FairnessAuditor,
    LightGBMLambdaRanker,
    MatchingABGating,
    RankingCandidate,
    RuleBasedRanker,
    get_matching_audit_logs,
    record_ranking_audit_log,
)
from ml.logistics.rate_guide import transport_rate_model
from ml.logistics.vrp_pooling import ORToolsVRPSolver

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logistics", tags=["Smart Logistics & Matching"])

# Globally initialized ranker instance
_lambda_ranker = LightGBMLambdaRanker()

# Mock historical session count in early rollout (can be queried from DB in full deployment)
_CURRENT_HISTORICAL_SESSIONS = 340  # Under the 1,200 threshold, documenting honest fallback


def _to_candidate_domain(item: RankingCandidateItem) -> RankingCandidate:
    """Converts Pydantic request item to domain dataclass."""
    feedback = item.implicit_feedback or {
        "views": 1,
        "accepts": 0,
        "completes": 0,
        "on_time": 0,
        "complaints": 0,
    }
    return RankingCandidate(
        candidate_id=item.candidate_id,
        farmer_name=item.farmer_name,
        crop=item.crop,
        distance_km=item.distance_km,
        quantity_kg=item.quantity_kg,
        requested_qty_kg=item.requested_qty_kg,
        farmer_grade=item.farmer_grade,
        buyer_grade_req=item.buyer_grade_req,
        price_per_kg=item.price_per_kg,
        mandi_modal_price=item.mandi_modal_price,
        completion_rate=item.completion_rate,
        response_time_hours=item.response_time_hours,
        rating=item.rating,
        is_smallholder=item.is_smallholder,
        implicit_feedback=feedback,
    )


@router.post("/rank-listings", response_model=RankingResponse)
async def rank_listings(req: RankingRequest) -> RankingResponse:
    """
    Ranks farmer listings for a buyer request.
    Uses A/B testing gating between Rule-based and LambdaRank models.
    Enforces Four-Fifths smallholder parity audit and decision logging.
    """
    candidates = [_to_candidate_domain(c) for c in req.candidates]
    sufficiency = DataSufficiencyChecker.check_sufficiency(_CURRENT_HISTORICAL_SESSIONS)

    variant = MatchingABGating.determine_variant(
        query_id=req.query_id,
        total_sessions=_CURRENT_HISTORICAL_SESSIONS,
        forced_variant=req.forced_variant,
        is_model_ready=_lambda_ranker.is_trained,
    )

    if variant == "lambdarank" and _lambda_ranker.is_trained:
        ranked_pairs = _lambda_ranker.rank(candidates)
    else:
        # Default or fallback to transparent rule ranking
        ranked_pairs = RuleBasedRanker.rank(candidates)
        variant = "rules"

    # Fairness Audit
    ranked_candidates_only = [c for c, _ in ranked_pairs]
    fairness_audit = FairnessAuditor.audit_top_k(
        ranked_candidates=ranked_candidates_only,
        pool_candidates=candidates,
        k=min(3, len(candidates)),
    )

    # Mitigation boost if requested and disparate impact violated
    if req.apply_fairness_mitigation and not fairness_audit["is_fair"]:
        ranked_pairs = FairnessAuditor.mitigate_with_parity_boost(
            ranked_pairs=ranked_pairs,
            pool_candidates=candidates,
            k=min(3, len(candidates)),
        )
        # Re-audit post mitigation
        fairness_audit = FairnessAuditor.audit_top_k(
            ranked_candidates=[c for c, _ in ranked_pairs],
            pool_candidates=candidates,
            k=min(3, len(candidates)),
        )
        fairness_audit["mitigation_applied"] = True

    results = []
    top_candidates_log = []
    for rank_idx, (cand, score) in enumerate(ranked_pairs, start=1):
        res = RankedCandidateResult(
            rank=rank_idx,
            candidate_id=cand.candidate_id,
            farmer_name=cand.farmer_name,
            crop=cand.crop,
            score=round(score, 4),
            is_smallholder=cand.is_smallholder,
            distance_km=cand.distance_km,
            quantity_fit=round(cand.quantity_fit, 3),
            grade_fit=round(cand.grade_fit, 3),
            price_fit_vs_mandi=round(cand.price_fit_vs_mandi, 3),
        )
        results.append(res)
        if rank_idx <= 3:
            top_candidates_log.append(res.model_dump())

    # Record decision audit trace
    record_ranking_audit_log(
        query_id=req.query_id,
        buyer_id=req.buyer_id,
        variant_used=variant,
        top_candidates=top_candidates_log,
        fairness_audit=fairness_audit,
    )

    return RankingResponse(
        query_id=req.query_id,
        buyer_id=req.buyer_id,
        variant_used=variant,
        ranked_candidates=results,
        fairness_audit=fairness_audit,
        data_sufficiency=sufficiency,
    )


@router.post("/rate-guide", response_model=RateGuideResponse)
async def get_transport_rate_guide(req: RateGuideRequest) -> RateGuideResponse:
    """
    Predicts fair indicative transport rate range with operational cost breakdown.
    """
    res = transport_rate_model.predict_rate_guide(
        distance_km=req.distance_km,
        load_weight_kg=req.load_weight_kg,
        vehicle_type=req.vehicle_type,
        fuel_price=req.fuel_price_per_litre,
        road_type=req.road_type,
        is_night=req.is_night,
    )
    return RateGuideResponse(**res)


@router.post("/pool-routes", response_model=PoolingResponse)
async def pool_transport_routes(req: PoolingRequest) -> PoolingResponse:
    """
    Solves multi-stop vehicle pickup routing using Google OR-Tools.
    Enforces payload capacities, pickup time windows, and crop spoilage shelf-life limits.
    Reports cost-per-kg savings versus separate individual trips.
    """
    pickups_dicts = [p.model_dump() for p in req.pickups]
    dropoff_dict = req.dropoff.model_dump()
    fleet_dicts = [v.model_dump() for v in req.vehicles] if req.vehicles else None

    solution = ORToolsVRPSolver.solve_pooling(
        pickups=pickups_dicts,
        dropoff=dropoff_dict,
        vehicles=fleet_dicts,
        max_search_seconds=req.max_search_seconds,
    )
    return PoolingResponse(**solution)


@router.post("/rank-drivers", response_model=DriverMatchResponse)
async def rank_drivers(req: DriverMatchRequest) -> DriverMatchResponse:
    """
    Ranks verified available drivers with anti-monopoly fair distribution.
    Prevents a small subset of drivers from monopolizing all trips.
    """
    driver_objs = [
        DriverProfile(
            driver_id=d.driver_id,
            name=d.name,
            phone=d.phone,
            vehicle_type=d.vehicle_type,
            vehicle_model=d.vehicle_model,
            capacity_kg=d.capacity_kg,
            current_latitude=d.current_latitude,
            current_longitude=d.current_longitude,
            reliability_rating=d.reliability_rating,
            on_time_rate=d.on_time_rate,
            trips_completed_total=d.trips_completed_total,
            recent_trips_count=d.recent_trips_count,
            is_verified=d.is_verified,
            is_available=d.is_available,
        )
        for d in req.drivers
    ]

    ranked = DriverMatchingEngine.rank_drivers(
        drivers=driver_objs,
        pickup_lat=req.pickup_lat,
        pickup_lng=req.pickup_lng,
        load_weight_kg=req.load_weight_kg,
        apply_fairness_leveling=req.apply_fairness_leveling,
        limit=req.limit,
    )

    recent_counts = [d.recent_trips_count for d in driver_objs]
    gini = DriverMatchingEngine.calculate_gini_coefficient(recent_counts)

    return DriverMatchResponse(
        total_evaluated=len(driver_objs),
        ranked_drivers=ranked,
        gini_coefficient=gini,
        leveling_enabled=req.apply_fairness_leveling,
    )


@router.get("/data-sufficiency")
async def get_data_sufficiency_status() -> dict[str, Any]:
    """
    Returns data sufficiency analysis and mathematical rationale for ML vs Rule ranking.
    """
    return DataSufficiencyChecker.check_sufficiency(_CURRENT_HISTORICAL_SESSIONS)


@router.get("/audit-logs", dependencies=[Depends(require_admin_role_enforced())])
async def list_ranking_audit_logs(limit: int = 50) -> list[dict[str, Any]]:
    """
    Returns recent ranking and safety audit logs.
    """
    return get_matching_audit_logs(limit=limit)
