import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, Float, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class PostTripFeedback(Base):
    __tablename__ = "post_trip_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    trip_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True, unique=True)
    destination: Mapped[str] = mapped_column(String(200), nullable=False)

    overall_rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    destination_rating: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    value_rating: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    actual_total_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)

    would_revisit: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    free_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
