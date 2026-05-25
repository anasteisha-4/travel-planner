import uuid
from datetime import date, datetime, time
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    ARRAY,
    Boolean,
    Date,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.base_model import BaseModel


class Trip(BaseModel):
    __tablename__ = "trips"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    destination: Mapped[str] = mapped_column(String, nullable=False)
    destination_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="RUB")
    people_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    rest_days_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String, nullable=False, default="planned")
    trip_type: Mapped[str | None] = mapped_column(String, nullable=True)
    season: Mapped[str | None] = mapped_column(String, nullable=True)
    departure_city: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ExpenseCategory(StrEnum):
    food = "food"
    transport = "transport"
    travel_to_destination = "travel_to_destination"
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
    is_one_time: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")


class UserProfile(BaseModel):
    __tablename__ = "user_profiles"
    __table_args__ = (
        Index("ix_user_profiles_liked_destination_ids", "liked_destination_ids", postgresql_using="gin"),
        Index("ix_user_profiles_vacation_preferences_ranked", "vacation_preferences_ranked", postgresql_using="gin"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    vacation_preferences_ranked: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    preferred_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")
    budget_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    budget_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    budget_min_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    budget_max_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    rest_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    typical_duration: Mapped[str | None] = mapped_column(String(20), nullable=True)
    typical_duration_days: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    origin_city_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    origin_city_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    origin_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    origin_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    citizenship_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    liked_destination_ids: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    liked_destination_names: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    risk_tolerance: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    visa_tolerance: Mapped[str | None] = mapped_column(String(20), nullable=True)
    language_comfort: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    crowd_preference: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    climate_preferences: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    free_text_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    onboarding_step: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(nullable=True)


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


class TripItinerary(BaseModel):
    __tablename__ = "trip_itineraries"
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    variant_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generation_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False, default="heuristic-itinerary-v2")
    route_signature: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    constraints: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    score_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class ItineraryGenerationJob(BaseModel):
    __tablename__ = "itinerary_generation_jobs"
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", index=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="generate")
    request_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_itinerary_ids: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)


class PushSubscription(BaseModel):
    __tablename__ = "push_subscriptions"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    p256dh: Mapped[str] = mapped_column(Text, nullable=False)
    auth: Mapped[str] = mapped_column(Text, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)


class TripItineraryDay(BaseModel):
    __tablename__ = "trip_itinerary_days"
    itinerary_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trip_itineraries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    day_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    theme: Mapped[str | None] = mapped_column(String(80), nullable=True)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)


class TripItineraryItem(BaseModel):
    __tablename__ = "trip_itinerary_items"
    day_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trip_itinerary_days.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    poi_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    arrival_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    departure_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    travel_from_previous_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="generated")
    opening_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    price_tier: Mapped[str | None] = mapped_column(String(20), nullable=True)
    entrance_fee_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_removed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    visited_place_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
