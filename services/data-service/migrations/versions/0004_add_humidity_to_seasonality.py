"""Add avg_humidity_pct to destination_seasonality.

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-29
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "destination_seasonality",
        sa.Column("avg_humidity_pct", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("destination_seasonality", "avg_humidity_pct")
