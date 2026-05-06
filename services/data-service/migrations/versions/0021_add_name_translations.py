"""add name translations overlay

Revision ID: 0021
Revises: 0020
Create Date: 2026-05-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    entity_enum = postgresql.ENUM("destination", "poi", name="nametranslationentity", create_type=False)
    quality_enum = postgresql.ENUM(
        "manual", "authoritative", "machine", "fallback", name="nametranslationquality", create_type=False
    )
    entity_enum.create(op.get_bind(), checkfirst=True)
    quality_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "name_translations",
        sa.Column("entity_type", entity_enum, nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("original_name", sa.Text(), nullable=False),
        sa.Column("translated_name", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_ref", sa.String(length=200), nullable=True),
        sa.Column("quality", quality_enum, nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("translation_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_name_translation_confidence"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_type", "entity_id", "locale", name="uq_name_translation_entity_locale"),
    )
    op.create_index("ix_name_translation_entity_id", "name_translations", ["entity_id"], unique=False)
    op.create_index("ix_name_translation_entity_type", "name_translations", ["entity_type"], unique=False)
    op.create_index("ix_name_translation_locale", "name_translations", ["locale"], unique=False)
    op.create_index("ix_name_translation_provider_ref", "name_translations", ["provider", "provider_ref"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_name_translation_provider_ref", table_name="name_translations")
    op.drop_index("ix_name_translation_locale", table_name="name_translations")
    op.drop_index("ix_name_translation_entity_type", table_name="name_translations")
    op.drop_index("ix_name_translation_entity_id", table_name="name_translations")
    op.drop_table("name_translations")
    postgresql.ENUM(name="nametranslationquality").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="nametranslationentity").drop(op.get_bind(), checkfirst=True)
