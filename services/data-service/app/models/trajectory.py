from sqlalchemy import ForeignKey, SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.base_model import BaseModel


class Trajectory(BaseModel):
    __tablename__ = "trajectories"

    destination_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    duration_days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    sequence_of_poi: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="generated")
    activity_tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
