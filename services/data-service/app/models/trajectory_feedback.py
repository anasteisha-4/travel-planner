import uuid

from sqlalchemy import Boolean, ForeignKey, SmallInteger, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.base_model import BaseModel


class TrajectoryFeedback(BaseModel):
    __tablename__ = "trajectory_feedback"

    trajectory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trajectories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    was_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    people_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    trip_duration_days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="synthetic")
