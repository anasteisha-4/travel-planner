"""Add safety_data_source and city_adjustment_factor to destination_safety (Migration 0017).

Phase 3.4 — City-level safety overrides for Russia.
Allows per-city adjustment on top of country-level GPI score.
"""

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "destination_safety",
        sa.Column(
            "safety_data_source",
            sa.String(length=50),
            nullable=False,
            server_default="gpi_country",
        ),
    )
    op.add_column(
        "destination_safety",
        sa.Column(
            "city_adjustment_factor",
            sa.Float(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("destination_safety", "city_adjustment_factor")
    op.drop_column("destination_safety", "safety_data_source")
