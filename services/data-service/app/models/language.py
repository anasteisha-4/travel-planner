import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class DestinationLanguageAccessibility(Base):
    __tablename__ = "destination_language_accessibility"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # ISO 639-1 codes: ["ru", "en", "tr"]
    local_languages: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    # 0–1: how well Russian-speaking tourists are served
    russian_speaking_score: Mapped[float] = mapped_column(Float, nullable=False)
    # 0–1: how well English-speaking tourists are served
    english_speaking_score: Mapped[float] = mapped_column(Float, nullable=False)
    # True if Cyrillic script is commonly used on signs/menus
    has_cyrillic_signs: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    # easy (Latin/Cyrillic) | moderate (Arabic/Greek/Hebrew/Devanagari) | hard (CJK/Thai/Khmer)
    script_difficulty: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="easy"
    )
    # rule_based | manual
    data_source: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="rule_based"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
