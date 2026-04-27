import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, Float, Integer, SmallInteger, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class UserFeatures(Base):
    __tablename__ = "user_features"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    feature_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    computed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Layer 1: from profile
    activity_prefs_vector: Mapped[list[float] | None] = mapped_column(ARRAY(Float), nullable=True)
    budget_min_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_max_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    preferred_duration_days: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    origin_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    origin_lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Layer 2: from events (behavioral)
    viewed_destination_ids: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    clicked_destination_ids: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    session_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_session_events: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Layer 3: from trips
    completed_trips_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_spend_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    visited_destination_ids: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    avg_destination_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    would_revisit_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)

    onboarding_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
