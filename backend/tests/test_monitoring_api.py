"""
FastAPI integration tests for ML-7 Post-Launch Monitoring API endpoints.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app


@pytest.mark.asyncio
async def test_get_monitoring_dashboard() -> None:
    """Verifies GET /monitoring/dashboard returns consolidated health report."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/monitoring/dashboard")
        assert res.status_code == 200
        data = res.json()
        assert "system_health" in data
        assert "forecast_health" in data
        assert "vision_health" in data
        assert "voice_agent_health" in data
        assert "active_release" in data
        assert "alerts_summary" in data
        assert "operating_cost" in data
        assert data["forecast_health"]["calibration_status"] in ["CALIBRATED", "UNDER_COVERAGE", "OVER_COVERAGE"]


@pytest.mark.asyncio
async def test_get_drift_report() -> None:
    """Verifies GET /monitoring/drift returns KS tests and PSI statistics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/monitoring/drift")
        assert res.status_code == 200
        data = res.json()
        assert "dataset_drift_detected" in data
        assert "drift_share" in data
        assert "prediction_drift" in data
        assert "feature_details" in data


@pytest.mark.asyncio
async def test_get_forecast_errors() -> None:
    """Verifies GET /monitoring/forecast-errors calculates MAE, sMAPE, and coverage."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/monitoring/forecast-errors")
        assert res.status_code == 200
        data = res.json()
        assert "mae" in data
        assert "smape_pct" in data
        assert "interval_coverage_pct" in data
        assert "per_crop_breakdown" in data


@pytest.mark.asyncio
async def test_alerts_lifecycle() -> None:
    """Verifies listing and acknowledging alerts."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Hit dashboard to populate any triggers
        await ac.get("/monitoring/dashboard")

        # 2. Get alerts
        res = await ac.get("/monitoring/alerts")
        assert res.status_code == 200
        alerts = res.json()
        assert isinstance(alerts, list)

        if len(alerts) > 0:
            target_id = alerts[0]["alert_id"]
            ack_res = await ac.post("/monitoring/alerts/acknowledge", json={"alert_id": target_id})
            assert ack_res.status_code == 200
            assert ack_res.json()["status"] == "acknowledged"


@pytest.mark.asyncio
async def test_feedback_report_and_review(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    """Verifies submitting 1-click error report, inspecting queue, and promoting to eval."""
    client.headers.update(admin_headers)
    # 1. Report incorrect answer
    rep_res = await client.post(
        "/monitoring/feedback/report-wrong",
        json={
            "user_id": "test-farmer-01",
            "channel": "ivr",
            "category": "price_error",
            "query_text": "Tenali tomato rate",
            "model_response": "₹45.0 per kg",
            "farmer_correction": "Mandi physical auction rate is ₹23.0 per kg",
        },
    )
    assert rep_res.status_code == 201
    data = rep_res.json()
    assert data["status"] == "queued_for_review"
    fb_id = data["feedback_id"]

    # 2. Check review queue
    q_res = await client.get("/monitoring/feedback/queue")
    assert q_res.status_code == 200
    queue = q_res.json()
    assert any(item["feedback_id"] == fb_id for item in queue)

    # 3. Review and promote to golden evaluation test set
    rev_res = await client.post(
        f"/monitoring/feedback/{fb_id}/review",
        json={
            "action": "promote_to_eval",
            "reviewer_notes": "Ground truth verified from Tenali physical market slip",
        },
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["status"] == "promoted_to_eval"

    # 4. Check promoted cases
    cases_res = await client.get("/monitoring/feedback/eval-cases")
    assert cases_res.status_code == 200
    cases = cases_res.json()
    assert any(c["category"] == "price_error" for c in cases)


@pytest.mark.asyncio
async def test_release_deployment_and_rollback_api(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    """Verifies deploying canary model and triggering automated/manual rollback."""
    client.headers.update(admin_headers)
    # 1. Deploy canary
    dep_res = await client.post(
        "/monitoring/release/deploy",
        json={
            "candidate_version": "v1.2-canary",
            "mode": "canary",
            "canary_percentage": 15,
            "data_hash": "sha256-hash-test-dataset",
        },
    )
    assert dep_res.status_code == 200
    assert dep_res.json()["stage"] == "CANARY"

    # 2. Check status
    st_res = await client.get("/monitoring/release/status")
    assert st_res.status_code == 200
    assert st_res.json()["candidate_version"] == "v1.2-canary"
    assert st_res.json()["canary_percentage"] == 15

    # 3. Trigger rollback
    rb_res = await client.post(
        "/monitoring/release/rollback",
        json={"reason": "Drift guardrail trigger in integration test"},
    )
    assert rb_res.status_code == 200
    assert rb_res.json()["status"] == "rolled_back"
    assert rb_res.json()["stage"] == "ROLLEDBACK"


@pytest.mark.asyncio
async def test_cost_metrics_and_record_call() -> None:
    """Verifies operating cost recording and budget telemetry."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Record call usage
        rec_res = await ac.post(
            "/monitoring/cost/record-call",
            json={
                "duration_seconds": 60.0,
                "stt_audio_seconds": 20.0,
                "tts_audio_seconds": 35.0,
                "llm_prompt_tokens": 300,
                "llm_completion_tokens": 120,
            },
        )
        assert rec_res.status_code == 200
        assert rec_res.json()["turn_cost_inr"] > 0.0

        # 2. Get cost summary
        cost_res = await ac.get("/monitoring/cost")
        assert cost_res.status_code == 200
        cdata = cost_res.json()
        assert "total_spend_inr" in cdata
        assert "breakdown_inr" in cdata
        assert "budget" in cdata
        assert "caching" in cdata
