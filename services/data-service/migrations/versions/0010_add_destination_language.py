"""Add destination_language_accessibility table (Migration 0010).

Phase 1.2 — language accessibility scores for CIS travelers:
russian_speaking_score, english_speaking_score, script_difficulty,
has_cyrillic_signs, and local_languages (ISO 639-1 list).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "destination_language_accessibility",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "destination_id",
            UUID(as_uuid=True),
            sa.ForeignKey("destinations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("local_languages", JSONB(), nullable=False, server_default="[]"),
        sa.Column("russian_speaking_score", sa.Float(), nullable=False),
        sa.Column("english_speaking_score", sa.Float(), nullable=False),
        sa.Column("has_cyrillic_signs", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("script_difficulty", sa.String(20), nullable=False, server_default="easy"),
        sa.Column("data_source", sa.String(50), nullable=False, server_default="rule_based"),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_destination_language_destination_id",
        "destination_language_accessibility",
        ["destination_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_destination_language_destination_id",
        table_name="destination_language_accessibility",
    )
    op.drop_table("destination_language_accessibility")
