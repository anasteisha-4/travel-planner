"""add citizenship code to user profiles

Revision ID: a8c2d4e6f901
Revises: 9b7d2f4a6c1e
Create Date: 2026-05-24 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a8c2d4e6f901"
down_revision: Union[str, Sequence[str], None] = "9b7d2f4a6c1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("citizenship_code", sa.String(length=2), nullable=True))


def downgrade() -> None:
    op.drop_column("user_profiles", "citizenship_code")
