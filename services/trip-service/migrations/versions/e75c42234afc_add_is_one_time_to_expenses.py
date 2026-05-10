"""Add is_one_time to expenses

Revision ID: e75c42234afc
Revises: d7f1c9a2b8e4
Create Date: 2026-05-08 19:23:40.889259

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e75c42234afc"
down_revision: Union[str, Sequence[str], None] = "d7f1c9a2b8e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("expenses", sa.Column("is_one_time", sa.Boolean(), server_default="false", nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("expenses", "is_one_time")
