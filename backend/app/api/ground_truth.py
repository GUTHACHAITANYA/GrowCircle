"""
Ground-truth validation API handlers:
Record phone audits, CSV import/export, and discrepancy reports.
"""

import csv
import io
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_db
from backend.app.models.crop import Crop
from backend.app.models.ground_truth import GroundTruthCheck
from backend.app.models.mandi import Mandi
from backend.app.models.price import Price
from backend.app.schemas.ground_truth import (
    GroundTruthCheckCreate,
    GroundTruthCheckOut,
    GroundTruthReportOut,
    MandiAccuracyMetric,
)
from backend.app.services.security import require_admin_role_enforced

router = APIRouter(
    prefix="/admin/ground-truth",
    tags=["Ground Truth Validation"],
    dependencies=[Depends(require_admin_role_enforced(require_2fa=False))],
)


@router.post("", response_model=GroundTruthCheckOut, status_code=status.HTTP_201_CREATED)
async def record_ground_truth_check(
    payload: GroundTruthCheckCreate,
    db: AsyncSession = Depends(get_async_db),
) -> GroundTruthCheckOut:
    """
    Records a manual phone check conducted with a mandi secretary or trader.
    Automatically reconciles against the price GrowCircle displayed on that check_date.
    """
    mandi = await db.get(Mandi, payload.mandi_id)
    if not mandi:
        raise HTTPException(status_code=404, detail=f"Mandi ID {payload.mandi_id} not found.")

    # 1. Lookup price GrowCircle displayed on check_date
    shown_price_row = await db.scalar(
        select(Price)
        .where(
            Price.mandi_id == payload.mandi_id,
            Price.crop_id == payload.crop_id.lower().strip(),
            Price.price_date <= payload.check_date,
            Price.anomaly_status.in_(["clean", "approved", "auto_cleared"]),
        )
        .order_by(desc(Price.price_date))
        .limit(1)
    )

    is_missing = False
    is_late = False
    price_shown_kg = payload.price_shown_kg

    if shown_price_row:
        if price_shown_kg is None:
            price_shown_kg = shown_price_row.modal_price_kg
        # If the latest recorded price in our DB was older than check_date by > 1 day
        if (payload.check_date - shown_price_row.price_date).days > 1:
            is_late = True
    else:
        is_missing = True
        price_shown_kg = None

    diff_kg = None
    diff_pct = None
    if price_shown_kg is not None and payload.price_quoted_kg > 0:
        diff_kg = round(price_shown_kg - payload.price_quoted_kg, 2)
        diff_pct = round((diff_kg / payload.price_quoted_kg) * 100.0, 2)

    check = GroundTruthCheck(
        mandi_id=payload.mandi_id,
        crop_id=payload.crop_id.lower().strip(),
        variety=payload.variety.strip(),
        grade=payload.grade.strip(),
        check_date=payload.check_date,
        price_shown_kg=price_shown_kg,
        price_quoted_kg=round(payload.price_quoted_kg, 2),
        contact_name=payload.contact_name,
        contact_role=payload.contact_role,
        contact_phone=payload.contact_phone,
        difference_kg=diff_kg,
        difference_pct=diff_pct,
        is_price_missing=is_missing,
        is_price_late=is_late,
        notes=payload.notes,
    )
    db.add(check)
    await db.commit()
    await db.refresh(check)

    return GroundTruthCheckOut(
        id=check.id,
        mandi_id=check.mandi_id,
        mandi_name=mandi.name,
        crop_id=check.crop_id,
        variety=check.variety,
        grade=check.grade,
        check_date=check.check_date,
        price_shown_kg=check.price_shown_kg,
        price_quoted_kg=check.price_quoted_kg,
        difference_kg=check.difference_kg,
        difference_pct=check.difference_pct,
        is_price_missing=check.is_price_missing,
        is_price_late=check.is_price_late,
        contact_name=check.contact_name,
        contact_role=check.contact_role,
        notes=check.notes,
        created_at=check.created_at,
    )


@router.get("/template.csv")
async def download_csv_template() -> Response:
    """Returns downloadable CSV template for recording manual mandi phone audits."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "mandi_id",
        "mandi_name",
        "crop_id",
        "variety",
        "grade",
        "check_date",
        "price_quoted_kg",
        "contact_role",
        "contact_name",
        "contact_phone",
        "notes",
    ])
    # Sample row for guidance
    writer.writerow([
        "1",
        "Guntur Mandi",
        "banana",
        "Amruthapani",
        "FAQ",
        datetime.now(UTC).date().isoformat(),
        "24.5",
        "secretary",
        "Sri Rama Rao (Secretary)",
        "+919848011223",
        "Morning auction price confirmed via phone",
    ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ground_truth_check_template.csv"},
    )


@router.post("/upload-csv")
async def upload_ground_truth_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Uploads and ingests a bulk batch of phone check records from CSV."""
    content = await file.read()
    decoded = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded))

    created_count = 0
    errors: list[str] = []

    for idx, row in enumerate(reader, start=2):
        try:
            mandi_id = int(row["mandi_id"].strip())
            crop_id = row.get("crop_id", "banana").strip().lower()
            variety = row.get("variety", "Other").strip()
            grade = row.get("grade", "FAQ").strip()
            check_date_val = datetime.strptime(row["check_date"].strip(), "%Y-%m-%d").date()
            price_quoted = float(row["price_quoted_kg"].strip())

            payload = GroundTruthCheckCreate(
                mandi_id=mandi_id,
                crop_id=crop_id,
                variety=variety,
                grade=grade,
                check_date=check_date_val,
                price_quoted_kg=price_quoted,
                contact_role=row.get("contact_role", "secretary").strip(),
                contact_name=row.get("contact_name", "").strip() or None,
                contact_phone=row.get("contact_phone", "").strip() or None,
                notes=row.get("notes", "").strip() or None,
            )
            await record_ground_truth_check(payload, db)
            created_count += 1
        except Exception as ex:
            errors.append(f"Row {idx}: {ex}")

    return {
        "status": "success",
        "records_imported": created_count,
        "errors_count": len(errors),
        "errors": errors[:10],
    }


