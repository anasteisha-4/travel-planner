"""Add visit_duration_minutes and opening_hours to poi table.

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-02
"""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "poi", sa.Column("visit_duration_minutes", sa.Integer(), nullable=True)
    )
    op.add_column("poi", sa.Column("opening_hours", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("poi", "opening_hours")
    op.drop_column("poi", "visit_duration_minutes")
