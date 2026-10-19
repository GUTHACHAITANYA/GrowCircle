"""
Unit tests for ML-5: Smarter Matching and Logistics.

Tests:
1. Rule-based ranking and LightGBM LambdaRank listwise model with NDCG@3.
2. Data sufficiency check (1,200 sessions threshold) and fallback.
3. Smallholder fairness auditing and parity mitigation boost.
4. Fair transport rate guide regression ranges and breakdown.
5. Google OR-Tools multi-stop CVRPTW pooling with crop spoilage and cost-per-kg savings.
6. Driver matching with anti-monopoly leveling penalty and Gini coefficient.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.logistics.driver_allocation import DriverMatchingEngine, DriverProfile
from ml.logistics.ranking_engine import (
    DataSufficiencyChecker,
    FairnessAuditor,
    LightGBMLambdaRanker,
    MatchingABGating,
    RankingCandidate,
    RuleBasedRanker,
    compute_ndcg_at_k,
    get_matching_audit_logs,
    record_ranking_audit_log,
)
from ml.logistics.rate_guide import (
    GUIDE_RATE_DISCLAIMER,
    TransportRateGuideModel,
)
from ml.logistics.vrp_pooling import ORToolsVRPSolver


def test_ranking_candidate_features() -> None:
    """Verifies feature extraction and implicit feedback mapping."""
    cand = RankingCandidate(
        candidate_id="C-1",
        farmer_name="Appa Rao",
        crop="tomato",
        distance_km=15.0,
        quantity_kg=400.0,
        requested_qty_kg=500.0,
        farmer_grade="A",
        buyer_grade_req="A",
        price_per_kg=22.0,
        mandi_modal_price=20.0,
        completion_rate=0.95,
        response_time_hours=1.5,
        rating=4.8,
        is_smallholder=True,
        implicit_feedback={"views": 2, "accepts": 1, "completes": 1, "on_time": 1, "complaints": 0},
    )

    assert cand.quantity_fit == pytest.approx(0.80)
    assert cand.grade_fit == 1.0
    assert cand.price_fit_vs_mandi == pytest.approx(0.90)  # 10% diff
    assert cand.distance_score == pytest.approx(0.70)
    assert cand.implicit_relevance_label == 4  # completed on-time with 0 complaints

    vec = cand.to_feature_vector()
    assert vec["is_smallholder"] == 1.0
    assert vec["rating_norm"] == pytest.approx(0.96)


def test_rule_based_ranker() -> None:
    """Verifies deterministic rule-based ranking logic."""
    c1 = RankingCandidate(
        candidate_id="C1",
        farmer_name="Farmer Close",
        crop="tomato",
        distance_km=5.0,
        quantity_kg=500.0,
        requested_qty_kg=500.0,
        farmer_grade="A",
        buyer_grade_req="A",
        price_per_kg=20.0,
        mandi_modal_price=20.0,
        completion_rate=1.0,
        response_time_hours=0.5,
        rating=5.0,
        is_smallholder=True,
    )
    c2 = RankingCandidate(
        candidate_id="C2",
        farmer_name="Farmer Far",
        crop="tomato",
        distance_km=45.0,
        quantity_kg=200.0,
        requested_qty_kg=500.0,
        farmer_grade="C",
        buyer_grade_req="A",
        price_per_kg=35.0,
        mandi_modal_price=20.0,
        completion_rate=0.6,
        response_time_hours=12.0,
        rating=3.0,
        is_smallholder=False,
    )

    ranked = RuleBasedRanker.rank([c2, c1])
    assert ranked[0][0].candidate_id == "C1"
    assert ranked[0][1] > ranked[1][1]


def test_lambdarank_training_and_ndcg() -> None:
    """Verifies LightGBM LambdaRank training and NDCG@3 computation."""
    ranker = LightGBMLambdaRanker()

    # Generate synthetic grouped ranking dataset
    rng = np.random.default_rng(seed=42)
    n_groups = 40
    group_size = 6

    rows = []
    labels = []
    group_sizes = [group_size] * n_groups

    for _ in range(n_groups):
        for _ in range(group_size):
            dist = rng.uniform(2.0, 50.0)
            q_fit = rng.uniform(0.3, 1.0)
            g_fit = rng.choice([0.4, 0.75, 1.0])
            p_fit = rng.uniform(0.5, 1.0)
            comp_rate = rng.uniform(0.6, 1.0)
            resp_time = rng.uniform(0.5, 8.0)
            rating_norm = rng.uniform(0.5, 1.0)
            smallholder = rng.choice([0.0, 1.0])

            # Synthetic relevance label correlated with features
            rel_score = int(np.clip(
                round(q_fit * 2.0 + g_fit * 1.5 + p_fit * 1.5 - (dist / 50.0) * 1.5 + comp_rate * 1.0),
                0,
                4,
            ))

            rows.append({
                "distance_km": dist,
                "quantity_fit": q_fit,
                "grade_fit": g_fit,
                "price_fit_vs_mandi": p_fit,
                "completion_rate": comp_rate,
                "response_time_hours": resp_time,
                "rating_norm": rating_norm,
                "is_smallholder": smallholder,
            })
            labels.append(rel_score)

    df = pd.DataFrame(rows)
    y = np.array(labels)

    train_res = ranker.train(df, y, group_sizes)
    assert train_res["status"] == "trained"
    assert ranker.is_trained is True

    # Test NDCG computation helper
    y_true = [4, 2, 0]
    y_pred_good = [0.9, 0.5, 0.1]
    y_pred_bad = [0.1, 0.5, 0.9]

    ndcg_good = compute_ndcg_at_k(y_true, y_pred_good, k=3)
    ndcg_bad = compute_ndcg_at_k(y_true, y_pred_bad, k=3)

    assert ndcg_good == pytest.approx(1.0, abs=0.01)
    assert ndcg_good > ndcg_bad


def test_data_sufficiency_check() -> None:
    """Verifies statistical data sufficiency check and rationale."""
    # Under 1,200 sessions
    status_low = DataSufficiencyChecker.check_sufficiency(450)
    assert status_low["is_sufficient"] is False
    assert "Keep transparent rule-based ranking" in status_low["recommendation"]
    assert "1,200" in status_low["statistical_rationale"]

    # Over 1,200 sessions
    status_high = DataSufficiencyChecker.check_sufficiency(1400)
    assert status_high["is_sufficient"] is True


def test_ab_gating() -> None:
    """Verifies deterministic A/B gating and fallbacks."""
    # When data is small, always fallback to 'rules'
    variant_fallback = MatchingABGating.determine_variant(
        query_id="query_abc",
        total_sessions=300,
        is_model_ready=True,
    )
    assert variant_fallback == "rules"

    # Forced variant
    variant_forced = MatchingABGating.determine_variant(
        query_id="query_abc",
        total_sessions=300,
        forced_variant="lambdarank",
        is_model_ready=True,
    )
    assert variant_forced == "lambdarank"

    # Deterministic split when data is sufficient
    v1 = MatchingABGating.determine_variant("query_test_1", 2000, is_model_ready=True)
    v2 = MatchingABGating.determine_variant("query_test_1", 2000, is_model_ready=True)
    assert v1 == v2


def test_fairness_auditor_and_parity_boost() -> None:
    """Verifies smallholder exposure audit and parity boost mitigation."""
    c_large1 = RankingCandidate("L1", "Large 1", "tomato", 10, 5000, 5000, "A", "A", 20, 20, 1.0, 1.0, 5.0, False)
    c_large2 = RankingCandidate("L2", "Large 2", "tomato", 12, 4000, 4000, "A", "A", 20, 20, 1.0, 1.0, 5.0, False)
    c_large3 = RankingCandidate("L3", "Large 3", "tomato", 14, 3000, 3000, "A", "A", 20, 20, 1.0, 1.0, 5.0, False)
    c_small1 = RankingCandidate("S1", "Small 1", "tomato", 15, 300, 500, "A", "A", 20, 20, 0.9, 1.0, 4.5, True)

    pool = [c_large1, c_large2, c_large3, c_small1]
    # In pool, 25% are smallholders (1 out of 4)
    # If top 3 has 0 smallholders:
    top_3_unfair = [c_large1, c_large2, c_large3]

    audit = FairnessAuditor.audit_top_k(top_3_unfair, pool, k=3)
    assert audit["is_fair"] is False
    assert audit["exposure_ratio"] == 0.0

    # Test parity boost mitigation
    ranked_pairs = [
        (c_large1, 0.95),
        (c_large2, 0.90),
        (c_large3, 0.85),
        (c_small1, 0.80),
    ]
    boosted = FairnessAuditor.mitigate_with_parity_boost(ranked_pairs, pool, k=3)
    boosted_candidates = [c for c, _ in boosted[:3]]

    # Smallholder promoted into top 3
    assert any(c.is_smallholder for c in boosted_candidates)
    audit_post = FairnessAuditor.audit_top_k(boosted_candidates, pool, k=3)
    assert audit_post["is_fair"] is True


def test_audit_logging() -> None:
    """Verifies decision audit trail logging."""
    record_ranking_audit_log(
        query_id="Q-100",
        buyer_id="B-50",
        variant_used="rules",
        top_candidates=[{"candidate_id": "C-1", "rank": 1}],
        fairness_audit={"is_fair": True, "exposure_ratio": 1.0},
    )
    logs = get_matching_audit_logs(limit=5)
    assert len(logs) >= 1
    assert logs[0]["query_id"] == "Q-100"


def test_transport_rate_guide() -> None:
    """Verifies transport rate regression model ranges, road multipliers, and night surcharge."""
    model = TransportRateGuideModel()

    # Daytime, district road
    day_res = model.predict_rate_guide(
        distance_km=40.0,
        load_weight_kg=800.0,
        vehicle_type="mini_truck",
        fuel_price=98.50,
        road_type="district_road",
        is_night=False,
    )
    assert day_res["min_guide_rate"] <= day_res["estimated_guide_rate"] <= day_res["max_guide_rate"]
    assert day_res["rate_per_kg"] > 0.0
    assert day_res["disclaimer"] == GUIDE_RATE_DISCLAIMER

    # Night surcharge comparison
    night_res = model.predict_rate_guide(
        distance_km=40.0,
        load_weight_kg=800.0,
        vehicle_type="mini_truck",
        fuel_price=98.50,
        road_type="district_road",
        is_night=True,
    )
    assert night_res["estimated_guide_rate"] > day_res["estimated_guide_rate"]

    # Rural unpaved road comparison
    rough_road_res = model.predict_rate_guide(
        distance_km=40.0,
        load_weight_kg=800.0,
        vehicle_type="mini_truck",
        fuel_price=98.50,
        road_type="rural_unpaved",
        is_night=False,
    )
    assert rough_road_res["estimated_guide_rate"] > day_res["estimated_guide_rate"]


def test_ortools_vrp_pooling() -> None:
    """Verifies Google OR-Tools multi-stop CVRPTW pooling with spoilage and savings."""
    # 3 Tenali/Guntur farmers pooling tomato and banana into Guntur Market Yard
    pickups = [
        {
            "order_id": "ORD-1",
            "farmer_name": "Ramesh",
            "latitude": 16.242,
            "longitude": 80.641,
            "weight_kg": 400.0,
            "crop": "tomato",
            "earliest_pickup_hour": 1.0,
            "latest_pickup_hour": 4.0,
        },
        {
            "order_id": "ORD-2",
            "farmer_name": "Venkatesh",
            "latitude": 16.255,
            "longitude": 80.635,
            "weight_kg": 350.0,
            "crop": "tomato",
            "earliest_pickup_hour": 1.5,
            "latest_pickup_hour": 5.0,
        },
        {
            "order_id": "ORD-3",
            "farmer_name": "Lakshmi",
            "latitude": 16.230,
            "longitude": 80.650,
            "weight_kg": 300.0,
            "crop": "banana",
            "earliest_pickup_hour": 2.0,
            "latest_pickup_hour": 5.5,
        },
    ]

    dropoff = {
        "destination_name": "Guntur Wholesale Market",
        "latitude": 16.306,
        "longitude": 80.436,
        "latest_arrival_hour": 10.0,
    }

    fleet = [
        {
            "vehicle_id": "MINI-101",
            "vehicle_type": "mini_truck",
            "capacity_kg": 1500.0,
        }
    ]

    result = ORToolsVRPSolver.solve_pooling(pickups, dropoff, fleet)

    assert result["success"] is True
    assert result["total_vehicles_used"] >= 1
    assert result["total_cargo_weight_kg"] == 1050.0

    # Spoilage safety check
    for route in result["routes"]:
        assert route["spoilage_safe"] is True
        assert route["dropoff_arrival_hour"] <= route["max_crop_spoilage_limit_hours"]
        assert route["utilized_load_kg"] <= route["capacity_kg"]

    # Savings validation
    savings = result["savings"]
    assert savings["total_separate_cost_inr"] > savings["total_pooled_cost_inr"]
    assert savings["inr_saved"] > 0
    assert savings["percentage_saved"] > 15.0  # pooling saves >15% freight costs
    assert savings["cost_per_kg_pooled_inr"] < savings["cost_per_kg_separate_inr"]
    assert savings["distance_reduced_km"] > 0


def test_driver_matching_and_fair_leveling() -> None:
    """Verifies driver ranking with anti-monopoly fair leveling penalty."""
    d_active = DriverProfile(
        driver_id="D-1",
        name="Star Driver",
        phone="9876543210",
        vehicle_type="mini_truck",
        vehicle_model="Tata Ace",
        capacity_kg=1200.0,
        current_latitude=16.240,
        current_longitude=80.640,
        reliability_rating=4.9,
        on_time_rate=0.98,
        trips_completed_total=120,
        recent_trips_count=10,  # Highly loaded driver (fatigued / monopolizing)
    )

    d_idle = DriverProfile(
        driver_id="D-2",
        name="Available Peer",
        phone="9876543211",
        vehicle_type="mini_truck",
        vehicle_model="Mahindra Bolero",
        capacity_kg=1200.0,
        current_latitude=16.241,
        current_longitude=80.641,
        reliability_rating=4.7,
        on_time_rate=0.94,
        trips_completed_total=40,
        recent_trips_count=0,  # Zero trips in last 7 days
    )

    drivers = [d_active, d_idle]

    # Without leveling: Star driver wins due to slightly higher rating/on-time
    ranked_no_level = DriverMatchingEngine.rank_drivers(
        drivers=drivers,
        pickup_lat=16.240,
        pickup_lng=80.640,
        load_weight_kg=500.0,
        apply_fairness_leveling=False,
    )
    assert ranked_no_level[0]["driver_id"] == "D-1"

    # With leveling: Fatigue penalty dampens D-1 so available peer D-2 gets dispatched
    ranked_levelled = DriverMatchingEngine.rank_drivers(
        drivers=drivers,
        pickup_lat=16.240,
        pickup_lng=80.640,
        load_weight_kg=500.0,
        apply_fairness_leveling=True,
    )
    assert ranked_levelled[0]["driver_id"] == "D-2"
    assert ranked_levelled[1]["equity_multiplier"] < 1.0

    # Gini coefficient
    gini = DriverMatchingEngine.calculate_gini_coefficient([10, 0])
    assert gini > 0.40  # Shows high inequality
