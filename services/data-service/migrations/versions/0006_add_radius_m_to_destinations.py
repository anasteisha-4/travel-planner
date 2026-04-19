"""Add radius_m column to destinations table.

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-30
"""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "destinations",
        sa.Column("radius_m", sa.Integer(), nullable=False, server_default="20000"),
    )


def downgrade() -> None:
    op.drop_column("destinations", "radius_m")
