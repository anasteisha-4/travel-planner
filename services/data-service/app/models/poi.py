import enum

from sqlalchemy import (
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.base_model import BaseModel


class POISource(enum.StrEnum):
    opentripmap = "opentripmap"
    overpass_osm = "overpass_osm"
    heritage = "heritage"  # UNESCO World Heritage Sites + OSM protected areas


class POI(BaseModel):
    __tablename__ = "poi"

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    destination_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[POISource] = mapped_column(Enum(POISource, name="poisource"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(200), nullable=False)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    popularity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    visit_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opening_hours: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_tier: Mapped[str | None] = mapped_column(String(20), nullable=True)
    entrance_fee_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    fee_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_poi_source_external"),
        Index("ix_poi_destination_category", "destination_id", "category"),
    )
