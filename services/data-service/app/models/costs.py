import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class DestinationCosts(Base):
    __tablename__ = "destination_costs"

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
    avg_meal_cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    avg_transport_cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    avg_hotel_cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    avg_daily_cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    cost_index: Mapped[float] = mapped_column(Float, nullable=False)
    data_source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="numbeo"
    )
    data_quality_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.7
    )
    # Accommodation tiers derived from avg_hotel_cost_usd
    hostel_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    mid_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    luxury_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Monthly cost multipliers derived from crowd_index: {"1": 0.85, ..., "12": 1.10}
    seasonal_multiplier: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
