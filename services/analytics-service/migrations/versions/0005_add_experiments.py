"""Add experiments

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-13

"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EXPERIMENTS = [
    ("ranker_content_vs_hybrid_v2", ["content", "hybrid_v2"]),
    ("recommendation_explanation_ui", ["compact_tags", "factor_breakdown"]),
    ("destination_validation_placement", ["detail_only", "create_form_and_detail"]),
    ("budget_uncertainty_ui", ["p50_only", "p10_p50_p90"]),
    ("itinerary_generation_entry", ["tab_cta", "proactive_prompt"]),
]


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

    experiments_table = sa.table(
        "experiments",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("key", sa.String),
        sa.column("description", sa.Text),
        sa.column("status", sa.String),
        sa.column("variants_json", postgresql.JSONB),
        sa.column("metrics_json", postgresql.JSONB),
        sa.column("guardrails_json", postgresql.JSONB),
    )
    op.bulk_insert(
        experiments_table,
        [
            {
                "id": uuid.uuid4(),
                "key": key,
                "description": "Seeded Triply experiment",
                "status": "active",
                "variants_json": variants,
                "metrics_json": {
                    "primary": "recommendation_to_trip_conversion",
                    "secondary": [
                        "detail_open_rate",
                        "validation_view_rate",
                        "budget_view_rate",
                        "itinerary_generation_rate",
                    ],
                    "quality": ["post_trip_rating", "would_revisit", "itinerary_approval_rate"],
                },
                "guardrails_json": {
                    "error_rate": "not_increase",
                    "latency_p95": "not_increase",
                    "empty_recommendation_rate": "not_increase",
                },
            }
            for key, variants in EXPERIMENTS
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_analytics_experiment_assignments_user_id", table_name="analytics_experiment_assignments")
    op.drop_index("ix_analytics_experiment_assignments_subject_key", table_name="analytics_experiment_assignments")
    op.drop_index("ix_analytics_experiment_assignments_experiment_key", table_name="analytics_experiment_assignments")
    op.drop_index("ix_analytics_experiment_assignments_anonymous_id", table_name="analytics_experiment_assignments")
    op.drop_table("analytics_experiment_assignments")
    op.drop_index("ix_experiments_key", table_name="experiments")
    op.drop_table("experiments")
