"""add order to place_visits

Revision ID: ba39d2e860e8
Revises: 456db4b486c8
Create Date: 2026-03-27 20:47:56.410899

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ba39d2e860e8"
down_revision: Union[str, Sequence[str], None] = "456db4b486c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("place_visits", sa.Column("order", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("place_visits", "order")
