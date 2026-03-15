"""remove_trip_title

Revision ID: 653c3ccd8c87
Revises: b80a9565cb34
Create Date: 2026-03-14 12:34:49.206092

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "653c3ccd8c87"
down_revision: Union[str, Sequence[str], None] = "b80a9565cb34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("trips", "title")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("trips", sa.Column("title", sa.String(), nullable=False))
