"""Add destination_attributes table (Migration 0009).

Phase 1.1 of dataset expansion — stores destination type classification,
vibe, best_for groups, landscape features, and boolean attributes (ski,
thermal, coastal) used by the recommendation model.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "destination_attributes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "destination_id",
            UUID(as_uuid=True),
            sa.ForeignKey("destinations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("dest_type", JSONB(), nullable=False, server_default="[]"),
        sa.Column("vibe", JSONB(), nullable=False, server_default="[]"),
        sa.Column("best_for", JSONB(), nullable=False, server_default="[]"),
        sa.Column("landscape", JSONB(), nullable=False, server_default="[]"),
        sa.Column("beach_type", sa.String(20), nullable=True),
        sa.Column("has_ski", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("has_thermal", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_coastal", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("altitude_m", sa.Integer(), nullable=True),
        sa.Column("summer_temp_class", sa.String(10), nullable=True),
        sa.Column("winter_temp_class", sa.String(10), nullable=True),
        sa.Column("data_source", sa.String(50), nullable=False, server_default="osm_inferred"),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_destination_attributes_destination_id",
        "destination_attributes",
        ["destination_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_destination_attributes_destination_id", table_name="destination_attributes")
    op.drop_table("destination_attributes")
