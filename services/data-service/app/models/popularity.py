import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class DestinationPopularity(Base):
    __tablename__ = "destination_popularity"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    avg_pageviews: Mapped[int] = mapped_column(Integer, nullable=False)
    crowd_index: Mapped[float] = mapped_column(Float, nullable=False)
    wikipedia_article: Mapped[str | None] = mapped_column(String(300), nullable=True)
    data_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("destination_id", "month", name="uq_popularity_dest_month"),
        CheckConstraint("month >= 1 AND month <= 12", name="ck_popularity_month"),
        CheckConstraint("crowd_index >= 0 AND crowd_index <= 1", name="ck_popularity_crowd_index"),
    )
