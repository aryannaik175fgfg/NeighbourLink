"""assistance: providers, requests, offers, jobs

Revision ID: 006
Revises: 005
Create Date: 2026-11-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "service_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_index("ix_service_categories_slug", "service_categories", ["slug"], unique=True)

    op.create_table(
        "provider_portfolios",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("headline", sa.String(160), nullable=False),
        sa.Column("introduction", sa.Text(), nullable=False),
        sa.Column("service_area_label", sa.String(255), nullable=False),
        sa.Column("location", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.execute("CREATE INDEX ix_provider_portfolios_location ON provider_portfolios USING GIST (location)")

    op.create_table(
        "portfolio_service_categories",
        sa.Column(
            "portfolio_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("provider_portfolios.user_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_categories.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.create_table(
        "service_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_categories.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("service_area_label", sa.String(255), nullable=False),
        sa.Column("location", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("budget_cents", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(32), server_default="published", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_service_requests_customer_id", "service_requests", ["customer_id"])
    op.create_index("ix_service_requests_status", "service_requests", ["status"])

    op.create_table(
        "service_offers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("included_work", sa.Text(), nullable=False),
        sa.Column("excluded_work", sa.Text(), nullable=True),
        sa.Column("estimated_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(24), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_service_offers_request_id", "service_offers", ["request_id"])
    op.create_index("ix_service_offers_provider_id", "service_offers", ["provider_id"])

    op.create_table(
        "service_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "offer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_offers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(32), server_default="confirmed", nullable=False),
        sa.Column("price_cents_snapshot", sa.Integer(), nullable=False),
        sa.Column("included_work_snapshot", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_service_jobs_request_id", "service_jobs", ["request_id"], unique=True)


def downgrade() -> None:
    op.drop_table("service_jobs")
    op.drop_table("service_offers")
    op.drop_table("service_requests")
    op.drop_table("portfolio_service_categories")
    op.drop_table("provider_portfolios")
    op.drop_index("ix_service_categories_slug", table_name="service_categories")
    op.drop_table("service_categories")