"""Add destination_infrastructure table (Migration 0013).

Phase 1.5 — infrastructure data for CIS travelers:
metro availability, taxi apps, road quality, internet speed,
healthcare, ATM density, cash economy flag.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "destination_infrastructure",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "destination_id",
            UUID(as_uuid=True),
            sa.ForeignKey("destinations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("has_metro", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "taxi_app_available", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column("road_quality_score", sa.Float(), nullable=True),
        sa.Column("avg_internet_mbps", sa.Float(), nullable=True),
        sa.Column("healthcare_score", sa.Float(), nullable=True),
        sa.Column(
            "atm_density_score", sa.Float(), nullable=False, server_default="0.5"
        ),
        sa.Column("cash_economy", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "data_source", sa.String(50), nullable=False, server_default="rule_based"
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_destination_infrastructure_destination_id",
        "destination_infrastructure",
        ["destination_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_destination_infrastructure_destination_id", "destination_infrastructure"
    )
    op.drop_table("destination_infrastructure")
