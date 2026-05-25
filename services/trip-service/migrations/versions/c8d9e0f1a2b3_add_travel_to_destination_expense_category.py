"""add travel_to_destination expense category

Revision ID: c8d9e0f1a2b3
Revises: a8c2d4e6f901
Create Date: 2026-05-25 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = "a8c2d4e6f901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE expensecategory ADD VALUE IF NOT EXISTS 'travel_to_destination'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be dropped safely while rows may still use them.
    pass
