"""add_rest_level_to_user_profiles

Revision ID: d7f1c9a2b8e4
Revises: 565632ac7576
Create Date: 2026-05-07 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d7f1c9a2b8e4"
down_revision: Union[str, Sequence[str], None] = "565632ac7576"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("rest_level", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("user_profiles", "rest_level")
