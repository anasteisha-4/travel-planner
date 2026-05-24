"""add destination ingestion requests

Revision ID: 0024
Revises: 0023
Create Date: 2026-05-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "destination_ingestion_requests",
        sa.Column("destination_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_name", sa.String(length=200), nullable=False),
        sa.Column("requested_country_code", sa.String(length=2), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=60), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("request_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("destination_id", "source", "status", name="uq_destination_ingestion_request_open"),
    )
    op.create_index(
        op.f("ix_destination_ingestion_requests_destination_id"),
        "destination_ingestion_requests",
        ["destination_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_destination_ingestion_requests_requested_country_code"),
        "destination_ingestion_requests",
        ["requested_country_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_destination_ingestion_requests_status"),
        "destination_ingestion_requests",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_destination_ingestion_requests_status"), table_name="destination_ingestion_requests")
    op.drop_index(
        op.f("ix_destination_ingestion_requests_requested_country_code"),
        table_name="destination_ingestion_requests",
    )
    op.drop_index(
        op.f("ix_destination_ingestion_requests_destination_id"),
        table_name="destination_ingestion_requests",
    )
    op.drop_table("destination_ingestion_requests")
