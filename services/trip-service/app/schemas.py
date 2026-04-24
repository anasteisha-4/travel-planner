from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


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


class UserProfileCreate(BaseModel):
    preferred_currency: str = "RUB"
    budget_min: Decimal | None = None
    budget_max: Decimal | None = None
    typical_duration: str | None = None
    origin_city_id: int | None = None
    origin_city_name: str | None = None
    origin_lat: float | None = None
    origin_lng: float | None = None
    vacation_preferences_ranked: Annotated[list[str], Field(max_length=5)] | None = None
    liked_destination_ids: Annotated[list[str], Field(max_length=10)] | None = None
    liked_destination_names: Annotated[list[str], Field(max_length=10)] | None = None
    risk_tolerance: Annotated[int, Field(ge=1, le=5)] | None = None
    visa_tolerance: str | None = None
    language_comfort: list[str] | None = None
    crowd_preference: Annotated[int, Field(ge=1, le=5)] | None = None
    climate_preferences: Annotated[list[str], Field(max_length=3)] | None = None
    free_text_notes: str | None = None

    @field_validator("budget_max")
    @classmethod
    def budget_max_gte_min(cls, v: Decimal | None, info: object) -> Decimal | None:
        if v is not None:
            data = getattr(info, "data", {})
            budget_min = data.get("budget_min")
            if budget_min is not None and v < budget_min:
                raise ValueError("budget_max must be >= budget_min")
        return v

    @field_validator("vacation_preferences_ranked")
    @classmethod
    def max_five_prefs(cls, v: list[str] | None) -> list[str] | None:
        if v is not None and len(v) > 5:
            raise ValueError("vacation_preferences_ranked can have at most 5 items")
        return v


class UserProfileUpdate(BaseModel):
    preferred_currency: str | None = None
    budget_min: Decimal | None = None
    budget_max: Decimal | None = None
    typical_duration: str | None = None
    origin_city_id: int | None = None
    origin_city_name: str | None = None
    origin_lat: float | None = None
    origin_lng: float | None = None
    vacation_preferences_ranked: list[str] | None = None
    liked_destination_ids: list[str] | None = None
    liked_destination_names: list[str] | None = None
    risk_tolerance: Annotated[int, Field(ge=1, le=5)] | None = None
    visa_tolerance: str | None = None
    language_comfort: list[str] | None = None
    crowd_preference: Annotated[int, Field(ge=1, le=5)] | None = None
    climate_preferences: list[str] | None = None
    free_text_notes: str | None = None


class UserProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    preferred_currency: str
    budget_min: Decimal | None
    budget_max: Decimal | None
    budget_min_usd: Decimal | None
    budget_max_usd: Decimal | None
    typical_duration: str | None
    typical_duration_days: int | None
    origin_city_id: int | None
    origin_city_name: str | None
    origin_lat: float | None
    origin_lng: float | None
    vacation_preferences_ranked: list[str] | None
    liked_destination_ids: list[str] | None
    liked_destination_names: list[str] | None
    risk_tolerance: int | None
    visa_tolerance: str | None
    language_comfort: list[str] | None
    crowd_preference: int | None
    climate_preferences: list[str] | None
    free_text_notes: str | None
    onboarding_completed: bool
    onboarding_step: int
    onboarding_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OnboardingStepPayload(BaseModel):
    preferred_currency: str | None = None
    budget_min: Decimal | None = None
    budget_max: Decimal | None = None
    typical_duration: str | None = None
    origin_city_id: int | None = None
    origin_city_name: str | None = None
    origin_lat: float | None = None
    origin_lng: float | None = None
    vacation_preferences_ranked: list[str] | None = None
    liked_destination_ids: list[str] | None = None
    liked_destination_names: list[str] | None = None
    risk_tolerance: int | None = None
    visa_tolerance: str | None = None
    language_comfort: list[str] | None = None
    crowd_preference: int | None = None
    climate_preferences: list[str] | None = None
    free_text_notes: str | None = None
