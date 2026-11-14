"""rental categories and item listings

Revision ID: 002
Revises: 001
Create Date: 2026-11-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rental_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_rental_categories_slug", "rental_categories", ["slug"], unique=True)

    op.create_table(
        "items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rental_categories.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("condition", sa.String(32), nullable=False),
        sa.Column("daily_price_cents", sa.Integer(), nullable=False),
        sa.Column("deposit_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(24), nullable=False, server_default="active"),
        sa.Column("pickup_instructions", sa.String(2000), nullable=True),
        sa.Column("public_area_label", sa.String(255), nullable=False),
        sa.Column("exact_address", sa.String(500), nullable=True),
        sa.Column("location", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_items_owner_id", "items", ["owner_id"])
    op.create_index("ix_items_category_id", "items", ["category_id"])
    op.create_index("ix_items_status", "items", ["status"])
    op.execute("CREATE INDEX ix_items_location ON items USING GIST (location)")


def downgrade() -> None:
    op.drop_index("ix_items_location", table_name="items")
    op.drop_index("ix_items_status", table_name="items")
    op.drop_index("ix_items_category_id", table_name="items")
    op.drop_index("ix_items_owner_id", table_name="items")
    op.drop_table("items")
    op.drop_index("ix_rental_categories_slug", table_name="rental_categories")
    op.drop_table("rental_categories")