"""phase5_diary_and_consumer

Revision ID: 0005_phase5_diary_and_consumer
Revises: 0004_transport_schema
Create Date: 2026-10-13 16:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_phase5_diary_and_consumer"
down_revision: str | None = "0004_transport_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Farm Seasons
    op.create_table(
        "farm_seasons",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("farmer_id", sa.Integer(), nullable=False),
        sa.Column("season_name", sa.String(length=100), nullable=False),
        sa.Column("crop_id", sa.String(length=50), nullable=False),
        sa.Column("area_acres", sa.Float(), nullable=False),
        sa.Column("soil_type", sa.String(length=100), nullable=True),
        sa.Column("planting_date", sa.Date(), nullable=False),
        sa.Column("harvest_date", sa.Date(), nullable=True),
        sa.Column("expected_yield_kg", sa.Float(), nullable=False),
        sa.Column("district", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["crop_id"], ["crops.id"]),
        sa.ForeignKeyConstraint(["farmer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_farm_seasons_farmer_id"), "farm_seasons", ["farmer_id"], unique=False)

    # 2. Farm Diary Entries
    op.create_table(
        "farm_diary_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("season_id", sa.Integer(), nullable=False),
        sa.Column("entry_type", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("amount_inr", sa.Float(), nullable=False),
        sa.Column("quantity_kg", sa.Float(), nullable=False),
        sa.Column("unit_price_inr", sa.Float(), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("voice_raw_text", sa.Text(), nullable=True),
        sa.Column("readback_confirmed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["season_id"], ["farm_seasons.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_farm_diary_entries_season_id"), "farm_diary_entries", ["season_id"], unique=False)

    # 3. Price Alerts
    op.create_table(
        "price_alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_phone", sa.String(length=20), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("telegram_chat_id", sa.String(length=50), nullable=True),
        sa.Column("crop_id", sa.String(length=50), nullable=False),
        sa.Column("district", sa.String(length=100), nullable=False),
        sa.Column("alert_type", sa.String(length=50), nullable=False),
        sa.Column("target_price_kg", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["crop_id"], ["crops.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_price_alerts_user_phone"), "price_alerts", ["user_phone"], unique=False)


def downgrade() -> None:
    op.drop_table("price_alerts")
    op.drop_table("farm_diary_entries")
    op.drop_table("farm_seasons")
