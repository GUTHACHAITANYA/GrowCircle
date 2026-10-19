"""phase6_audit_and_dpdp

Revision ID: 0006_phase6_audit_and_dpdp
Revises: 0005_phase5_diary_and_consumer
Create Date: 2026-10-13 16:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_phase6_audit_and_dpdp"
down_revision: str | None = "0005_phase5_diary_and_consumer"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add DPDP fields to users table
    op.add_column("users", sa.Column("consent_version", sa.String(length=20), server_default="1.0", nullable=True))
    op.add_column("users", sa.Column("consent_purpose", sa.String(length=255), server_default="mandi_prices_and_marketplace", nullable=True))
    op.add_column("users", sa.Column("consent_withdrawn_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False))

    # 2. Audit Logs Table (OWASP Top 10 + DPDP Act audit trail)
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("actor_role", sa.String(length=50), server_default="anonymous", nullable=False),
        sa.Column("client_ip", sa.String(length=50), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_resource", sa.String(length=100), nullable=True),
        sa.Column("target_id", sa.String(length=100), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="SUCCESS", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_timestamp"), "audit_logs", ["timestamp"], unique=False)
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)

    # 3. Feedbacks Table (Pilot Kit voice & one-key feedback)
    op.create_table(
        "feedbacks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("channel", sa.String(length=20), server_default="web", nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=50), server_default="general", nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("voice_audio_url", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_feedbacks_user_id"), "feedbacks", ["user_id"], unique=False)
    op.create_index(op.f("ix_feedbacks_created_at"), "feedbacks", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_table("feedbacks")
    op.drop_table("audit_logs")
    op.drop_column("users", "is_deleted")
    op.drop_column("users", "consent_withdrawn_at")
    op.drop_column("users", "consent_purpose")
    op.drop_column("users", "consent_version")
