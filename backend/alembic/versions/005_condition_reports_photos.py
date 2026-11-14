"""condition reports and item photos

Revision ID: 005
Revises: 004
Create Date: 2026-11-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rental_condition_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "rental_booking_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rental_bookings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phase", sa.String(16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("damage_notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("owner_acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("renter_acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_condition_reports_booking_id", "rental_condition_reports", ["rental_booking_id"])
    op.execute(
        """
        CREATE UNIQUE INDEX uq_condition_report_booking_phase
        ON rental_condition_reports (rental_booking_id, phase)
        """
    )

    op.create_table(
        "condition_report_photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rental_condition_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("object_key", sa.String(512), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_condition_photos_report_id", "condition_report_photos", ["report_id"])
    op.create_index("ix_condition_photos_object_key", "condition_report_photos", ["object_key"], unique=True)

    op.create_table(
        "item_photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("object_key", sa.String(512), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_item_photos_item_id", "item_photos", ["item_id"])
    op.create_index("ix_item_photos_object_key", "item_photos", ["object_key"], unique=True)


def downgrade() -> None:
    op.drop_table("item_photos")
    op.drop_table("condition_report_photos")
    op.drop_table("rental_condition_reports")