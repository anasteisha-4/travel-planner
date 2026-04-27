import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class DestinationAttributes(Base):
    __tablename__ = "destination_attributes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # Multi-value JSONB arrays
    # dest_type: city|beach|mountain|nature|cultural|ski_resort|spa_resort|island|rural|pilgrimage
    dest_type: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    # vibe: party|relaxation|adventure|cultural|romantic|family|spiritual|luxury|budget|off_beaten
    vibe: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    # best_for: couples|families|solo|groups
    best_for: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    # landscape: sea|mountains|desert|steppe|forest|lake|river
    landscape: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    # beach_type: sea|lake|river|null
    beach_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    has_ski: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    has_thermal: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_coastal: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    altitude_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # hot|warm|mild|cold
    summer_temp_class: Mapped[str | None] = mapped_column(String(10), nullable=True)
    winter_temp_class: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # osm_inferred|manual|llm_enriched
    data_source: Mapped[str] = mapped_column(String(50), nullable=False, server_default="osm_inferred")
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
