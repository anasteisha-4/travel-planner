"""Add experiments

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "experiments",
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=40), server_default="active", nullable=False),
        sa.Column("variants_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metrics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("guardrails_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experiments_key", "experiments", ["key"], unique=True)
    op.create_table(
        "analytics_experiment_assignments",
        sa.Column("experiment_key", sa.String(length=120), nullable=False),
        sa.Column("variant", sa.String(length=80), nullable=False),
        sa.Column("subject_key", sa.String(length=160), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("anonymous_id", sa.String(length=120), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("experiment_key", "subject_key", name="uq_analytics_experiment_subject"),
    )
    op.create_index(
        "ix_analytics_experiment_assignments_anonymous_id", "analytics_experiment_assignments", ["anonymous_id"]
    )
    op.create_index(
        "ix_analytics_experiment_assignments_experiment_key",
        "analytics_experiment_assignments",
        ["experiment_key"],
    )
    op.create_index(
        "ix_analytics_experiment_assignments_subject_key", "analytics_experiment_assignments", ["subject_key"]
    )
    op.create_index("ix_analytics_experiment_assignments_user_id", "analytics_experiment_assignments", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_analytics_experiment_assignments_user_id", table_name="analytics_experiment_assignments")
    op.drop_index("ix_analytics_experiment_assignments_subject_key", table_name="analytics_experiment_assignments")
    op.drop_index("ix_analytics_experiment_assignments_experiment_key", table_name="analytics_experiment_assignments")
    op.drop_index("ix_analytics_experiment_assignments_anonymous_id", table_name="analytics_experiment_assignments")
    op.drop_table("analytics_experiment_assignments")
    op.drop_index("ix_experiments_key", table_name="experiments")
    op.drop_table("experiments")
