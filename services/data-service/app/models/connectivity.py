import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class DestinationConnectivity(Base):
    __tablename__ = "destination_connectivity"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # Direct flights from major Russian cities
    direct_from_moscow: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    direct_from_spb: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    direct_from_ekb: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    direct_from_novosibirsk: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    # Transit hubs (post-2022 relevant for Russian travelers)
    transit_via_dubai: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    transit_via_istanbul: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    transit_via_yerevan: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    transit_via_tashkent: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    transit_via_tbilisi: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    # Ground transport
    train_from_moscow: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    train_hours_from_moscow: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Travel time
    flight_hours_from_moscow: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_transit_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Composite score: 0.5*direct_msk + 0.3*(1-transit/20) + 0.2*ground
    connectivity_score: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    # Payment
    mir_card_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    # Metadata
    data_source: Mapped[str] = mapped_column(String(50), nullable=False, server_default="rule_based")
    data_year: Mapped[int] = mapped_column(Integer, nullable=False, server_default="2025")
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
