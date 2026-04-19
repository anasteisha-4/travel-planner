"""Add price_tier to poi table (Migration 0014).

Phase 1.6 — price tier classification for POI:
free, budget, mid, premium, luxury.
Populated from OSM tags (fee=no), categories (natural=beach → free),
and Wikidata P2555 (admission fee).
"""

import sqlalchemy as sa
from alembic import op


revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "poi",
        sa.Column("price_tier", sa.String(20), nullable=True),
    )
    op.add_column(
        "poi",
        sa.Column("entrance_fee_usd", sa.Float(), nullable=True),
    )
    op.add_column(
        "poi",
        sa.Column("fee_notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("poi", "fee_notes")
    op.drop_column("poi", "entrance_fee_usd")
    op.drop_column("poi", "price_tier")
