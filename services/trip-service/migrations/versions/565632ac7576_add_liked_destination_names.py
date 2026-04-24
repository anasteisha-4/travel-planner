"""add_liked_destination_names

Revision ID: 565632ac7576
Revises: a3f2b1c0d4e5
Create Date: 2026-04-20 15:35:02.977317

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '565632ac7576'
down_revision: Union[str, Sequence[str], None] = 'a3f2b1c0d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user_profiles', sa.Column('liked_destination_names', sa.ARRAY(sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('user_profiles', 'liked_destination_names')
