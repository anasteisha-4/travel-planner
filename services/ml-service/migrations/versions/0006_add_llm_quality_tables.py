"""Add LLM quality audit tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_review_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=120), nullable=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("prompt_version", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("issue_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cache_hit", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("request_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_review_logs_entity_id", "llm_review_logs", ["entity_id"])
    op.create_index("ix_llm_review_logs_entity_type", "llm_review_logs", ["entity_type"])
    op.create_index("ix_llm_review_logs_status", "llm_review_logs", ["status"])
    op.create_index("ix_llm_review_logs_user_id", "llm_review_logs", ["user_id"])

    op.create_table(
        "llm_candidate_poi",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("destination_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trip_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("itinerary_id", sa.String(length=120), nullable=True),
        sa.Column("review_log_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("approved_poi_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_candidate_poi_destination_id", "llm_candidate_poi", ["destination_id"])
    op.create_index("ix_llm_candidate_poi_review_log_id", "llm_candidate_poi", ["review_log_id"])
    op.create_index("ix_llm_candidate_poi_status", "llm_candidate_poi", ["status"])
    op.create_index("ix_llm_candidate_poi_trip_id", "llm_candidate_poi", ["trip_id"])

    op.create_table(
        "llm_candidate_destinations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trip_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("review_log_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("country_name", sa.Text(), nullable=True),
        sa.Column("region", sa.Text(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("reviewed_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_candidate_destinations_review_log_id", "llm_candidate_destinations", ["review_log_id"])
    op.create_index("ix_llm_candidate_destinations_status", "llm_candidate_destinations", ["status"])
    op.create_index("ix_llm_candidate_destinations_trip_id", "llm_candidate_destinations", ["trip_id"])
    op.create_index("ix_llm_candidate_destinations_user_id", "llm_candidate_destinations", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_candidate_destinations_user_id", table_name="llm_candidate_destinations")
    op.drop_index("ix_llm_candidate_destinations_trip_id", table_name="llm_candidate_destinations")
    op.drop_index("ix_llm_candidate_destinations_status", table_name="llm_candidate_destinations")
    op.drop_index("ix_llm_candidate_destinations_review_log_id", table_name="llm_candidate_destinations")
    op.drop_table("llm_candidate_destinations")

    op.drop_index("ix_llm_candidate_poi_trip_id", table_name="llm_candidate_poi")
    op.drop_index("ix_llm_candidate_poi_status", table_name="llm_candidate_poi")
    op.drop_index("ix_llm_candidate_poi_review_log_id", table_name="llm_candidate_poi")
    op.drop_index("ix_llm_candidate_poi_destination_id", table_name="llm_candidate_poi")
    op.drop_table("llm_candidate_poi")

    op.drop_index("ix_llm_review_logs_user_id", table_name="llm_review_logs")
    op.drop_index("ix_llm_review_logs_status", table_name="llm_review_logs")
    op.drop_index("ix_llm_review_logs_entity_type", table_name="llm_review_logs")
    op.drop_index("ix_llm_review_logs_entity_id", table_name="llm_review_logs")
    op.drop_table("llm_review_logs")
