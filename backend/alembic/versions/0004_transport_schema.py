"""transport_schema

Revision ID: 0004_transport_schema
Revises: 0003_direct_selling_schema
Create Date: 2026-10-13 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_transport_schema"
down_revision: str | None = "0003_direct_selling_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Transporters
    op.create_table(
        "transporters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("license_number", sa.String(length=50), nullable=False),
        sa.Column("license_expiry", sa.Date(), nullable=False),
        sa.Column("license_photo_url", sa.String(length=255), nullable=False),
        sa.Column("rc_number", sa.String(length=50), nullable=False),
        sa.Column("rc_expiry", sa.Date(), nullable=False),
        sa.Column("rc_photo_url", sa.String(length=255), nullable=False),
        sa.Column("insurance_expiry", sa.Date(), nullable=False),
        sa.Column("insurance_photo_url", sa.String(length=255), nullable=True),
        sa.Column("fitness_expiry", sa.Date(), nullable=False),
        sa.Column("fitness_photo_url", sa.String(length=255), nullable=True),
        sa.Column("vehicle_type", sa.String(length=30), nullable=False),
        sa.Column("vehicle_model", sa.String(length=50), nullable=False),
        sa.Column("capacity_kg", sa.Integer(), nullable=False),
        sa.Column(
            "service_area_districts",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("current_latitude", sa.Float(), nullable=False),
        sa.Column("current_longitude", sa.Float(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("available_today", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("reliability_rating", sa.Float(), server_default=sa.text("5.0"), nullable=False),
        sa.Column("trips_completed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transporters_user_id", "transporters", ["user_id"])
    op.create_index("ix_transporters_phone", "transporters", ["phone"])
    op.create_index("ix_transporters_vehicle_type", "transporters", ["vehicle_type"])
    op.create_index("ix_transporters_is_verified", "transporters", ["is_verified"])
    op.create_index("ix_transporters_available_today", "transporters", ["available_today"])
    op.create_index("ix_transporters_license_expiry", "transporters", ["license_expiry"])
    op.create_index("ix_transporters_rc_expiry", "transporters", ["rc_expiry"])
    op.create_index("ix_transporters_insurance_expiry", "transporters", ["insurance_expiry"])
    op.create_index("ix_transporters_fitness_expiry", "transporters", ["fitness_expiry"])

    # 2. Trips
    op.create_table(
        "trips",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("transporter_id", sa.Integer(), nullable=False),
        sa.Column("deal_id", sa.Integer(), nullable=True),
        sa.Column(
            "deal_ids",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=30), server_default="assigned", nullable=False),
        sa.Column("vehicle_type", sa.String(length=30), nullable=False),
        sa.Column("total_weight_kg", sa.Float(), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("guide_rate", sa.Float(), nullable=False),
        sa.Column("actual_freight_agreed", sa.Float(), nullable=True),
        sa.Column("pickup_otp", sa.String(length=6), nullable=False),
        sa.Column("pickup_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_otp", sa.String(length=6), nullable=False),
        sa.Column("delivery_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_photo_url", sa.String(length=255), nullable=True),
        sa.Column("buyer_dispute_reason", sa.Text(), nullable=True),
        sa.Column("buyer_dispute_photo_url", sa.String(length=255), nullable=True),
        sa.Column("dispute_resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispute_resolution_notes", sa.Text(), nullable=True),
        sa.Column("pickup_latitude", sa.Float(), nullable=False),
        sa.Column("pickup_longitude", sa.Float(), nullable=False),
        sa.Column("pickup_address", sa.String(length=255), nullable=True),
        sa.Column("dropoff_latitude", sa.Float(), nullable=False),
        sa.Column("dropoff_longitude", sa.Float(), nullable=False),
        sa.Column("dropoff_address", sa.String(length=255), nullable=True),
        sa.Column("is_pooled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["transporter_id"], ["transporters.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trips_transporter_id", "trips", ["transporter_id"])
    op.create_index("ix_trips_deal_id", "trips", ["deal_id"])
    op.create_index("ix_trips_status", "trips", ["status"])
    op.create_index("ix_trips_is_pooled", "trips", ["is_pooled"])

    # 3. Trip Ratings
    op.create_table(
        "trip_ratings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("trip_id", sa.Integer(), nullable=False),
        sa.Column("rater_id", sa.Integer(), nullable=False),
        sa.Column("ratee_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("tag", sa.String(length=50), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rater_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ratee_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trip_ratings_trip_id", "trip_ratings", ["trip_id"])
    op.create_index("ix_trip_ratings_rater_id", "trip_ratings", ["rater_id"])
    op.create_index("ix_trip_ratings_ratee_id", "trip_ratings", ["ratee_id"])


def downgrade() -> None:
    op.drop_table("trip_ratings")
    op.drop_table("trips")
    op.drop_table("transporters")
