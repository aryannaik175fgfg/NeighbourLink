"""user settings and notification preferences

Revision ID: 012
Revises: 011
Create Date: 2026-11-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_settings",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("notify_rentals", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("notify_assistance", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("notify_messages", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("notify_community", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("default_latitude", sa.Float(), nullable=True),
        sa.Column("default_longitude", sa.Float(), nullable=True),
        sa.Column("default_radius_km", sa.Integer(), server_default="25", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_settings")