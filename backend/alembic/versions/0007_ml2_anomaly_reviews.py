"""ml2_anomaly_reviews

Revision ID: 0007_ml2_anomaly_reviews
Revises: 0006_phase6_audit_and_dpdp
Create Date: 2026-10-13 18:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_ml2_anomaly_reviews"
down_revision: str | None = "0006_phase6_audit_and_dpdp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add anomaly_status column to prices table
    op.add_column(
        "prices",
        sa.Column("anomaly_status", sa.String(length=30), server_default="clean", nullable=False),
    )
    op.create_index(op.f("ix_prices_anomaly_status"), "prices", ["anomaly_status"], unique=False)

    # 2. Create anomaly_reviews table
    op.create_table(
        "anomaly_reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=False),
        sa.Column("crop_id", sa.String(length=50), nullable=True),
        sa.Column("mandi_id", sa.String(length=50), nullable=True),
        sa.Column("reason_code", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="pending_review", nullable=False),
        sa.Column("metrics_payload", sa.JSON(), nullable=False),
        sa.Column("auto_cleared_reason", sa.String(length=255), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_anomaly_reviews_entity_type"), "anomaly_reviews", ["entity_type"], unique=False)
    op.create_index(op.f("ix_anomaly_reviews_entity_id"), "anomaly_reviews", ["entity_id"], unique=False)
    op.create_index(op.f("ix_anomaly_reviews_crop_id"), "anomaly_reviews", ["crop_id"], unique=False)
    op.create_index(op.f("ix_anomaly_reviews_mandi_id"), "anomaly_reviews", ["mandi_id"], unique=False)
    op.create_index(op.f("ix_anomaly_reviews_reason_code"), "anomaly_reviews", ["reason_code"], unique=False)
    op.create_index(op.f("ix_anomaly_reviews_severity"), "anomaly_reviews", ["severity"], unique=False)
    op.create_index(op.f("ix_anomaly_reviews_status"), "anomaly_reviews", ["status"], unique=False)
    op.create_index(op.f("ix_anomaly_reviews_created_at"), "anomaly_reviews", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_anomaly_reviews_created_at"), table_name="anomaly_reviews")
    op.drop_index(op.f("ix_anomaly_reviews_status"), table_name="anomaly_reviews")
    op.drop_index(op.f("ix_anomaly_reviews_severity"), table_name="anomaly_reviews")
    op.drop_index(op.f("ix_anomaly_reviews_reason_code"), table_name="anomaly_reviews")
    op.drop_index(op.f("ix_anomaly_reviews_mandi_id"), table_name="anomaly_reviews")
    op.drop_index(op.f("ix_anomaly_reviews_crop_id"), table_name="anomaly_reviews")
    op.drop_index(op.f("ix_anomaly_reviews_entity_id"), table_name="anomaly_reviews")
    op.drop_index(op.f("ix_anomaly_reviews_entity_type"), table_name="anomaly_reviews")
    op.drop_table("anomaly_reviews")

    op.drop_index(op.f("ix_prices_anomaly_status"), table_name="prices")
    op.drop_column("prices", "anomaly_status")
