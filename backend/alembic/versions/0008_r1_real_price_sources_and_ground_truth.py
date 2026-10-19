"""r1_real_price_sources_and_ground_truth

Revision ID: 0008_r1_real_price_sources_and_ground_truth
Revises: 0007_ml2_anomaly_reviews
Create Date: 2026-10-15 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008_r1_real_price_sources_and_ground_truth"
down_revision: str | None = "0007_ml2_anomaly_reviews"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add original units, raw reference, and fetched_at to prices table
    op.add_column(
        "prices",
        sa.Column("original_unit", sa.String(length=30), server_default="quintal", nullable=False),
    )
    op.add_column(
        "prices",
        sa.Column("original_min_price", sa.Float(), server_default="0.0", nullable=False),
    )
    op.add_column(
        "prices",
        sa.Column("original_max_price", sa.Float(), server_default="0.0", nullable=False),
    )
    op.add_column(
        "prices",
        sa.Column("original_modal_price", sa.Float(), server_default="0.0", nullable=False),
    )
    op.add_column(
        "prices",
        sa.Column("raw_payload_ref", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "prices",
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    # 2. Create ground_truth_checks table
    op.create_table(
        "ground_truth_checks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("mandi_id", sa.Integer(), nullable=False),
        sa.Column("crop_id", sa.String(length=50), nullable=False),
        sa.Column("variety", sa.String(length=100), server_default="Other", nullable=False),
        sa.Column("grade", sa.String(length=50), server_default="FAQ", nullable=False),
        sa.Column("check_date", sa.Date(), nullable=False),
        sa.Column("price_shown_kg", sa.Float(), nullable=True),
        sa.Column("price_quoted_kg", sa.Float(), nullable=False),
        sa.Column("contact_name", sa.String(length=150), nullable=True),
        sa.Column("contact_role", sa.String(length=50), server_default="secretary", nullable=False),
        sa.Column("contact_phone", sa.String(length=30), nullable=True),
        sa.Column("difference_kg", sa.Float(), nullable=True),
        sa.Column("difference_pct", sa.Float(), nullable=True),
        sa.Column("is_price_missing", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("is_price_late", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["crop_id"], ["crops.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mandi_id"], ["mandis.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ground_truth_checks_check_date"),
        "ground_truth_checks",
        ["check_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ground_truth_checks_crop_id"),
        "ground_truth_checks",
        ["crop_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ground_truth_checks_mandi_id"),
        "ground_truth_checks",
        ["mandi_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("ground_truth_checks")
    op.drop_column("prices", "fetched_at")
    op.drop_column("prices", "raw_payload_ref")
    op.drop_column("prices", "original_modal_price")
    op.drop_column("prices", "original_max_price")
    op.drop_column("prices", "original_min_price")
    op.drop_column("prices", "original_unit")
