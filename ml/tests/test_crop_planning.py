"""
GrowCircle ML-3 Crop Planning & Downside Risk Engine Test Suite.
Verifies:
1. ANGRAU / KVK agronomic suitability filtering (no unverified crops recommended).
2. Quantile range constraints (p10 <= p50 <= p90, ranges always, never single numbers).
3. Cobweb crowding & price crash risk scoring mechanics.
4. Blended farmer diary cost and yield updates.
5. Multilingual voice advisories (< 45s audio) and mandatory KVK statutory disclaimers.
6. Multi-season historical backtest validation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ml.planning.agronomic_knowledge import (
    get_agronomically_suitable_crops,
)
from ml.planning.planner_engine import CropPlanningEngine, CropPlanResponse


@pytest.fixture
def planner_engine() -> CropPlanningEngine:
    return CropPlanningEngine()


def test_agronomic_suitability_filtering() -> None:
    """Verifies that only ANGRAU / KVK verified crops are returned for a district and planting month."""
    # Guntur in July (monsoon / Kharif)
    suitable_july = get_agronomically_suitable_crops("guntur", 7)
    crop_ids = [c.crop_id for c in suitable_july]

    assert len(suitable_july) >= 3
    # Guntur in July is suitable for banana, onion, chilli, tomato, maize
    assert "banana" in crop_ids
    assert "chilli" in crop_ids

    # Each crop profile must cite verified agronomic and finance sources
    for prof in suitable_july:
        assert prof.agronomic_source != ""
        assert "ANGRAU" in prof.agronomic_source or "KVK" in prof.agronomic_source or "YSR" in prof.agronomic_source
        assert prof.finance_source != ""


def test_ranges_always_never_single_numbers(planner_engine: CropPlanningEngine) -> None:
    """Confirms all candidate crop metrics are strictly 3-element ranges [10th, 50th, 90th]."""
    plan = planner_engine.generate_plan(district="Guntur", planting_month=7)

    assert isinstance(plan, CropPlanResponse)
    assert 3 <= len(plan.ranked_candidates) <= 5

    for c in plan.ranked_candidates:
        # Harvest price range: [p10, p50, p90]
        assert len(c.harvest_price_kg_range) == 3
        p10, p50, p90 = c.harvest_price_kg_range
        assert p10 <= p50 <= p90
        assert p10 > 0

        # Yield range: [y10, y50, y90]
        assert len(c.yield_tonnes_acre_range) == 3
        y10, y50, y90 = c.yield_tonnes_acre_range
        assert y10 <= y50 <= y90
        assert y10 > 0

        # Cost range: [c10, c50, c90]
        assert len(c.cost_per_acre_range) == 3
        c10, c50, c90 = c.cost_per_acre_range
        assert c10 <= c50 <= c90
        assert c10 > 0

        # Profit range: [downside_10, expected_50, upside_90]
        assert len(c.profit_per_acre_range) == 3
        d10, e50, u90 = c.profit_per_acre_range
        assert d10 <= e50 <= u90
        assert c.downside_profit_acre == d10
        assert c.expected_profit_acre == e50
        assert c.upside_profit_acre == u90


def test_ranked_by_expected_profit(planner_engine: CropPlanningEngine) -> None:
    """Verifies candidate crops are ranked by expected profit per acre in descending order."""
    plan = planner_engine.generate_plan(district="Guntur", planting_month=7)

    profits = [c.expected_profit_acre for c in plan.ranked_candidates]
    assert profits == sorted(profits, reverse=True)


def test_cobweb_crowding_and_crash_risk(planner_engine: CropPlanningEngine) -> None:
    """Verifies crash risk scoring and crowding factor logic."""
    plan = planner_engine.generate_plan(district="Guntur", planting_month=7)

    for c in plan.ranked_candidates:
        assert 0 <= c.crash_risk_score <= 100
        assert c.crash_risk_level in ["LOW", "MEDIUM", "HIGH", "SEVERE"]
        assert c.crowding_factor > 0.5
        assert len(c.rationale) > 20

    # Green chilli or tomato in Guntur typically has high district acreage share
    high_share_crops = [c for c in plan.ranked_candidates if c.crop_id in ["chilli", "tomato"]]
    for c in high_share_crops:
        # Should be classified as having heightened risk or crowding
        assert c.crash_risk_score >= 30


def test_farmer_diary_blending(planner_engine: CropPlanningEngine) -> None:
    """Verifies that farmer diary costs and yields blend 50% with regional norms."""
    # Base plan with regional norms
    plan_base = planner_engine.generate_plan(district="Guntur", planting_month=7)
    assert plan_base.data_sufficiency == "regional_norms"

    # Customized diary entry for tomato (e.g. low-cost farmer with 35,000 cost and 12t yield)
    diary_summary = {
        "tomato": {
            "cost_per_acre": 35000.0,
            "yield_tonnes_acre": 12.0,
        }
    }

    plan_blended = planner_engine.generate_plan(
        district="Guntur",
        planting_month=7,
        farmer_diary_summary=diary_summary,
        farmer_id=42,
    )

    assert plan_blended.data_sufficiency == "blended_farmer_diary"
    assert plan_blended.farmer_id == 42

    base_tomato = next(c for c in plan_base.ranked_candidates if c.crop_id == "tomato")
    blended_tomato = next(c for c in plan_blended.ranked_candidates if c.crop_id == "tomato")

    # Median cost should be lower than baseline (58,000 baseline vs blended (35000 + 58000)/2 = 46500)
    assert blended_tomato.cost_per_acre_range[1] < base_tomato.cost_per_acre_range[1]


def test_voice_summary_and_statutory_disclaimers(planner_engine: CropPlanningEngine) -> None:
    """Verifies 4-language spoken summaries under 45s audio and mandatory KVK disclaimers."""
    plan = planner_engine.generate_plan(district="Annamayya", planting_month=8)

    # Mandatory plain disclaimer
    assert "guidance" in plan.plain_disclaimer.lower()
    assert "kvk" in plan.plain_disclaimer.lower() or "agriculture officer" in plan.plain_disclaimer.lower()

    # Voice summary must support en, te, hi, gu
    assert set(plan.voice_summary.keys()) == {"en", "te", "hi", "gu"}

    # Word count check: Spoken rate is ~130 words per minute.
    # 45 seconds corresponds to <= 98 words.
    for lang, text in plan.voice_summary.items():
        assert len(text) > 30, f"Voice text for {lang} is too short"
        word_count = len(text.split())
        assert word_count <= 85, f"Voice advisory for {lang} has {word_count} words, exceeds 45s audio target"


def test_backtest_report_validity() -> None:
    """Verifies that the historical multi-season backtest report exists and documents honest metrics."""
    report_path = Path("docs/ml/crop_planning_backtest_report.json")
    assert report_path.exists(), "Backtest report JSON must exist"

    with open(report_path, encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("total_seasons_tested", 0) >= 5
    assert data.get("crashes_encountered", 0) >= 1
    # Verify 100% crash avoidance rate on genuine supply gluts
    assert data.get("crash_avoidance_rate_pct") == 100.0

    # Verify honest reporting of false alarms (weather/disease in competing states)
    assert data.get("false_alarm_count", 0) >= 1
    assert "honest_evaluation_summary" in data
    assert len(data.get("cases", [])) >= 5
