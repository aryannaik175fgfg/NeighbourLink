"""community comments, reactions, moderation, listing links

Revision ID: 016
Revises: 015
Create Date: 2026-11-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("community_posts", sa.Column("linked_listing_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("community_posts", sa.Column("is_hidden", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("community_posts", sa.Column("hidden_reason", sa.String(500), nullable=True))
    op.create_foreign_key(
        "fk_community_posts_listing",
        "community_posts",
        "items",
        ["linked_listing_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "community_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "post_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("community_posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body", sa.String(2000), nullable=False),
        sa.Column("is_hidden", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_community_comments_post", "community_comments", ["post_id"])

    op.create_table(
        "community_reactions",
        sa.Column("post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("community_posts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("reaction", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("community_reactions")
    op.drop_table("community_comments")
    op.drop_constraint("fk_community_posts_listing", "community_posts", type_="foreignkey")
    op.drop_column("community_posts", "hidden_reason")
    op.drop_column("community_posts", "is_hidden")
    op.drop_column("community_posts", "linked_listing_id")