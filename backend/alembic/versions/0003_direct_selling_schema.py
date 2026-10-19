"""direct_selling_schema

Revision ID: 0003_direct_selling_schema
Revises: 0002_inquiries_table
Create Date: 2026-10-13 15:00:00.000000

"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_direct_selling_schema"
down_revision: str | None = "0002_inquiries_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Buyer Profiles
    op.create_table(
        "buyer_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("business_name", sa.String(length=200), nullable=False),
        sa.Column("business_type", sa.String(length=50), nullable=False),
        sa.Column("verification_status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("encrypted_gst_number", sa.Text(), nullable=True),
        sa.Column("encrypted_document_ref", sa.Text(), nullable=True),
        sa.Column("verification_notes", sa.Text(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by_admin_id", sa.Integer(), nullable=True),
        sa.Column("reliability_score", sa.Float(), server_default="5.0", nullable=False),
        sa.Column("deals_completed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("address", sa.String(length=300), nullable=False),
        sa.Column("district", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=100), server_default="Andhra Pradesh", nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326, from_text="ST_GeomFromEWKT", name="geometry"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_buyer_profiles_user_id", "buyer_profiles", ["user_id"])
    op.create_index("ix_buyer_profiles_district", "buyer_profiles", ["district"])
    op.create_index("ix_buyer_profiles_verification_status", "buyer_profiles", ["verification_status"])

    # 2. Buyer Needs
    op.create_table(
        "buyer_needs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("buyer_id", sa.Integer(), sa.ForeignKey("buyer_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("crop_id", sa.String(length=50), sa.ForeignKey("crops.id"), nullable=False),
        sa.Column("quantity_kg", sa.Float(), nullable=False),
        sa.Column("frequency", sa.String(length=20), server_default="weekly", nullable=False),
        sa.Column("preferred_grade", sa.String(length=10), server_default="any", nullable=False),
        sa.Column("target_price_kg", sa.Float(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("district", sa.String(length=100), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326, from_text="ST_GeomFromEWKT", name="geometry"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_buyer_needs_buyer_id", "buyer_needs", ["buyer_id"])
    op.create_index("ix_buyer_needs_crop_id", "buyer_needs", ["crop_id"])

    # 3. Farmer Listings
    op.create_table(
        "listings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("farmer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("crop_id", sa.String(length=50), sa.ForeignKey("crops.id"), nullable=False),
        sa.Column("variety", sa.String(length=100), nullable=False),
        sa.Column("quantity_kg", sa.Float(), nullable=False),
        sa.Column("grade", sa.String(length=5), nullable=False),
        sa.Column("harvest_date", sa.Date(), nullable=False),
        sa.Column("expected_price_kg", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("media_checklist", sa.JSON(), nullable=False),
        sa.Column("media_captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("media_latitude", sa.Float(), nullable=True),
        sa.Column("media_longitude", sa.Float(), nullable=True),
        sa.Column("district", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=100), server_default="Andhra Pradesh", nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326, from_text="ST_GeomFromEWKT", name="geometry"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_listings_farmer_id", "listings", ["farmer_id"])
    op.create_index("ix_listings_crop_id", "listings", ["crop_id"])
    op.create_index("ix_listings_district", "listings", ["district"])
    op.create_index("ix_listings_status", "listings", ["status"])

    # 4. Offers
    op.create_table(
        "offers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("listing_id", sa.Integer(), sa.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("buyer_id", sa.Integer(), sa.ForeignKey("buyer_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("buyer_need_id", sa.Integer(), nullable=True),
        sa.Column("offered_price_kg", sa.Float(), nullable=False),
        sa.Column("quantity_kg", sa.Float(), nullable=False),
        sa.Column("counter_price_kg", sa.Float(), nullable=True),
        sa.Column("counter_by", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_offers_listing_id", "offers", ["listing_id"])
    op.create_index("ix_offers_buyer_id", "offers", ["buyer_id"])

    # 5. Deals
    op.create_table(
        "deals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("offer_id", sa.Integer(), sa.ForeignKey("offers.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("listing_id", sa.Integer(), sa.ForeignKey("listings.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("buyer_id", sa.Integer(), sa.ForeignKey("buyer_profiles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("farmer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("agreed_price_kg", sa.Float(), nullable=False),
        sa.Column("quantity_kg", sa.Float(), nullable=False),
        sa.Column("total_reference_value", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="confirmed", nullable=False),
        sa.Column("pickup_otp", sa.String(length=6), nullable=False),
        sa.Column("deal_date", sa.Date(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_deals_listing_id", "deals", ["listing_id"])
    op.create_index("ix_deals_buyer_id", "deals", ["buyer_id"])
    op.create_index("ix_deals_farmer_id", "deals", ["farmer_id"])

    # 6. Ratings
    op.create_table(
        "ratings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("deal_id", sa.Integer(), sa.ForeignKey("deals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rater_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ratee_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("reliability_tag", sa.String(length=50), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ratings_deal_id", "ratings", ["deal_id"])


def downgrade() -> None:
    op.drop_table("ratings")
    op.drop_table("deals")
    op.drop_table("offers")
    op.drop_table("listings")
    op.drop_table("buyer_needs")
    op.drop_table("buyer_profiles")
