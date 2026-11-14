"""service job payments and progress timeline

Revision ID: 007
Revises: 006
Create Date: 2026-11-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("payments", "rental_booking_id", existing_type=postgresql.UUID(), nullable=True)
    op.add_column(
        "payments",
        sa.Column(
            "service_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_jobs.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index("ix_payments_service_job_id", "payments", ["service_job_id"], unique=False)
    op.create_check_constraint(
        "ck_payments_subject",
        "payments",
        "(rental_booking_id IS NOT NULL AND service_job_id IS NULL) OR "
        "(rental_booking_id IS NULL AND service_job_id IS NOT NULL)",
    )

    op.add_column("service_jobs", sa.Column("hold_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("service_jobs", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("service_jobs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "service_job_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(48), nullable=False),
        sa.Column("summary", sa.String(255), nullable=False),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_service_job_events_job_id", "service_job_events", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_service_job_events_job_id", table_name="service_job_events")
    op.drop_table("service_job_events")
    op.drop_column("service_jobs", "started_at")
    op.drop_column("service_jobs", "paid_at")
    op.drop_column("service_jobs", "hold_expires_at")
    op.drop_constraint("ck_payments_subject", "payments", type_="check")
    op.drop_index("ix_payments_service_job_id", table_name="payments")
    op.drop_column("payments", "service_job_id")
    op.alter_column("payments", "rental_booking_id", existing_type=postgresql.UUID(), nullable=False)