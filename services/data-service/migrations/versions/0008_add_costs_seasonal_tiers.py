"""Add accommodation tiers and seasonal_multiplier to destination_costs.

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("destination_costs", sa.Column("hostel_usd", sa.Float(), nullable=True))
    op.add_column("destination_costs", sa.Column("budget_usd", sa.Float(), nullable=True))
    op.add_column("destination_costs", sa.Column("mid_usd", sa.Float(), nullable=True))
    op.add_column("destination_costs", sa.Column("luxury_usd", sa.Float(), nullable=True))
    op.add_column("destination_costs", sa.Column("seasonal_multiplier", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("destination_costs", "seasonal_multiplier")
    op.drop_column("destination_costs", "luxury_usd")
    op.drop_column("destination_costs", "mid_usd")
    op.drop_column("destination_costs", "budget_usd")
    op.drop_column("destination_costs", "hostel_usd")
