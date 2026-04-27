"""add feature_snapshots table

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feature_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("snapshot_type", sa.String(20), nullable=False),
        sa.Column("feature_version", sa.Integer, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("rows_count", sa.Integer, nullable=True),
        sa.Column("purpose", sa.String(30), nullable=True),
        sa.Column("storage_path", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("feature_snapshots")
