"""Add destination_events table (Migration 0012).

Phase 1.4 — events data for CIS travelers:
recurring annual events that affect crowd_index and price_impact
(Novruz, Russian May holidays, White Nights, Ramadan, Georgian New Year, etc.).
Supports category enum: festival|holiday|religious|carnival|sports|music|food|arts.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "destination_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "destination_id",
            UUID(as_uuid=True),
            sa.ForeignKey("destinations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("name_ru", sa.String(200), nullable=True),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("month_start", sa.SmallInteger(), nullable=False),
        sa.Column("month_end", sa.SmallInteger(), nullable=False),
        sa.Column("day_start", sa.SmallInteger(), nullable=True),
        sa.Column("day_end", sa.SmallInteger(), nullable=True),
        sa.Column("is_annual", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("crowd_impact", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("price_impact", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column(
            "traveler_relevance", sa.Float(), nullable=False, server_default="0.5"
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "data_source", sa.String(50), nullable=False, server_default="seed_csv"
        ),
    )
    op.create_index(
        "ix_destination_events_destination_id",
        "destination_events",
        ["destination_id"],
    )
    op.create_index(
        "ix_destination_events_month_start",
        "destination_events",
        ["month_start"],
    )


def downgrade() -> None:
    op.drop_index("ix_destination_events_month_start", table_name="destination_events")
    op.drop_index(
        "ix_destination_events_destination_id", table_name="destination_events"
    )
    op.drop_table("destination_events")
