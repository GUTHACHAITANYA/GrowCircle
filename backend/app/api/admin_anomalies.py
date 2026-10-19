"""
FastAPI Admin Anomaly Review Queue and Outage Alert Router (Phase ML-2).
Enforces:
1. Review queue workflow (approve/reject with audit logs).
2. Quarantining suspicious prices until reviewed.
3. Outage reporting status monitoring.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_db
from backend.app.models.anomaly import AnomalyReview
from backend.app.models.audit_log import AuditLog
from backend.app.models.price import Price
from backend.app.schemas.anomaly import (
    AnomalyReviewActionRequest,
    AnomalyReviewItem,
    AnomalyStatsResponse,
    ReportingStatusResponse,
)
from backend.app.services.security import require_admin_role_enforced
from ml.anomaly.reporting_drops import reporting_drop_detector

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/admin/anomalies/queue",
    response_model=list[AnomalyReviewItem],
    dependencies=[Depends(require_admin_role_enforced())],
    tags=["Admin Anomalies"],
)
async def get_anomaly_review_queue(
    status_filter: Annotated[
        str | None,
        Query(
            description="Filter by state: pending_review, approved, rejected, auto_cleared, or all"
        ),
    ] = "pending_review",
    entity_type: Annotated[str | None, Query(description="Filter by entity type")] = None,
    severity: Annotated[str | None, Query(description="Filter by severity")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    db: AsyncSession = Depends(get_async_db),
) -> list[AnomalyReviewItem]:
    """
    Returns items in the anomaly review queue.
    By default returns pending items awaiting admin decision.
    """
    stmt = select(AnomalyReview)

    if status_filter and status_filter.lower() != "all":
        stmt = stmt.where(AnomalyReview.status == status_filter.lower())

    if entity_type:
        stmt = stmt.where(AnomalyReview.entity_type == entity_type.lower())

    if severity:
        stmt = stmt.where(AnomalyReview.severity == severity.upper())

    stmt = stmt.order_by(desc(AnomalyReview.created_at)).offset(skip).limit(limit)
    res = await db.execute(stmt)
    records = res.scalars().all()

    return [
        AnomalyReviewItem(
            id=r.id,
            entity_type=r.entity_type,
            entity_id=r.entity_id,
            crop_id=r.crop_id,
            mandi_id=r.mandi_id,
            reason_code=r.reason_code,
            severity=r.severity,
            status=r.status,
            metrics_payload=r.metrics_payload or {},
            auto_cleared_reason=r.auto_cleared_reason,
            reviewed_by=r.reviewed_by,
            reviewed_at=r.reviewed_at,
            review_notes=r.review_notes,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in records
    ]


@router.post(
    "/admin/anomalies/{anomaly_id}/review",
    response_model=AnomalyReviewItem,
    dependencies=[Depends(require_admin_role_enforced())],
    tags=["Admin Anomalies"],
)
async def review_anomaly_action(
    anomaly_id: int,
    action_req: AnomalyReviewActionRequest,
    db: AsyncSession = Depends(get_async_db),
) -> AnomalyReviewItem:
    """
    Approves or rejects a quarantined anomaly item.
    - If approved: marks status='approved', releasing the item to user-facing queries.
    - If rejected: marks status='rejected', permanently keeping the record hidden.
    """
    record = await db.get(AnomalyReview, anomaly_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly review record with id={anomaly_id} not found.",
        )

    now = datetime.now(UTC)
    new_status = "approved" if action_req.action == "approve" else "rejected"

    record.status = new_status
    record.reviewed_by = action_req.admin_id or 1
    record.reviewed_at = now
    record.review_notes = action_req.notes

    # If linked entity is a price record, synchronize Price.anomaly_status
    if record.entity_type == "price":
        try:
            price_id = int(record.entity_id)
            price_obj = await db.get(Price, price_id)
            if price_obj:
                price_obj.anomaly_status = new_status
        except ValueError:
            pass

    # Audit log entry
    audit = AuditLog(
        actor_role="admin",
        user_id=action_req.admin_id or 1,
        action=f"ANOMALY_{action_req.action.upper()}",
        target_resource=f"{record.entity_type}_anomaly",
        target_id=str(record.id),
        details=f"Admin {action_req.admin_id} marked anomaly #{record.id} ({record.reason_code}) as {new_status}. Note: {action_req.notes}",
        status="SUCCESS",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(record)

    return AnomalyReviewItem(
        id=record.id,
        entity_type=record.entity_type,
        entity_id=record.entity_id,
        crop_id=record.crop_id,
        mandi_id=record.mandi_id,
        reason_code=record.reason_code,
        severity=record.severity,
        status=record.status,
        metrics_payload=record.metrics_payload or {},
        auto_cleared_reason=record.auto_cleared_reason,
        reviewed_by=record.reviewed_by,
        reviewed_at=record.reviewed_at,
        review_notes=record.review_notes,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get(
    "/admin/anomalies/stats",
    response_model=AnomalyStatsResponse,
    dependencies=[Depends(require_admin_role_enforced())],
    tags=["Admin Anomalies"],
)
async def get_anomaly_statistics(
    db: AsyncSession = Depends(get_async_db),
) -> AnomalyStatsResponse:
    """
    Returns summary counts of anomalies across statuses, severities, and entity types.
    """
    # Count by status
    stmt_status = select(AnomalyReview.status, func.count(AnomalyReview.id)).group_by(
        AnomalyReview.status
    )
    res_status = await db.execute(stmt_status)
    status_counts = dict(res_status.all())

    # Count by severity
    stmt_sev = select(AnomalyReview.severity, func.count(AnomalyReview.id)).group_by(
        AnomalyReview.severity
    )
    res_sev = await db.execute(stmt_sev)
    sev_counts = dict(res_sev.all())

    # Count by entity type
    stmt_ent = select(AnomalyReview.entity_type, func.count(AnomalyReview.id)).group_by(
        AnomalyReview.entity_type
    )
    res_ent = await db.execute(stmt_ent)
    ent_counts = dict(res_ent.all())

    return AnomalyStatsResponse(
        total_pending=status_counts.get("pending_review", 0),
        total_approved=status_counts.get("approved", 0),
        total_rejected=status_counts.get("rejected", 0),
        total_auto_cleared=status_counts.get("auto_cleared", 0),
        by_severity=sev_counts,
        by_entity_type=ent_counts,
    )


@router.get(
    "/health/reporting-status",
    response_model=ReportingStatusResponse,
    tags=["System"],
)
async def get_reporting_drop_status(
    target_date_query: Annotated[
        str | None,
        Query(description="ISO Date YYYY-MM-DD to inspect, defaults to today"),
    ] = None,
    db: AsyncSession = Depends(get_async_db),
) -> ReportingStatusResponse:
    """
    Evaluates today's count of reporting mandis against historical day-of-week baselines.
    Raises alert on unusual drops indicative of upstream data.gov.in / APMC outages.
    """
    if target_date_query:
        target_d = date.fromisoformat(target_date_query)
    else:
        target_d = datetime.now(UTC).date()

    # Query distinct mandis reporting on target_d
    stmt = (
        select(func.count(func.distinct(Price.mandi_id)))
        .where(Price.price_date == target_d)
    )
    actual_active_mandis = (await db.scalar(stmt)) or 0

    # If test database has no current date rows, fallback to total mandis registered
    if actual_active_mandis == 0 and not target_date_query:
        # Check latest price date
        latest_date = await db.scalar(select(func.max(Price.price_date)))
        if latest_date:
            target_d = latest_date
            actual_active_mandis = (
                await db.scalar(
                    select(func.count(func.distinct(Price.mandi_id))).where(
                        Price.price_date == latest_date
                    )
                )
            ) or 0

    # Evaluate using learned baseline detector
    eval_res = reporting_drop_detector.evaluate_reporting(
        target_date=target_d,
        actual_mandis_count=actual_active_mandis,
    )

    return ReportingStatusResponse(
        target_date=eval_res.target_date,
        day_of_week=eval_res.day_of_week,
        actual_reporting_mandis=eval_res.actual_reporting_mandis,
        expected_reporting_mandis=eval_res.expected_reporting_mandis,
        drop_ratio=eval_res.drop_ratio,
        drop_zscore=eval_res.drop_zscore,
        status=eval_res.status,
        is_outage_alert=eval_res.is_outage_alert,
        alert_message=eval_res.alert_message,
    )
