"""booking requests and availability blocks

Revision ID: 003
Revises: 002
Create Date: 2026-11-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROTECTED_STATUSES = ("requested", "awaiting_payment", "confirmed", "active")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "item_availability_blocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_item_blocks_item_id", "item_availability_blocks", ["item_id"])
    op.execute(
        """
        ALTER TABLE item_availability_blocks
        ADD CONSTRAINT item_blocks_valid_range CHECK (end_date >= start_date)
        """
    )

    op.create_table(
        "rental_bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("renter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="requested"),
        sa.Column("rental_days", sa.Integer(), nullable=False),
        sa.Column("daily_price_cents_snapshot", sa.Integer(), nullable=False),
        sa.Column("deposit_cents_snapshot", sa.Integer(), nullable=False),
        sa.Column("subtotal_cents", sa.Integer(), nullable=False),
        sa.Column("total_cents", sa.Integer(), nullable=False),
        sa.Column("owner_note", sa.String(500), nullable=True),
        sa.Column("renter_note", sa.String(500), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_rental_bookings_item_id", "rental_bookings", ["item_id"])
    op.create_index("ix_rental_bookings_renter_id", "rental_bookings", ["renter_id"])
    op.create_index("ix_rental_bookings_status", "rental_bookings", ["status"])
    op.execute(
        """
        ALTER TABLE rental_bookings
        ADD CONSTRAINT rental_bookings_valid_range CHECK (end_date >= start_date)
        """
    )

    statuses_sql = ", ".join(f"'{s}'" for s in PROTECTED_STATUSES)
    op.execute(
        f"""
        ALTER TABLE rental_bookings
        ADD CONSTRAINT rental_bookings_no_overlap
        EXCLUDE USING gist (
            item_id WITH =,
            daterange(start_date, end_date + 1, '[)') WITH &&
        )
        WHERE (status IN ({statuses_sql}))
        """
    )


def downgrade() -> None:
    op.drop_table("rental_bookings")
    op.drop_table("item_availability_blocks")