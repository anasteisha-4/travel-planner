"""Add destination_connectivity table (Migration 0011).

Phase 1.3 — connectivity data for CIS travelers:
direct flights from Moscow/SPb/Ekb/Novosibirsk, transit hubs (Dubai/Istanbul/Yerevan/
Tashkent/Tbilisi), train access, flight hours, Mir card acceptance, composite score.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "destination_connectivity",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "destination_id",
            UUID(as_uuid=True),
            sa.ForeignKey("destinations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("direct_from_moscow", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("direct_from_spb", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("direct_from_ekb", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "direct_from_novosibirsk",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("transit_via_dubai", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("transit_via_istanbul", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("transit_via_yerevan", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("transit_via_tashkent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("transit_via_tbilisi", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("train_from_moscow", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("train_hours_from_moscow", sa.Float(), nullable=True),
        sa.Column("flight_hours_from_moscow", sa.Float(), nullable=True),
        sa.Column("min_transit_hours", sa.Float(), nullable=True),
        sa.Column("connectivity_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("mir_card_accepted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("data_source", sa.String(50), nullable=False, server_default="rule_based"),
        sa.Column("data_year", sa.Integer(), nullable=False, server_default="2025"),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_destination_connectivity_destination_id",
        "destination_connectivity",
        ["destination_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_destination_connectivity_destination_id",
        table_name="destination_connectivity",
    )
    op.drop_table("destination_connectivity")
