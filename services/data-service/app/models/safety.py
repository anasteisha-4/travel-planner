import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    SmallInteger,
    String,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class DestinationSafety(Base):
    __tablename__ = "destination_safety"

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
    safety_score: Mapped[float] = mapped_column(Float, nullable=False)
    gpi_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    gpi_rank: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    gpi_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    safety_data_source: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="gpi_country"
    )
    city_adjustment_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "safety_score >= 0 AND safety_score <= 1", name="ck_safety_score"
        ),
    )
