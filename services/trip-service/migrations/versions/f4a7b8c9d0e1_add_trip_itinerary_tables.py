"""add trip itinerary tables

Revision ID: f4a7b8c9d0e1
Revises: e75c42234afc
Create Date: 2026-05-11 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f4a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e75c42234afc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trip_itineraries",
        sa.Column("trip_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("variant_index", sa.Integer(), nullable=False),
        sa.Column("generation_seed", sa.Integer(), nullable=True),
        sa.Column("model_version", sa.String(length=80), nullable=False),
        sa.Column("route_signature", sa.String(length=500), nullable=True),
        sa.Column("constraints", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("score_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trip_itineraries_route_signature"), "trip_itineraries", ["route_signature"], unique=False)
    op.create_index(op.f("ix_trip_itineraries_status"), "trip_itineraries", ["status"], unique=False)
    op.create_index(op.f("ix_trip_itineraries_trip_id"), "trip_itineraries", ["trip_id"], unique=False)
    op.create_index(op.f("ix_trip_itineraries_user_id"), "trip_itineraries", ["user_id"], unique=False)

    op.create_table(
        "trip_itinerary_days",
        sa.Column("itinerary_id", sa.UUID(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("day_number", sa.SmallInteger(), nullable=False),
        sa.Column("theme", sa.String(length=80), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["itinerary_id"], ["trip_itineraries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trip_itinerary_days_date"), "trip_itinerary_days", ["date"], unique=False)
    op.create_index(op.f("ix_trip_itinerary_days_itinerary_id"), "trip_itinerary_days", ["itinerary_id"], unique=False)

    op.create_table(
        "trip_itinerary_items",
        sa.Column("day_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("trip_id", sa.UUID(), nullable=False),
        sa.Column("poi_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("arrival_time", sa.Time(), nullable=True),
        sa.Column("departure_time", sa.Time(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("travel_from_previous_minutes", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("opening_status", sa.String(length=40), nullable=True),
        sa.Column("price_tier", sa.String(length=20), nullable=True),
        sa.Column("entrance_fee_usd", sa.Float(), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("is_pinned", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_removed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("visited_place_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["day_id"], ["trip_itinerary_days.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trip_itinerary_items_day_id"), "trip_itinerary_items", ["day_id"], unique=False)
    op.create_index(op.f("ix_trip_itinerary_items_poi_id"), "trip_itinerary_items", ["poi_id"], unique=False)
    op.create_index(op.f("ix_trip_itinerary_items_trip_id"), "trip_itinerary_items", ["trip_id"], unique=False)
    op.create_index(op.f("ix_trip_itinerary_items_user_id"), "trip_itinerary_items", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_trip_itinerary_items_visited_place_id"),
        "trip_itinerary_items",
        ["visited_place_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_trip_itinerary_items_visited_place_id"), table_name="trip_itinerary_items")
    op.drop_index(op.f("ix_trip_itinerary_items_user_id"), table_name="trip_itinerary_items")
    op.drop_index(op.f("ix_trip_itinerary_items_trip_id"), table_name="trip_itinerary_items")
    op.drop_index(op.f("ix_trip_itinerary_items_poi_id"), table_name="trip_itinerary_items")
    op.drop_index(op.f("ix_trip_itinerary_items_day_id"), table_name="trip_itinerary_items")
    op.drop_table("trip_itinerary_items")
    op.drop_index(op.f("ix_trip_itinerary_days_itinerary_id"), table_name="trip_itinerary_days")
    op.drop_index(op.f("ix_trip_itinerary_days_date"), table_name="trip_itinerary_days")
    op.drop_table("trip_itinerary_days")
    op.drop_index(op.f("ix_trip_itineraries_user_id"), table_name="trip_itineraries")
    op.drop_index(op.f("ix_trip_itineraries_trip_id"), table_name="trip_itineraries")
    op.drop_index(op.f("ix_trip_itineraries_status"), table_name="trip_itineraries")
    op.drop_index(op.f("ix_trip_itineraries_route_signature"), table_name="trip_itineraries")
    op.drop_table("trip_itineraries")
