"""Add post_trip_feedback table

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "post_trip_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trip_id", sa.String(length=50), nullable=False),
        sa.Column("destination", sa.String(length=200), nullable=False),
        sa.Column("overall_rating", sa.SmallInteger(), nullable=False),
        sa.Column("destination_rating", sa.SmallInteger(), nullable=True),
        sa.Column("value_rating", sa.SmallInteger(), nullable=True),
        sa.Column("actual_total_cost", sa.Float(), nullable=True),
        sa.Column("actual_currency", sa.String(length=3), nullable=True),
        sa.Column("would_revisit", sa.Boolean(), nullable=True),
        sa.Column("free_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trip_id"),
    )
    op.create_index("ix_post_trip_feedback_user_id", "post_trip_feedback", ["user_id"])
    op.create_index("ix_post_trip_feedback_trip_id", "post_trip_feedback", ["trip_id"])


def downgrade() -> None:
    op.drop_index("ix_post_trip_feedback_trip_id", table_name="post_trip_feedback")
    op.drop_index("ix_post_trip_feedback_user_id", table_name="post_trip_feedback")
    op.drop_table("post_trip_feedback")
