import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Enum,
    Float,
    ForeignKey,
    Integer,
    TIMESTAMP,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class ActivityType(str, enum.Enum):
    beach = "beach"
    culture = "culture"
    nature = "nature"
    adventure = "adventure"
    food = "food"
    nightlife = "nightlife"
    wellness = "wellness"
    shopping = "shopping"
    family = "family"
    urban = "urban"


class DestinationActivity(Base):
    __tablename__ = "destination_activities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity_type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType, name="activitytype"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    poi_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "destination_id", "activity_type", name="uq_activity_dest_type"
        ),
        CheckConstraint("score >= 0 AND score <= 1", name="ck_activity_score"),
    )
