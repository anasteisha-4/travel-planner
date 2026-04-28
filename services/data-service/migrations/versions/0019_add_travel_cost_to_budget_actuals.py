"""Add travel_to_destination_usd, origin_lat, origin_lng to trip_budget_actuals.

Phase 7.8 — Travel-to-destination cost component for budget prediction.
Stores the round-trip transport cost (flight/train) as a separate column so
the ML model can learn the relationship between origin distance and total cost.
"""

import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "trip_budget_actuals",
        sa.Column("travel_to_destination_usd", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "trip_budget_actuals",
        sa.Column("origin_lat", sa.Float(), nullable=True),
    )
    op.add_column(
        "trip_budget_actuals",
        sa.Column("origin_lng", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("trip_budget_actuals", "origin_lng")
    op.drop_column("trip_budget_actuals", "origin_lat")
    op.drop_column("trip_budget_actuals", "travel_to_destination_usd")
