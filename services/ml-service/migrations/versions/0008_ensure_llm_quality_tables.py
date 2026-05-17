"""Ensure LLM quality audit tables

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-17

"""

from typing import Sequence, Union

from alembic import op

revision: str = "0008"
down_revision: Union[str, Sequence[str], None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_review_logs (
            id UUID PRIMARY KEY,
            user_id UUID,
            entity_type VARCHAR(80) NOT NULL,
            entity_id VARCHAR(120),
            provider VARCHAR(80) NOT NULL,
            model VARCHAR(160) NOT NULL,
            prompt_version VARCHAR(120) NOT NULL,
            status VARCHAR(40) NOT NULL,
            latency_ms INTEGER,
            issue_codes JSONB NOT NULL,
            cache_hit BOOLEAN NOT NULL,
            error_code VARCHAR(120),
            request_summary JSONB,
            response JSONB
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_llm_review_logs_entity_id ON llm_review_logs (entity_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_llm_review_logs_entity_type ON llm_review_logs (entity_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_llm_review_logs_status ON llm_review_logs (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_llm_review_logs_user_id ON llm_review_logs (user_id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_candidate_poi (
            id UUID PRIMARY KEY,
            destination_id UUID,
            trip_id UUID,
            itinerary_id VARCHAR(120),
            review_log_id UUID,
            name TEXT NOT NULL,
            category VARCHAR(120),
            lat DOUBLE PRECISION,
            lng DOUBLE PRECISION,
            address TEXT,
            payload JSONB NOT NULL,
            status VARCHAR(40) NOT NULL,
            approved_poi_id UUID,
            reviewed_by_user_id VARCHAR(64),
            review_comment TEXT
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_llm_candidate_poi_destination_id ON llm_candidate_poi (destination_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_llm_candidate_poi_review_log_id ON llm_candidate_poi (review_log_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_llm_candidate_poi_status ON llm_candidate_poi (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_llm_candidate_poi_trip_id ON llm_candidate_poi (trip_id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_candidate_destinations (
            id UUID PRIMARY KEY,
            user_id UUID,
            trip_id UUID,
            review_log_id UUID,
            name TEXT NOT NULL,
            country_code VARCHAR(2),
            country_name TEXT,
            region TEXT,
            lat DOUBLE PRECISION,
            lng DOUBLE PRECISION,
            payload JSONB NOT NULL,
            status VARCHAR(40) NOT NULL,
            reviewed_by_user_id VARCHAR(64),
            review_comment TEXT
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_llm_candidate_destinations_review_log_id "
        "ON llm_candidate_destinations (review_log_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_llm_candidate_destinations_status ON llm_candidate_destinations (status)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_llm_candidate_destinations_trip_id ON llm_candidate_destinations (trip_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_llm_candidate_destinations_user_id ON llm_candidate_destinations (user_id)"
    )


def downgrade() -> None:
    pass
