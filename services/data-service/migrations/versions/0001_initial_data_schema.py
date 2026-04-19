"""Initial data schema

Revision ID: 0001
Revises:
Create Date: 2026-03-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all data layer tables."""

    # 1. destinations
    op.create_table(
        "destinations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("lat", sa.Float, nullable=False),
        sa.Column("lng", sa.Float, nullable=False),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("subregion", sa.String(100), nullable=True),
        sa.Column("capital", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("population", sa.BigInteger, nullable=True),
        sa.Column("currencies", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
        sa.UniqueConstraint("name", "country_code", name="uq_destination_name_country"),
    )
    op.create_index("ix_destinations_country_code", "destinations", ["country_code"])

    # 2. destination_seasonality
    op.create_table(
        "destination_seasonality",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "destination_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("destinations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("month", sa.SmallInteger, nullable=False),
        sa.Column("avg_temp_c", sa.Float, nullable=False),
        sa.Column("avg_precipitation_mm", sa.Float, nullable=False),
        sa.Column("season_score", sa.Float, nullable=False),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "destination_id", "month", name="uq_seasonality_dest_month"
        ),
        sa.CheckConstraint("month >= 1 AND month <= 12", name="ck_seasonality_month"),
        sa.CheckConstraint(
            "season_score >= 0 AND season_score <= 1", name="ck_seasonality_score"
        ),
    )
    op.create_index(
        "ix_destination_seasonality_destination_id",
        "destination_seasonality",
        ["destination_id"],
    )

    # 3. destination_costs
    op.create_table(
        "destination_costs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "destination_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("destinations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("avg_meal_cost_usd", sa.Float, nullable=False),
        sa.Column("avg_transport_cost_usd", sa.Float, nullable=False),
        sa.Column("avg_hotel_cost_usd", sa.Float, nullable=False),
        sa.Column("avg_daily_cost_usd", sa.Float, nullable=False),
        sa.Column("cost_index", sa.Float, nullable=False),
        sa.Column(
            "data_source", sa.String(50), nullable=False, server_default="numbeo"
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_destination_costs_destination_id", "destination_costs", ["destination_id"]
    )

    # 4. destination_safety
    op.create_table(
        "destination_safety",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "destination_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("destinations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("safety_score", sa.Float, nullable=False),
        sa.Column("gpi_score", sa.Float, nullable=True),
        sa.Column("gpi_rank", sa.SmallInteger, nullable=True),
        sa.Column("gpi_year", sa.SmallInteger, nullable=True),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "safety_score >= 0 AND safety_score <= 1", name="ck_safety_score"
        ),
    )
    op.create_index(
        "ix_destination_safety_destination_id", "destination_safety", ["destination_id"]
    )

    # 5. visa_rules (enum first)
    visa_type_enum = postgresql.ENUM(
        "visa_free",
        "evisa",
        "visa_required",
        "no_admission",
        name="visatype",
        create_type=True,
    )
    visa_type_enum.create(op.get_bind())

    op.create_table(
        "visa_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("citizenship_code", sa.String(2), nullable=False),
        sa.Column(
            "destination_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("destinations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "visa_type",
            postgresql.ENUM(
                "visa_free",
                "evisa",
                "visa_required",
                "no_admission",
                name="visatype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("visa_score", sa.Float, nullable=False),
        sa.Column("max_stay_days", sa.SmallInteger, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("data_year", sa.SmallInteger, nullable=True),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "citizenship_code", "destination_id", name="uq_visa_citizenship_dest"
        ),
        sa.CheckConstraint("visa_score >= 0 AND visa_score <= 1", name="ck_visa_score"),
    )
    op.create_index(
        "ix_visa_rules_citizenship_code", "visa_rules", ["citizenship_code"]
    )
    op.create_index("ix_visa_rules_destination_id", "visa_rules", ["destination_id"])

    # 6. destination_activities (enum first)
    activity_type_enum = postgresql.ENUM(
        "beach",
        "culture",
        "nature",
        "adventure",
        "food",
        "nightlife",
        "wellness",
        "shopping",
        "family",
        "urban",
        name="activitytype",
        create_type=True,
    )
    activity_type_enum.create(op.get_bind())

    op.create_table(
        "destination_activities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "destination_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("destinations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "activity_type",
            postgresql.ENUM(
                "beach",
                "culture",
                "nature",
                "adventure",
                "food",
                "nightlife",
                "wellness",
                "shopping",
                "family",
                "urban",
                name="activitytype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("poi_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "destination_id", "activity_type", name="uq_activity_dest_type"
        ),
        sa.CheckConstraint("score >= 0 AND score <= 1", name="ck_activity_score"),
    )
    op.create_index(
        "ix_destination_activities_destination_id",
        "destination_activities",
        ["destination_id"],
    )

    # 7. poi (enum first)
    poi_source_enum = postgresql.ENUM(
        "opentripmap", "foursquare", name="poisource", create_type=True
    )
    poi_source_enum.create(op.get_bind())

    op.create_table(
        "poi",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("lat", sa.Float, nullable=False),
        sa.Column("lng", sa.Float, nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column(
            "destination_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("destinations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source",
            postgresql.ENUM(
                "opentripmap", "foursquare", name="poisource", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(200), nullable=False),
        sa.Column("rating", sa.Float, nullable=True),
        sa.Column("popularity_score", sa.Float, nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("tags", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
        sa.UniqueConstraint("source", "external_id", name="uq_poi_source_external"),
    )
    op.create_index("ix_poi_destination_id", "poi", ["destination_id"])
    op.create_index("ix_poi_category", "poi", ["category"])
    op.create_index(
        "ix_poi_destination_category", "poi", ["destination_id", "category"]
    )

    # 8. trajectories
    op.create_table(
        "trajectories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "destination_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("destinations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("duration_days", sa.SmallInteger, nullable=False),
        sa.Column(
            "sequence_of_poi", postgresql.JSONB, nullable=False, server_default="[]"
        ),
        sa.Column("source", sa.String(50), nullable=False, server_default="generated"),
        sa.Column(
            "activity_tags", postgresql.JSONB, nullable=False, server_default="[]"
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_trajectories_destination_id", "trajectories", ["destination_id"]
    )


def downgrade() -> None:
    """Drop all data layer tables."""
    op.drop_table("trajectories")
    op.drop_table("poi")
    op.drop_index("ix_destination_activities_destination_id")
    op.drop_table("destination_activities")
    op.drop_index("ix_visa_rules_destination_id")
    op.drop_index("ix_visa_rules_citizenship_code")
    op.drop_table("visa_rules")
    op.drop_table("destination_safety")
    op.drop_table("destination_costs")
    op.drop_table("destination_seasonality")
    op.drop_index("ix_destinations_country_code")
    op.drop_table("destinations")

    # drop enums
    postgresql.ENUM(name="poisource", create_type=False).drop(op.get_bind())
    postgresql.ENUM(name="activitytype", create_type=False).drop(op.get_bind())
    postgresql.ENUM(name="visatype", create_type=False).drop(op.get_bind())
