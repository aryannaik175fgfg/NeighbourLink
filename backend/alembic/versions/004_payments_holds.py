"""payments, payment events, booking hold and lifecycle timestamps

Revision ID: 004
Revises: 003
Create Date: 2026-11-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("rental_bookings", sa.Column("hold_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("rental_bookings", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("rental_bookings", sa.Column("pickup_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("rental_bookings", sa.Column("return_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("rental_bookings", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "rental_booking_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rental_bookings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("provider", sa.String(32), nullable=False, server_default="sandbox"),
        sa.Column("provider_reference", sa.String(128), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("succeeded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_payments_booking_id", "payments", ["rental_booking_id"])
    op.create_index("ix_payments_idempotency_key", "payments", ["idempotency_key"], unique=True)
    op.create_index("ix_payments_provider_reference", "payments", ["provider_reference"], unique=True)

    op.create_table(
        "payment_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "payment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("payments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("provider_event_id", sa.String(128), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_payment_events_payment_id", "payment_events", ["payment_id"])
    op.create_index("ix_payment_events_provider_event_id", "payment_events", ["provider_event_id"], unique=True)


def downgrade() -> None:
    op.drop_table("payment_events")
    op.drop_table("payments")
    op.drop_column("rental_bookings", "completed_at")
    op.drop_column("rental_bookings", "return_at")
    op.drop_column("rental_bookings", "pickup_at")
    op.drop_column("rental_bookings", "paid_at")
    op.drop_column("rental_bookings", "hold_expires_at")