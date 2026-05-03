from sqlalchemy import Boolean, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.base_model import BaseModel


class Airport(BaseModel):
    __tablename__ = "airports"
    __table_args__ = (
        Index("ix_airports_iata_code", "iata_code"),
        Index("ix_airports_municipality", "municipality"),
        Index("ix_airports_country_code", "country_code"),
    )

    iata_code: Mapped[str] = mapped_column(String(3), nullable=False, unique=True)
    ident: Mapped[str | None] = mapped_column(String(16), nullable=True)
    airport_type: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    municipality: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    scheduled_service: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
