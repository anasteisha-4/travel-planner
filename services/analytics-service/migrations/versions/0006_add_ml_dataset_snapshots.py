"""Add ML dataset snapshots

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ml_dataset_snapshots",
        sa.Column("dataset_type", sa.String(length=40), nullable=False),
        sa.Column("date_from", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("date_to", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("contract_version", sa.String(length=20), server_default="1", nullable=False),
        sa.Column("builder_version", sa.String(length=80), nullable=False),
        sa.Column("row_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("positive_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sanity_report", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ml_dataset_snapshots_dataset_type", "ml_dataset_snapshots", ["dataset_type"])
    op.create_index("ix_ml_dataset_snapshots_created_by_user_id", "ml_dataset_snapshots", ["created_by_user_id"])
    op.create_index("ix_ml_dataset_snapshots_type_created", "ml_dataset_snapshots", ["dataset_type", "created_at"])
    op.create_index("ix_ml_dataset_snapshots_range", "ml_dataset_snapshots", ["date_from", "date_to"])


def downgrade() -> None:
    op.drop_index("ix_ml_dataset_snapshots_range", table_name="ml_dataset_snapshots")
    op.drop_index("ix_ml_dataset_snapshots_type_created", table_name="ml_dataset_snapshots")
    op.drop_index("ix_ml_dataset_snapshots_created_by_user_id", table_name="ml_dataset_snapshots")
    op.drop_index("ix_ml_dataset_snapshots_dataset_type", table_name="ml_dataset_snapshots")
    op.drop_table("ml_dataset_snapshots")
