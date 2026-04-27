import uuid

from sqlalchemy import Float, ForeignKey, SmallInteger, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.base_model import BaseModel


class TripBudgetActual(BaseModel):
    __tablename__ = "trip_budget_actuals"

    trip_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    duration_days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    people_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    travel_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    total_actual_usd: Mapped[float] = mapped_column(Float, nullable=False)
    meals_usd: Mapped[float] = mapped_column(Float, nullable=False)
    accommodation_usd: Mapped[float] = mapped_column(Float, nullable=False)
    transport_usd: Mapped[float] = mapped_column(Float, nullable=False)
    activities_usd: Mapped[float] = mapped_column(Float, nullable=False)
    accommodation_tier: Mapped[str] = mapped_column(String(20), nullable=False)
    data_source: Mapped[str] = mapped_column(String(50), nullable=False, default="synthetic")
