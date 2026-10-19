"""
Anomaly Review and Quarantine database model (Phase ML-2).
Quarantines suspicious prices, offers, deals, and reporting drops.
Enforces admin review workflow before unverified data reaches users.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class AnomalyReview(Base):
    __tablename__ = "anomaly_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Entity classification: 'price', 'offer', 'deal', 'listing', 'reporting_drop'
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Agricultural context
    crop_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    mandi_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    # Diagnostic metadata
    reason_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # Severity: 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # State: 'pending_review', 'approved', 'rejected', 'auto_cleared'
    status: Mapped[str] = mapped_column(
        String(30), default="pending_review", nullable=False, index=True
    )

    # Detailed metrics snapshot (actual vs expected, z-score, neighbor corroboration, etc.)
    metrics_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    auto_cleared_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Reviewer audit trail
    reviewed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
