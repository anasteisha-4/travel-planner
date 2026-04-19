"""Add data_source_details JSONB to destination_infrastructure (Migration 0018).

Phase 3.5 — Infrastructure data quality upgrade.
Records per-field data source provenance (WB year, Speedtest, regional fallback, etc.)
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "destination_infrastructure",
        sa.Column(
            "data_source_details",
            JSONB,
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("destination_infrastructure", "data_source_details")
