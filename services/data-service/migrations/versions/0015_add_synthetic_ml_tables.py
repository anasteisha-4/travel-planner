"""Add synthetic ML tables: user_preference_profiles, trip_budget_actuals, trajectory_feedback.

Phase 1.7 — synthetic training data tables for:
- Destination recommendation (UserPreferenceProfile)
- Budget prediction (TripBudgetActual)
- Route quality feedback (TrajectoryFeedback)
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_preference_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("citizenship_code", sa.String(2), nullable=False),
        sa.Column("travel_month", sa.SmallInteger(), nullable=False),
        sa.Column("budget_tier", sa.String(20), nullable=False),
        sa.Column("preferred_activities", JSONB(), nullable=False, server_default="[]"),
        sa.Column("trip_type", sa.String(50), nullable=False),
        sa.Column("min_safety_threshold", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("profile_type", sa.String(50), nullable=False),
        sa.Column("label_destination_id", UUID(as_uuid=True), nullable=True),
        sa.Column("label_score", sa.Float(), nullable=True),
        sa.Column("source", sa.String(50), nullable=False, server_default="synthetic"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_user_preference_profiles_citizenship_code",
        "user_preference_profiles",
        ["citizenship_code"],
    )
    op.create_index(
        "ix_user_preference_profiles_label_destination_id",
        "user_preference_profiles",
        ["label_destination_id"],
    )

    op.create_table(
        "trip_budget_actuals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("trip_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "destination_id",
            UUID(as_uuid=True),
            sa.ForeignKey("destinations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("duration_days", sa.SmallInteger(), nullable=False),
        sa.Column("people_count", sa.SmallInteger(), nullable=False),
        sa.Column("travel_month", sa.SmallInteger(), nullable=False),
        sa.Column("total_actual_usd", sa.Float(), nullable=False),
        sa.Column("meals_usd", sa.Float(), nullable=False),
        sa.Column("accommodation_usd", sa.Float(), nullable=False),
        sa.Column("transport_usd", sa.Float(), nullable=False),
        sa.Column("activities_usd", sa.Float(), nullable=False),
        sa.Column("accommodation_tier", sa.String(20), nullable=False),
        sa.Column("data_source", sa.String(50), nullable=False, server_default="synthetic"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_trip_budget_actuals_trip_id", "trip_budget_actuals", ["trip_id"])
    op.create_index(
        "ix_trip_budget_actuals_destination_id",
        "trip_budget_actuals",
        ["destination_id"],
    )

    op.create_table(
        "trajectory_feedback",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "trajectory_id",
            UUID(as_uuid=True),
            sa.ForeignKey("trajectories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("was_completed", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("people_count", sa.SmallInteger(), nullable=False),
        sa.Column("trip_duration_days", sa.SmallInteger(), nullable=False),
        sa.Column("source", sa.String(50), nullable=False, server_default="synthetic"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_trajectory_feedback_trajectory_id", "trajectory_feedback", ["trajectory_id"])


def downgrade() -> None:
    op.drop_table("trajectory_feedback")
    op.drop_table("trip_budget_actuals")
    op.drop_table("user_preference_profiles")
