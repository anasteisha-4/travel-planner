"""add rest days to trips

Revision ID: 0f8a1c2d3e4b
Revises: f4a7b8c9d0e1
Create Date: 2026-05-11 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0f8a1c2d3e4b"
down_revision: Union[str, Sequence[str], None] = "f4a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "trips",
        sa.Column("rest_days_count", sa.SmallInteger(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("trips", "rest_days_count")
