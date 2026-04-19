"""Add destination_popularity table for Wikipedia pageview crowd index

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-29

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
        "destination_popularity",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "destination_id",
            UUID(as_uuid=True),
            sa.ForeignKey("destinations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("month", sa.SmallInteger, nullable=False),
        sa.Column("avg_pageviews", sa.Integer, nullable=False),
        sa.Column("crowd_index", sa.Float, nullable=False),
        sa.Column("wikipedia_article", sa.String(300), nullable=True),
        sa.Column("data_year", sa.SmallInteger, nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_popularity_dest_month",
        "destination_popularity",
        ["destination_id", "month"],
    )
    op.create_check_constraint(
        "ck_popularity_month", "destination_popularity", "month >= 1 AND month <= 12"
    )
    op.create_check_constraint(
        "ck_popularity_crowd_index",
        "destination_popularity",
        "crowd_index >= 0 AND crowd_index <= 1",
    )


def downgrade() -> None:
    op.drop_table("destination_popularity")
