"""Add airports lookup table for IATA resolution."""

import sqlalchemy as sa
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "airports",
        sa.Column("iata_code", sa.String(length=3), nullable=False),
        sa.Column("ident", sa.String(length=16), nullable=True),
        sa.Column("airport_type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("municipality", sa.String(length=255), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("scheduled_service", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("iata_code"),
    )
    op.create_index("ix_airports_country_code", "airports", ["country_code"], unique=False)
    op.create_index("ix_airports_iata_code", "airports", ["iata_code"], unique=False)
    op.create_index("ix_airports_municipality", "airports", ["municipality"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_airports_municipality", table_name="airports")
    op.drop_index("ix_airports_iata_code", table_name="airports")
    op.drop_index("ix_airports_country_code", table_name="airports")
    op.drop_table("airports")
