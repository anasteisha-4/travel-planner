"""Add LLM admin approved POI source.

Revision ID: 0022
Revises: 0021
Create Date: 2026-05-18
"""

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE poisource ADD VALUE IF NOT EXISTS 'llm_admin_approved'")


def downgrade() -> None:
    # PostgreSQL cannot remove enum values without recreating the enum type.
    pass
