import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.base_model import BaseModel
from app.database import Base


class Destination(BaseModel):
    __tablename__ = "destinations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subregion: Mapped[str | None] = mapped_column(String(100), nullable=True)
    capital: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    population: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    currencies: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    radius_m: Mapped[int] = mapped_column(Integer, nullable=False, default=20000)

    seasonality: Mapped[list["DestinationSeasonality"]] = relationship(
        back_populates="destination", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("name", "country_code", name="uq_destination_name_country"),)


class DestinationIngestionStatus(enum.StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class DestinationIngestionRequest(BaseModel):
    __tablename__ = "destination_ingestion_requests"

    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_name: Mapped[str] = mapped_column(String(200), nullable=False)
    requested_country_code: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    status: Mapped[DestinationIngestionStatus] = mapped_column(
        String(20),
        nullable=False,
        default=DestinationIngestionStatus.pending,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(60), nullable=False, default="osm_external_route")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint(
            "destination_id",
            "source",
            "status",
            name="uq_destination_ingestion_request_open",
        ),
    )


class DestinationSeasonality(Base):
    __tablename__ = "destination_seasonality"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    avg_temp_c: Mapped[float] = mapped_column(Float, nullable=False)
    avg_precipitation_mm: Mapped[float] = mapped_column(Float, nullable=False)
    avg_humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    season_score: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    destination: Mapped["Destination"] = relationship(back_populates="seasonality")

    __table_args__ = (
        UniqueConstraint("destination_id", "month", name="uq_seasonality_dest_month"),
        CheckConstraint("month >= 1 AND month <= 12", name="ck_seasonality_month"),
        CheckConstraint("season_score >= 0 AND season_score <= 1", name="ck_seasonality_score"),
    )
