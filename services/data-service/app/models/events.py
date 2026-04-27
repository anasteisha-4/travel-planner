import enum
import uuid

from sqlalchemy import Boolean, Float, ForeignKey, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EventCategory(enum.StrEnum):
    festival = "festival"
    holiday = "holiday"
    religious = "religious"
    carnival = "carnival"
    sports = "sports"
    music = "music"
    food = "food"
    arts = "arts"


class DestinationEvent(Base):
    __tablename__ = "destination_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_ru: Mapped[str | None] = mapped_column(String(200), nullable=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    month_start: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    month_end: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    day_start: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    day_end: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    is_annual: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    crowd_impact: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.5")
    price_impact: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.5")
    traveler_relevance: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.5")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_source: Mapped[str] = mapped_column(String(50), nullable=False, server_default="seed_csv")
