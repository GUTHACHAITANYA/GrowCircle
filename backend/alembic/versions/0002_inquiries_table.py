"""inquiries_table

Revision ID: 0002_inquiries_table
Revises: 0001_initial_schema
Create Date: 2026-10-13 14:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_inquiries_table"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "inquiries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("intent", sa.String(length=50), nullable=False),
        sa.Column("crop_id", sa.String(length=50), nullable=True),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="te"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_inquiries_phone", "inquiries", ["phone"])


def downgrade() -> None:
    op.drop_index("ix_inquiries_phone", table_name="inquiries")
    op.drop_table("inquiries")
