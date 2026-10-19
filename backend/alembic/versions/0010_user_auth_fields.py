"""user_auth_fields

Revision ID: 0010_user_auth_fields
Revises: 0009_r2_mandi_master_and_lgd_hierarchy
Create Date: 2026-10-19 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010_user_auth_fields"
down_revision: str | None = "0009_r2_mandi_master_and_lgd_hierarchy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Safely add auth, security, and profile columns to users table
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {col["name"] for col in inspector.get_columns("users")}

    if "name" not in existing_cols:
        op.add_column("users", sa.Column("name", sa.String(length=100), nullable=True))
    if "session_version" not in existing_cols:
        op.add_column(
            "users",
            sa.Column("session_version", sa.Integer(), server_default="1", nullable=False),
        )
    if "is_admin_2fa_verified" not in existing_cols:
        op.add_column(
            "users",
            sa.Column(
                "is_admin_2fa_verified",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=False,
            ),
        )
    if "failed_otp_attempts" not in existing_cols:
        op.add_column(
            "users",
            sa.Column(
                "failed_otp_attempts",
                sa.Integer(),
                server_default="0",
                nullable=False,
            ),
        )
    if "locked_until" not in existing_cols:
        op.add_column(
            "users",
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_otp_attempts")
    op.drop_column("users", "is_admin_2fa_verified")
    op.drop_column("users", "session_version")
    op.drop_column("users", "name")
