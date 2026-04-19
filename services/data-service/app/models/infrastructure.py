import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class DestinationInfrastructure(Base):
    __tablename__ = "destination_infrastructure"

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
    # Public transport
    has_metro: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    # Taxi apps (Yandex.Taxi for CIS, Uber global)
    taxi_app_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    # Road quality (0–1, LPI Infrastructure WB LP.LPI.INFR.XQ normalized)
    road_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Internet speed (Mbps, Speedtest Global Index 2024 by country)
    avg_internet_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Healthcare (0–1, WB SP.DYN.LE00.IN life expectancy normalized)
    healthcare_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # ATM density (0–1, WB FB.ATM.TOTL.P5 per 100k adults normalized)
    atm_density_score: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0.5"
    )
    # Cash economy flag (WB FX.OWN.TOTL.ZS account ownership < 50%)
    cash_economy: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    # Metadata
    data_source: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="rule_based"
    )
    # Per-field data source provenance: {"internet_mbps": "speedtest_2024", "healthcare": "wb_le_2022", ...}
    data_source_details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
