"""Add data_quality_score to destination_costs (Migration 0016).

Phase 3.3 — Cost data quality scoring for Russian cities.
Scores: 1.0 = real Numbeo; 0.7 = country avg; 0.5 = PPP-corrected;
        0.3 = subregion avg; 0.1 = global avg.
"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "destination_costs",
        sa.Column(
            "data_quality_score",
            sa.Float(),
            nullable=False,
            server_default="0.7",
        ),
    )
    # Backfill existing records based on data_source
    op.execute("""
        UPDATE destination_costs
        SET data_quality_score = CASE data_source
            WHEN 'numbeo'            THEN 1.0
            WHEN 'country_average'   THEN 0.7
            WHEN 'subregion_average' THEN 0.3
            WHEN 'region_average'    THEN 0.3
            WHEN 'global_average'    THEN 0.1
            ELSE 0.5
        END
    """)


def downgrade() -> None:
    op.drop_column("destination_costs", "data_quality_score")
