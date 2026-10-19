"""
Integration Tests for Admin Anomaly Review Queue and Price Quarantine (Phase ML-2).
Verifies:
1. Quarantined unreviewed anomalies are excluded from public GET /prices.
2. Admin review queue lists pending items with diagnostic metrics.
3. Admin approval releases the quarantined price to public endpoints.
4. Admin rejection permanently suppresses the bad data.
5. Stats and reporting outage endpoints operate reliably.
"""

from __future__ import annotations

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.anomaly import AnomalyReview
from backend.app.models.mandi import Mandi
from backend.app.models.price import Price


@pytest.mark.asyncio
async def test_admin_anomalies_quarantine_and_approval_workflow(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    # 1. Seed a Mandi
    mandi = Mandi(
        id=101,
        name="Guntur Yard",
        district="Guntur",
        state="Andhra Pradesh",
        latitude=16.3067,
        longitude=80.4365,
    )
    db_session.add(mandi)
    await db_session.flush()

    # 2. Seed a clean price and an anomalous quarantined price
    clean_price = Price(
        mandi_id=101,
        crop_id="banana",
        variety="Robusta",
        grade="FAQ",
        price_date=date(2026, 10, 13),
        min_price_quintal=2000.0,
        max_price_quintal=3000.0,
        modal_price_quintal=2500.0,
        min_price_kg=20.0,
        max_price_kg=30.0,
        modal_price_kg=25.0,
        modal_price_ton=25000.0,
        arrival_tonnes=10.0,
        source="data.gov.in",
        anomaly_status="clean",
    )
    db_session.add(clean_price)

    quarantined_price = Price(
        mandi_id=101,
        crop_id="banana",
        variety="Grand Naine",
        grade="FAQ",
        price_date=date(2026, 10, 13),
        min_price_quintal=200000.0,
        max_price_quintal=300000.0,
        modal_price_quintal=250000.0,
        min_price_kg=2000.0,  # Extreme unit error: ₹2000/kg
        max_price_kg=3000.0,
        modal_price_kg=2500.0,
        modal_price_ton=2500000.0,
        arrival_tonnes=5.0,
        source="data.gov.in",
        anomaly_status="pending_review",
    )
    db_session.add(quarantined_price)
    await db_session.flush()

    # Create anomaly review queue record for the quarantined price
    anomaly_entry = AnomalyReview(
        entity_type="price",
        entity_id=str(quarantined_price.id),
        crop_id="banana",
        mandi_id="ap-guntur-01",
        reason_code="RULE_UNIT_ERROR",
        severity="CRITICAL",
        status="pending_review",
        metrics_payload={"modal_price_kg": 2500.0, "unit_thresh": 450.0},
    )
    db_session.add(anomaly_entry)
    await db_session.commit()

    # 3. Verify public GET /prices hides the quarantined anomalous price
    resp = await client.get("/prices?crop=banana")
    assert resp.status_code == 200
    prices = resp.json()
    # The quarantined price with variety "Grand Naine" must NOT be returned
    varieties = [p["variety"] for p in prices]
    assert "Grand Naine" not in varieties
    assert "Robusta" in varieties

    # 4. Verify Admin Queue lists the pending anomaly
    queue_resp = await client.get("/admin/anomalies/queue?status_filter=pending_review", headers=admin_headers)
    assert queue_resp.status_code == 200
    queue = queue_resp.json()
    assert len(queue) == 1
    assert queue[0]["id"] == anomaly_entry.id
    assert queue[0]["reason_code"] == "RULE_UNIT_ERROR"
    assert queue[0]["severity"] == "CRITICAL"

    # 5. Admin Approves the anomaly (e.g. verified special high-value organic lot)
    action_resp = await client.post(
        f"/admin/anomalies/{anomaly_entry.id}/review",
        json={"action": "approve", "notes": "Verified export grade lot by mandi officer.", "admin_id": 99},
        headers=admin_headers,
    )
    assert action_resp.status_code == 200
    updated_item = action_resp.json()
    assert updated_item["status"] == "approved"
    assert updated_item["reviewed_by"] == 99

    # 6. Public GET /prices NOW includes the approved record!
    resp_after = await client.get("/prices?crop=banana")
    assert resp_after.status_code == 200
    varieties_after = [p["variety"] for p in resp_after.json()]
    assert "Grand Naine" in varieties_after


@pytest.mark.asyncio
async def test_admin_anomalies_rejection_workflow(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    # Seed a Mandi
    mandi = Mandi(
        id=102,
        name="Madanapalle Yard",
        district="Chittoor",
        state="Andhra Pradesh",
        latitude=13.5500,
        longitude=78.5000,
    )
    db_session.add(mandi)
    await db_session.flush()

    # Seed a bad price
    bad_price = Price(
        mandi_id=102,
        crop_id="tomato",
        variety="Hybrid",
        grade="FAQ",
        price_date=date(2026, 10, 13),
        min_price_quintal=3500.0,
        max_price_quintal=2000.0,  # Inverted!
        modal_price_quintal=2500.0,
        min_price_kg=35.0,
        max_price_kg=20.0,
        modal_price_kg=25.0,
        modal_price_ton=25000.0,
        arrival_tonnes=10.0,
        source="data.gov.in",
        anomaly_status="pending_review",
    )
    db_session.add(bad_price)
    await db_session.flush()

    anomaly_entry = AnomalyReview(
        entity_type="price",
        entity_id=str(bad_price.id),
        crop_id="tomato",
        mandi_id="ap-madanapalle-01",
        reason_code="RULE_INVERTED_RANGE",
        severity="CRITICAL",
        status="pending_review",
        metrics_payload={"min": 35.0, "max": 20.0},
    )
    db_session.add(anomaly_entry)
    await db_session.commit()

    # Admin Rejects
    action_resp = await client.post(
        f"/admin/anomalies/{anomaly_entry.id}/review",
        json={"action": "reject", "notes": "Confirmed inverted range typo by mandi clerk.", "admin_id": 99},
        headers=admin_headers,
    )
    assert action_resp.status_code == 200
    updated_item = action_resp.json()
    assert updated_item["status"] == "rejected"

    # Public GET /prices must still be empty for tomato
    resp = await client.get("/prices?crop=tomato")
    assert resp.status_code == 200
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_admin_anomalies_stats_and_reporting_status(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    # Test Stats endpoint
    stats_resp = await client.get("/admin/anomalies/stats", headers=admin_headers)
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert "total_pending" in stats
    assert "total_approved" in stats
    assert "total_rejected" in stats
    assert "by_severity" in stats

    # Test Reporting Status endpoint
    rpt_resp = await client.get("/health/reporting-status?target_date_query=2026-10-13")
    assert rpt_resp.status_code == 200
    rpt_data = rpt_resp.json()
    assert rpt_data["target_date"] == "2026-10-13"
    assert "status" in rpt_data
    assert "is_outage_alert" in rpt_data
    assert "drop_ratio" in rpt_data
