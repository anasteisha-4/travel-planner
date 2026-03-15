from enum import StrEnum

from sqlalchemy import Column, Date, Enum, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.base_model import BaseModel


class Trip(BaseModel):
    __tablename__ = "trips"
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    destination = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    budget = Column(Float, nullable=True)
    currency = Column(String, nullable=False, default="RUB")
    people_count = Column(Integer, nullable=False, default=1)
    status = Column(String, nullable=False, default="planned")
    trip_type = Column(String, nullable=True)
    season = Column(String, nullable=True)
    departure_city = Column(String, nullable=True)
    notes = Column(Text, nullable=True)


class ExpenseCategory(StrEnum):
    food = "food"
    transport = "transport"
    housing = "housing"
    entertainment = "entertainment"
    shopping = "shopping"
    other = "other"


class Expense(BaseModel):
    __tablename__ = "expenses"
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    category = Column(Enum(ExpenseCategory), nullable=False)
    description = Column(Text, nullable=True)
    expense_date = Column(Date, nullable=True)
