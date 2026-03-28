import uuid
from datetime import date
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Date, Enum, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.base_model import BaseModel


class Trip(BaseModel):
    __tablename__ = "trips"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    destination: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="RUB")
    people_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String, nullable=False, default="planned")
    trip_type: Mapped[str | None] = mapped_column(String, nullable=True)
    season: Mapped[str | None] = mapped_column(String, nullable=True)
    departure_city: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ExpenseCategory(StrEnum):
    food = "food"
    transport = "transport"
    housing = "housing"
    entertainment = "entertainment"
    shopping = "shopping"
    other = "other"


class Expense(BaseModel):
    __tablename__ = "expenses"
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    category: Mapped[ExpenseCategory] = mapped_column(Enum(ExpenseCategory), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expense_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class PlaceVisit(BaseModel):
    __tablename__ = "place_visits"
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    visited_at: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    order: Mapped[int | None] = mapped_column(Integer, nullable=True)
