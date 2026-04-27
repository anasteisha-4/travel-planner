"""add experiment_assignments table

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "experiment_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("experiment_name", sa.String(100), nullable=False),
        sa.Column("variant", sa.String(50), nullable=False),
        sa.Column("assigned_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "experiment_name", name="uq_experiment_user"),
    )


def downgrade() -> None:
    op.drop_table("experiment_assignments")
