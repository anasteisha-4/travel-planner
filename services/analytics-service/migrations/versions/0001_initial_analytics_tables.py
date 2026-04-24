"""Initial analytics tables: user_events and user_features

Revision ID: 0001
Revises:
Create Date: 2026-04-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=True),
        sa.Column("entity_id", sa.String(length=50), nullable=True),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("client_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_events_user_id", "user_events", ["user_id"])
    op.create_index("ix_user_events_session_id", "user_events", ["session_id"])
    op.create_index("ix_user_events_event_type", "user_events", ["event_type"])
    op.create_index("ix_user_events_user_created", "user_events", ["user_id", "created_at"])
    op.create_index("ix_user_events_type_created", "user_events", ["event_type", "created_at"])
    op.create_index(
        "ix_user_events_context_gin", "user_events", ["context"], postgresql_using="gin"
    )

    op.create_table(
        "user_features",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feature_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("computed_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("activity_prefs_vector", postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column("budget_min_usd", sa.Float(), nullable=True),
        sa.Column("budget_max_usd", sa.Float(), nullable=True),
        sa.Column("preferred_duration_days", sa.SmallInteger(), nullable=True),
        sa.Column("origin_lat", sa.Float(), nullable=True),
        sa.Column("origin_lng", sa.Float(), nullable=True),
        sa.Column("viewed_destination_ids", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("clicked_destination_ids", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("session_count", sa.Integer(), nullable=True),
        sa.Column("avg_session_events", sa.Float(), nullable=True),
        sa.Column("completed_trips_count", sa.Integer(), nullable=True),
        sa.Column("avg_spend_ratio", sa.Float(), nullable=True),
        sa.Column("visited_destination_ids", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("avg_destination_rating", sa.Float(), nullable=True),
        sa.Column("would_revisit_ratio", sa.Float(), nullable=True),
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_features")
    op.drop_index("ix_user_events_context_gin", table_name="user_events")
    op.drop_index("ix_user_events_type_created", table_name="user_events")
    op.drop_index("ix_user_events_user_created", table_name="user_events")
    op.drop_index("ix_user_events_event_type", table_name="user_events")
    op.drop_index("ix_user_events_session_id", table_name="user_events")
    op.drop_index("ix_user_events_user_id", table_name="user_events")
    op.drop_table("user_events")
