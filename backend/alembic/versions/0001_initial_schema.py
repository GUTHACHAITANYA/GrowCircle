"""initial_schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-13 13:54:00.000000

"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Enable PostGIS extension if PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # 2. Crops table
    op.create_table(
        "crops",
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("name_en", sa.String(length=100), nullable=False),
        sa.Column("name_te", sa.String(length=100), nullable=False),
        sa.Column("name_hi", sa.String(length=100), nullable=False),
        sa.Column("name_gu", sa.String(length=100), nullable=False),
        sa.Column("icon", sa.String(length=50), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False, server_default="fruit"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_crops_id", "crops", ["id"])

    # 3. Mandis table
    op.create_table(
        "mandis",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("district", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(
                geometry_type="POINT", srid=4326, from_text="ST_GeomFromEWKT", name="geometry"
            ),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_mandis_name", "mandis", ["name"])
    op.create_index("ix_mandis_district", "mandis", ["district"])
    op.create_index("ix_mandis_state", "mandis", ["state"])

    # 4. Prices table
    op.create_table(
        "prices",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column(
            "mandi_id", sa.Integer(), sa.ForeignKey("mandis.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "crop_id",
            sa.String(length=50),
            sa.ForeignKey("crops.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("variety", sa.String(length=100), server_default="Other", nullable=False),
        sa.Column("grade", sa.String(length=50), server_default="FAQ", nullable=False),
        sa.Column("price_date", sa.Date(), nullable=False),
        sa.Column("min_price_quintal", sa.Float(), nullable=False),
        sa.Column("max_price_quintal", sa.Float(), nullable=False),
        sa.Column("modal_price_quintal", sa.Float(), nullable=False),
        sa.Column("min_price_kg", sa.Float(), nullable=False),
        sa.Column("max_price_kg", sa.Float(), nullable=False),
        sa.Column("modal_price_kg", sa.Float(), nullable=False),
        sa.Column("modal_price_ton", sa.Float(), nullable=False),
        sa.Column("arrival_tonnes", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("source", sa.String(length=50), server_default="data.gov.in", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "mandi_id",
            "crop_id",
            "variety",
            "grade",
            "price_date",
            name="uq_mandi_crop_variety_grade_date",
        ),
    )
    op.create_index("ix_prices_mandi_id", "prices", ["mandi_id"])
    op.create_index("ix_prices_crop_id", "prices", ["crop_id"])
    op.create_index("ix_prices_price_date", "prices", ["price_date"])

    # 5. Users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("language", sa.String(length=10), server_default="te", nullable=False),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("role", sa.String(length=50), server_default="consumer", nullable=False),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_users_phone", "users", ["phone"], unique=True)
    op.create_index("ix_users_district", "users", ["district"])

    # 6. Ingestion Logs table
    op.create_table(
        "ingestion_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("source", sa.String(length=50), server_default="data.gov.in", nullable=False),
        sa.Column(
            "fetch_timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("records_fetched", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_upserted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_failed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="success", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_ingestion_logs_fetch_timestamp", "ingestion_logs", ["fetch_timestamp"])


def downgrade() -> None:
    op.drop_table("ingestion_logs")
    op.drop_table("users")
    op.drop_table("prices")
    op.drop_table("mandis")
    op.drop_table("crops")