@router.get("/report", response_model=GroundTruthReportOut)
async def get_ground_truth_report(
    db: AsyncSession = Depends(get_async_db),
) -> GroundTruthReportOut:
    """
    Computes statistical evaluation metrics on manual phone checks vs displayed prices:
    - Average difference (₹/kg and %)
    - Missing price count and rate
    - Late price count and rate (>24h stale)
    - Verified match rate (within ±5% range)
    """
    checks = (await db.execute(select(GroundTruthCheck))).scalars().all()
    total = len(checks)

    if total == 0:
        return GroundTruthReportOut(
            total_checks=0,
            avg_diff_kg=0.0,
            avg_diff_pct=0.0,
            missing_price_count=0,
            missing_price_rate_pct=0.0,
            late_price_count=0,
            late_price_rate_pct=0.0,
            verified_match_rate_pct=0.0,
            mandi_breakdown=[],
        )

    diffs_kg = [abs(c.difference_kg) for c in checks if c.difference_kg is not None]
    diffs_pct = [abs(c.difference_pct) for c in checks if c.difference_pct is not None]
    missing_cnt = sum(1 for c in checks if c.is_price_missing)
    late_cnt = sum(1 for c in checks if c.is_price_late)
    matches_cnt = sum(1 for c in checks if c.difference_pct is not None and abs(c.difference_pct) <= 5.0)

    avg_kg = round(sum(diffs_kg) / len(diffs_kg), 2) if diffs_kg else 0.0
    avg_pct = round(sum(diffs_pct) / len(diffs_pct), 2) if diffs_pct else 0.0

    # Per-mandi breakdown
    mandi_groups: dict[int, list[GroundTruthCheck]] = {}
    for c in checks:
        mandi_groups.setdefault(c.mandi_id, []).append(c)

    breakdown: list[MandiAccuracyMetric] = []
    for m_id, m_checks in mandi_groups.items():
        m_row = await db.get(Mandi, m_id)
        m_name = m_row.name if m_row else f"Mandi #{m_id}"
        m_pcts = [abs(c.difference_pct) for c in m_checks if c.difference_pct is not None]
        breakdown.append(
            MandiAccuracyMetric(
                mandi_name=m_name,
                checks_count=len(m_checks),
                avg_diff_pct=round(sum(m_pcts) / len(m_pcts), 2) if m_pcts else 0.0,
                missing_count=sum(1 for c in m_checks if c.is_price_missing),
                late_count=sum(1 for c in m_checks if c.is_price_late),
            )
        )

    return GroundTruthReportOut(
        total_checks=total,
        avg_diff_kg=avg_kg,
        avg_diff_pct=avg_pct,
        missing_price_count=missing_cnt,
        missing_price_rate_pct=round((missing_cnt / total) * 100.0, 1),
        late_price_count=late_cnt,
        late_price_rate_pct=round((late_cnt / total) * 100.0, 1),
        verified_match_rate_pct=round((matches_cnt / total) * 100.0, 1),
        mandi_breakdown=breakdown,
    )


@router.get("", response_model=list[GroundTruthCheckOut])
async def list_ground_truth_checks(
    limit: int = 50,
    db: AsyncSession = Depends(get_async_db),
) -> list[GroundTruthCheckOut]:
    """Lists recent ground truth phone verification logs."""
    stmt = (
        select(GroundTruthCheck, Mandi)
        .join(Mandi, GroundTruthCheck.mandi_id == Mandi.id)
        .order_by(desc(GroundTruthCheck.created_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    records: list[GroundTruthCheckOut] = []

    for check, mandi in result.all():
        records.append(
            GroundTruthCheckOut(
                id=check.id,
                mandi_id=check.mandi_id,
                mandi_name=mandi.name,
                crop_id=check.crop_id,
                variety=check.variety,
                grade=check.grade,
                check_date=check.check_date,
                price_shown_kg=check.price_shown_kg,
                price_quoted_kg=check.price_quoted_kg,
                difference_kg=check.difference_kg,
                difference_pct=check.difference_pct,
                is_price_missing=check.is_price_missing,
                is_price_late=check.is_price_late,
                contact_name=check.contact_name,
                contact_role=check.contact_role,
                notes=check.notes,
                created_at=check.created_at,
            )
        )

    return records
