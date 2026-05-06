import enum
import uuid

from sqlalchemy import CheckConstraint, Enum, Float, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.base_model import BaseModel


class NameTranslationEntity(enum.StrEnum):
    destination = "destination"
    poi = "poi"


class NameTranslationQuality(enum.StrEnum):
    manual = "manual"
    authoritative = "authoritative"
    machine = "machine"
    fallback = "fallback"


class NameTranslation(BaseModel):
    __tablename__ = "name_translations"

    entity_type: Mapped[NameTranslationEntity] = mapped_column(
        Enum(NameTranslationEntity, name="nametranslationentity"),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    locale: Mapped[str] = mapped_column(String(8), nullable=False, default="ru", index=True)
    original_name: Mapped[str] = mapped_column(Text, nullable=False)
    translated_name: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    quality: Mapped[NameTranslationQuality] = mapped_column(
        Enum(NameTranslationQuality, name="nametranslationquality"),
        nullable=False,
        default=NameTranslationQuality.authoritative,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    translation_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "locale", name="uq_name_translation_entity_locale"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_name_translation_confidence"),
        Index("ix_name_translation_provider_ref", "provider", "provider_ref"),
    )
