"""assistance reviews, job messages, regulated skill verification

Revision ID: 008
Revises: 007
Create Date: 2026-11-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "service_categories",
        sa.Column("requires_verification", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.execute(
        "UPDATE service_categories SET requires_verification = true WHERE slug IN ('plumbing', 'electrical')"
    )

    op.add_column(
        "portfolio_service_categories",
        sa.Column("verification_status", sa.String(24), server_default="not_required", nullable=False),
    )
    op.add_column("portfolio_service_categories", sa.Column("admin_note", sa.Text(), nullable=True))
    op.add_column("portfolio_service_categories", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "portfolio_service_categories",
        sa.Column(
            "reviewed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.execute(
        "UPDATE portfolio_service_categories psc SET verification_status = 'approved' "
        "FROM service_categories sc WHERE sc.id = psc.category_id AND sc.requires_verification = true"
    )

    op.create_table(
        "assistance_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "service_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_assistance_reviews_rating"),
    )
    op.create_index("ix_assistance_reviews_service_job_id", "assistance_reviews", ["service_job_id"], unique=True)
    op.create_index("ix_assistance_reviews_provider_id", "assistance_reviews", ["provider_id"])

    op.create_table(
        "service_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "service_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_service_conversations_service_job_id", "service_conversations", ["service_job_id"], unique=True)

    op.create_table(
        "service_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_service_messages_conversation_id", "service_messages", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("ix_service_messages_conversation_id", table_name="service_messages")
    op.drop_table("service_messages")
    op.drop_index("ix_service_conversations_service_job_id", table_name="service_conversations")
    op.drop_table("service_conversations")
    op.drop_index("ix_assistance_reviews_provider_id", table_name="assistance_reviews")
    op.drop_index("ix_assistance_reviews_service_job_id", table_name="assistance_reviews")
    op.drop_table("assistance_reviews")
    op.drop_column("portfolio_service_categories", "reviewed_by")
    op.drop_column("portfolio_service_categories", "reviewed_at")
    op.drop_column("portfolio_service_categories", "admin_note")
    op.drop_column("portfolio_service_categories", "verification_status")
    op.drop_column("service_categories", "requires_verification")