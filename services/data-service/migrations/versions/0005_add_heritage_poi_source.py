"""Add 'heritage' value to poisource enum.

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-29
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE poisource ADD VALUE IF NOT EXISTS 'heritage'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values — would require recreating the type.
    # Safe to leave as-is; unused 'heritage' value is harmless.
    pass
