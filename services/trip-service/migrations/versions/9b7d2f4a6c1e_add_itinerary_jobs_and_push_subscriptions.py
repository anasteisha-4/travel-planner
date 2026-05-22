"""add itinerary jobs and push subscriptions

Revision ID: 9b7d2f4a6c1e
Revises: 0f8a1c2d3e4b
Create Date: 2026-05-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9b7d2f4a6c1e"
down_revision: Union[str, Sequence[str], None] = "0f8a1c2d3e4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "itinerary_generation_jobs",
        sa.Column("trip_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("result_itinerary_ids", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_itinerary_generation_jobs_status"), "itinerary_generation_jobs", ["status"], unique=False)
    op.create_index(
        op.f("ix_itinerary_generation_jobs_trip_id"), "itinerary_generation_jobs", ["trip_id"], unique=False
    )
    op.create_index(
        op.f("ix_itinerary_generation_jobs_user_id"), "itinerary_generation_jobs", ["user_id"], unique=False
    )

    op.create_table(
        "push_subscriptions",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.Text(), nullable=False),
        sa.Column("auth", sa.Text(), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint"),
    )
    op.create_index(op.f("ix_push_subscriptions_user_id"), "push_subscriptions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_push_subscriptions_user_id"), table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
    op.drop_index(op.f("ix_itinerary_generation_jobs_user_id"), table_name="itinerary_generation_jobs")
    op.drop_index(op.f("ix_itinerary_generation_jobs_trip_id"), table_name="itinerary_generation_jobs")
    op.drop_index(op.f("ix_itinerary_generation_jobs_status"), table_name="itinerary_generation_jobs")
    op.drop_table("itinerary_generation_jobs")
