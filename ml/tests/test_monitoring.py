"""
Unit tests for ML-7: Post-Launch Monitoring, Drift Detection, Alerts, and Safe Releases.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ml.monitoring.alerts import AlertEngine
from ml.monitoring.cost_controller import CostController
from ml.monitoring.drift_detector import DriftDetector
from ml.monitoring.feedback_loop import HumanFeedbackLoop
from ml.monitoring.release_manager import ModelReleaseManager, ReleaseStage


def test_drift_detector_ks_and_psi() -> None:
    """Verifies KS test and PSI calculation on identical and drifted distributions."""
    np.random.seed(42)
    ref = np.random.normal(25.0, 3.0, 200)
    same_dist = np.random.normal(25.1, 3.0, 200)
    drifted_dist = np.random.normal(38.0, 5.0, 200)

    # Identical / same distribution
    res_stable = DriftDetector.compute_ks_drift(ref, same_dist)
    psi_stable = DriftDetector.compute_psi(ref, same_dist)
    assert not res_stable["drift_detected"]
    assert psi_stable < 0.25

    # Drifted distribution
    res_drift = DriftDetector.compute_ks_drift(ref, drifted_dist)
    psi_drift = DriftDetector.compute_psi(ref, drifted_dist)
    assert res_drift["drift_detected"]
    assert res_drift["p_value"] < 0.05
    assert psi_drift >= 0.25

    # Feature-level dataset drift test
    ref_df = pd.DataFrame({"feat1": ref, "feat2": np.random.normal(10, 1, 200)})
    curr_df = pd.DataFrame({"feat1": drifted_dist, "feat2": np.random.normal(20, 2, 200)})
    report = DriftDetector.detect_feature_data_drift(ref_df, curr_df)
    assert report["dataset_drift_detected"]
    assert report["drifted_features_count"] == 2


def test_daily_forecast_error_tracking_and_calibration() -> None:
    """Verifies MAE, sMAPE, pinball losses, and empirical interval calibration."""
    records = [
        {"crop": "tomato", "actual_price": 22.0, "predicted_p10": 19.0, "predicted_p50": 22.5, "predicted_p90": 25.0},
        {"crop": "tomato", "actual_price": 24.0, "predicted_p10": 20.0, "predicted_p50": 23.0, "predicted_p90": 26.0},
        {"crop": "banana", "actual_price": 35.0, "predicted_p10": 30.0, "predicted_p50": 34.0, "predicted_p90": 38.0},
        {"crop": "banana", "actual_price": 42.0, "predicted_p10": 31.0, "predicted_p50": 36.0, "predicted_p90": 40.0},  # outside
        {"crop": "onion", "actual_price": 28.0, "predicted_p10": 25.0, "predicted_p50": 28.0, "predicted_p90": 31.0},
    ]

    eval_res = DriftDetector.track_daily_forecast_errors(records)
    assert eval_res["total_evaluations"] == 5
    assert eval_res["mae"] > 0.0
    assert eval_res["smape_pct"] > 0.0
    assert eval_res["interval_coverage_pct"] == 80.0  # 4 out of 5 inside [P10, P90]
    assert eval_res["is_well_calibrated"]
    assert eval_res["calibration_status"] == "CALIBRATED"
    assert "tomato" in eval_res["per_crop_breakdown"]


def test_vision_and_voice_health_tracking() -> None:
    """Verifies vision confidence distribution and multilingual voice agent failure metrics."""
    vision_records = [
        {"confidence": 0.88, "blur_score": 140.0, "glare_detected": False},
        {"confidence": 0.92, "blur_score": 150.0, "glare_detected": False},
        {"confidence": 0.55, "blur_score": 80.0, "is_blurry": True, "glare_detected": False},
    ]
    vis_res = DriftDetector.track_vision_confidence_distribution(vision_records)
    assert vis_res["total_inferences"] == 3
    assert vis_res["mean_confidence"] > 0.70
    assert vis_res["low_confidence_rate_pct"] == 33.3

    voice_logs = [
        {"language": "te", "intent_matched": True, "hallucination_detected": False, "routed_to_kvk": False, "wer": 0.05},
        {"language": "te", "intent_matched": True, "hallucination_detected": False, "routed_to_kvk": False, "wer": 0.06},
        {"language": "gu", "intent_matched": False, "hallucination_detected": False, "routed_to_kvk": True, "wer": 0.08},
    ]
    voice_res = DriftDetector.track_voice_agent_failure_rates(voice_logs)
    assert voice_res["total_logged_interactions"] == 3
    assert voice_res["by_language"]["te"]["status"] == "HEALTHY"
    assert voice_res["by_language"]["gu"]["intent_error_rate_pct"] == 100.0


def test_alert_engine_triggers() -> None:
    """Verifies alert triggers for error breach, data outage, policy shocks, and festivals."""
    engine = AlertEngine()

    # 1. Forecast error breach alert
    alert1 = engine.check_forecast_error_alert({"smape_pct": 32.5, "mae": 6.8})
    assert alert1 is not None
    assert alert1.severity == "CRITICAL"
    assert alert1.category == "FORECAST_ERROR"

    # 2. Data outage alert
    alert2 = engine.check_data_arrival_alert(active_mandis_count=10, expected_mandis_count=100)
    assert alert2 is not None
    assert alert2.category == "DATA_OUTAGE"

    # 3. Festival detection
    alert3 = engine.detect_policy_or_festival_shock([22.0, 23.0], date_str="2026-01-14", crop="banana")
    assert alert3 is not None
    assert alert3.category == "FESTIVAL_SURGE"

    # 4. Policy shock detection (sudden 50% jump)
    prices = [20.0, 21.0, 20.5, 20.0, 35.0, 38.0, 42.0]
    alert4 = engine.detect_policy_or_festival_shock(prices, date_str="2026-10-13", crop="onion")
    assert alert4 is not None
    assert alert4.category == "POLICY_SHOCK"

    # 5. Acknowledge alert
    active = engine.get_active_alerts()
    assert len(active) >= 4
    ok = engine.acknowledge_alert(alert1.alert_id)
    assert ok
    remaining = engine.get_active_alerts()
    assert len(remaining) == len(active) - 1


def test_release_manager_shadow_and_canary_routing() -> None:
    """Verifies shadow and canary routing behavior."""
    mgr = ModelReleaseManager(model_name="test_forecaster", baseline_version="v1.0")

    # Baseline mode
    base_res = mgr.route_request(
        user_id="user-123",
        baseline_fn=lambda x: f"base-{x}",
        candidate_fn=lambda x: f"cand-{x}",
        x="test",
    )
    assert base_res["served_by"] == "v1.0"
    assert not base_res.get("is_shadow")

    # Shadow mode
    mgr.deploy_shadow(
        candidate_version="v1.1-shadow",
        data_hash="hash-abc",
        initial_metrics={"smape_pct": 13.0, "mae": 2.1},
    )
    assert mgr.stage == ReleaseStage.SHADOW
    shadow_res = mgr.route_request(
        user_id="user-123",
        baseline_fn=lambda: "baseline_prediction",
        candidate_fn=lambda: "candidate_shadow_prediction",
    )
    assert shadow_res["served_by"] == "v1.0"  # User only sees baseline
    assert shadow_res["shadow_result"] == "candidate_shadow_prediction"
    assert shadow_res["is_shadow"]

    # Canary mode (20% traffic)
    mgr.deploy_canary(candidate_version="v1.1-canary", canary_pct=20)
    assert mgr.stage == ReleaseStage.CANARY

    # Check routing across different users
    served_versions = set()
    for uid in range(50):
        r = mgr.route_request(
            user_id=uid,
            baseline_fn=lambda: "base",
            candidate_fn=lambda: "cand",
        )
        served_versions.add(r["served_by"])

    # At least some traffic went to baseline and canary
    assert "v1.0" in served_versions
    assert "v1.1-canary" in served_versions


def test_release_manager_automatic_rollback() -> None:
    """Verifies that metric regression in canary triggers immediate automatic rollback."""
    mgr = ModelReleaseManager(model_name="test_rollback_forecaster", baseline_version="v1.0")
    mgr.deploy_canary(candidate_version="v1.1-buggy", canary_pct=10)

    # 1. Healthy metrics pass guardrail
    healthy = mgr.evaluate_canary_guardrails({"smape_pct": 14.5, "latency_ms": 15.0, "error_rate": 0.0})
    assert healthy
    assert mgr.stage == ReleaseStage.CANARY

    # 2. Severe error spike breaches guardrail (sMAPE degrades by >15%)
    # Baseline sMAPE is 14.2; candidate sMAPE 22.0 is > 14.2 * 1.15 = 16.33
    healthy_after_spike = mgr.evaluate_canary_guardrails({"smape_pct": 22.0, "latency_ms": 15.0, "error_rate": 0.0})
    assert not healthy_after_spike
    assert mgr.stage == ReleaseStage.ROLLEDBACK
    assert mgr.last_rollback_reason is not None
    assert "exceeded baseline" in mgr.last_rollback_reason

    # Subsequent traffic is strictly served by baseline
    fallback_call = mgr.route_request(
        user_id="any-user",
        baseline_fn=lambda: "safe_baseline",
        candidate_fn=lambda: "failed_cand",
    )
    assert fallback_call["served_by"] == "v1.0"
    assert fallback_call["result"] == "safe_baseline"


def test_human_feedback_loop_and_eval_promotion(tmp_path) -> None:
    """Verifies error reporting, PII redaction, review queue, and golden test case promotion."""
    eval_file = tmp_path / "test_eval_cases.json"
    loop = HumanFeedbackLoop(storage_path=str(eval_file))

    # Record 1-click error report containing sensitive PII
    res = loop.record_wrong_answer(
        user_id="farmer-88",
        channel="ivr",
        category="price_error",
        query_text="Call me at 9848022338, Tenali tomato rate is wrong",
        model_response="Tenali tomato rate is ₹34.0/kg",
        farmer_correction="Actual mandi modal rate is ₹22.0/kg",
    )
    assert res["status"] == "queued_for_review"
    fb_id = res["feedback_id"]

    # Verify PII was redacted
    queue = loop.get_review_queue(status_filter="pending_review")
    assert len(queue) == 1
    assert "9848022338" not in queue[0]["query_text"]
    assert "[PHONE_REDACTED]" in queue[0]["query_text"]

    # Agronomist promotes error to golden regression test case
    review_res = loop.review_and_resolve(
        feedback_id=fb_id,
        action="promote_to_eval",
        reviewer_notes="Verified against AP Agmarknet physical bulletin",
    )
    assert review_res["status"] == "promoted_to_eval"

    # Verify golden test cases
    golden_cases = loop.get_promoted_eval_cases()
    assert len(golden_cases) == 1
    assert golden_cases[0]["category"] == "price_error"
    assert golden_cases[0]["expected_behavior"] == "Actual mandi modal rate is ₹22.0/kg"


def test_cost_controller_tariffs_and_caching() -> None:
    """Verifies unit cost tracking, cache hit/miss, and cost savings."""
    ctrl = CostController(daily_budget_inr=1000.0)

    # Record a 45-second call
    call_cost = ctrl.record_call_cost(
        duration_seconds=45.0,
        stt_audio_seconds=15.0,
        tts_audio_seconds=20.0,
        llm_prompt_tokens=200,
        llm_completion_tokens=80,
    )
    assert call_cost["turn_cost_inr"] > 0.0
    assert ctrl.total_calls_tracked == 1

    # Record 2 SMS messages
    ctrl.record_sms_cost(count=2)
    assert ctrl.total_messages_tracked == 2
    assert ctrl.total_sms_cost_inr == 0.24

    # Caching test
    miss = ctrl.get_from_cache("audio_tts", "hash_welcome_te")
    assert miss is None
    assert ctrl.cache_misses == 1

    ctrl.set_in_cache("audio_tts", "hash_welcome_te", b"synthetic_wav_data", ttl_seconds=300)
    hit = ctrl.get_from_cache("audio_tts", "hash_welcome_te")
    assert hit == b"synthetic_wav_data"
    assert ctrl.cache_hits == 1
    assert ctrl.estimated_savings_inr > 0.0

    summary = ctrl.get_cost_summary()
    assert summary["budget"]["status"] == "WITHIN_BUDGET"
    assert summary["caching"]["hit_rate_pct"] == 50.0
