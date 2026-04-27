"""add ltr_training_pairs table

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-24

Each row is one (query, document) pair for LambdaRank training.
query_id groups all destination candidates scored for the same synthetic profile.
relevance_label is an integer 0..3 derived from content_scorer output.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ltr_training_pairs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("query_id", UUID(as_uuid=True), nullable=False),
        sa.Column("destination_id", UUID(as_uuid=True), nullable=False),
        sa.Column("relevance_label", sa.SmallInteger, nullable=False),
        sa.Column("content_score", sa.Float, nullable=False),
        sa.Column("profile_snapshot", sa.JSON, nullable=True),
        sa.Column("travel_month", sa.SmallInteger, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ltr_pairs_query_id", "ltr_training_pairs", ["query_id"])
    op.create_index("ix_ltr_pairs_dest_id", "ltr_training_pairs", ["destination_id"])


def downgrade() -> None:
    op.drop_table("ltr_training_pairs")
