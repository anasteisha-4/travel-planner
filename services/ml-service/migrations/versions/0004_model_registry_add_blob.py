"""add model_blob column to model_registry

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-24

Stores serialised joblib artifact as bytea so the model survives
container restarts without a persistent volume.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("model_registry", sa.Column("model_blob", sa.LargeBinary, nullable=True))


def downgrade() -> None:
    op.drop_column("model_registry", "model_blob")
