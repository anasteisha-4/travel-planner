from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class TripStatus(StrEnum):
    planned = "planned"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class TripCreate(BaseModel):
    destination: str
    start_date: date
    end_date: date
    budget: float | None = None
    currency: str = "RUB"
    people_count: int = 1
    trip_type: str | None = None
    season: str | None = None
    departure_city: str | None = None
    notes: str | None = None


class TripUpdate(BaseModel):
    destination: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    budget: float | None = None
    currency: str | None = None
    people_count: int | None = None
    status: TripStatus | None = None
    trip_type: str | None = None
    season: str | None = None
    departure_city: str | None = None
    notes: str | None = None


class TripResponse(BaseModel):
    id: UUID
    user_id: UUID
    destination: str
    start_date: date
    end_date: date
    budget: float | None
    currency: str
    people_count: int
    status: TripStatus
    trip_type: str | None = None
    season: str | None = None
    departure_city: str | None = None
    notes: str | None
    created_at: str
    updated_at: str | None

    class Config:
        from_attributes = True


class ExpenseCategory(StrEnum):
    food = "food"
    transport = "transport"
    housing = "housing"
    entertainment = "entertainment"
    shopping = "shopping"
    other = "other"


class ExpenseCreate(BaseModel):
    amount: Decimal
    currency: str
    category: ExpenseCategory
    description: str | None = None
    expense_date: date | None = None


class ExpenseUpdate(BaseModel):
    amount: Decimal | None = None
    currency: str | None = None
    category: ExpenseCategory | None = None
    description: str | None = None
    expense_date: date | None = None


class ExpenseResponse(BaseModel):
    id: UUID
    trip_id: UUID
    user_id: UUID
    amount: Decimal
    currency: str
    category: ExpenseCategory
    description: str | None
    expense_date: date | None
    created_at: str
    updated_at: str | None

    class Config:
        from_attributes = True


class ExpenseSummary(BaseModel):
    total: Decimal
    by_category: dict[str, Decimal]


class ConvertedExpenseSummary(BaseModel):
    total: Decimal
    by_category: dict[str, Decimal]
    target_currency: str
    original_currencies: list[str]
    has_conversion_errors: bool = False


class ExchangeRatesResponse(BaseModel):
    base: str
    rates: dict[str, float]


class PlaceVisitCreate(BaseModel):
    name: str
    visited_at: date
    latitude: Decimal
    longitude: Decimal
    notes: str | None = None


class PlaceVisitUpdate(BaseModel):
    name: str | None = None
    visited_at: date | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    notes: str | None = None


class PlaceVisitResponse(BaseModel):
    id: UUID
    trip_id: UUID
    user_id: UUID
    name: str
    visited_at: date
    latitude: Decimal
    longitude: Decimal
    notes: str | None
    order: int | None
    created_at: str
    updated_at: str | None

    class Config:
        from_attributes = True


class PlaceVisitReorder(BaseModel):
    date: date
    place_ids: list[UUID]


class PlaceVisitsByDate(BaseModel):
    date: date
    places: list[PlaceVisitResponse]
