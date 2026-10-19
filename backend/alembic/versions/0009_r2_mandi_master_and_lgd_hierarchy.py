"""r2_mandi_master_and_lgd_hierarchy

Revision ID: 0009_r2_mandi_master_and_lgd_hierarchy
Revises: 0008_r1_real_price_sources_and_ground_truth
Create Date: 2026-10-15 10:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_r2_mandi_master_and_lgd_hierarchy"
down_revision: str | None = "0008_r1_real_price_sources_and_ground_truth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create states_master table
    op.create_table(
        "states_master",
        sa.Column("id", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("lgd_code", sa.Integer(), nullable=True),
        sa.Column("min_lat", sa.Float(), nullable=False),
        sa.Column("max_lat", sa.Float(), nullable=False),
        sa.Column("min_lon", sa.Float(), nullable=False),
        sa.Column("max_lon", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("lgd_code"),
    )

    # 2. Create districts_master table
    op.create_table(
        "districts_master",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("state_id", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("lgd_code", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["state_id"], ["states_master.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_districts_master_name"), "districts_master", ["name"], unique=False)
    op.create_index(op.f("ix_districts_master_state_id"), "districts_master", ["state_id"], unique=False)

    # 3. Create mandals_master table
    op.create_table(
        "mandals_master",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("district_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("lgd_code", sa.Integer(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["district_id"], ["districts_master.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mandals_master_district_id"), "mandals_master", ["district_id"], unique=False)
    op.create_index(op.f("ix_mandals_master_name"), "mandals_master", ["name"], unique=False)

    # 4. Add columns to mandis table
    with op.batch_alter_table("mandis") as batch_op:
        batch_op.add_column(sa.Column("canonical_name", sa.String(length=150), server_default="", nullable=False))
        batch_op.add_column(sa.Column("mandal", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("state_id", sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column("district_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("mandal_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("state_lgd_code", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("district_lgd_code", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("mandal_lgd_code", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("location_verified", sa.Boolean(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("geocode_confidence", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("geocode_source", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("needs_review", sa.Boolean(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("review_reason", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("merged_into_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("mandis") as batch_op:
        batch_op.drop_column("merged_into_id")
        batch_op.drop_column("review_reason")
        batch_op.drop_column("needs_review")
        batch_op.drop_column("geocode_source")
        batch_op.drop_column("geocode_confidence")
        batch_op.drop_column("location_verified")
        batch_op.drop_column("mandal_lgd_code")
        batch_op.drop_column("district_lgd_code")
        batch_op.drop_column("state_lgd_code")
        batch_op.drop_column("mandal_id")
        batch_op.drop_column("district_id")
        batch_op.drop_column("state_id")
        batch_op.drop_column("mandal")
        batch_op.drop_column("canonical_name")

    op.drop_table("mandals_master")
    op.drop_table("districts_master")
    op.drop_table("states_master")
