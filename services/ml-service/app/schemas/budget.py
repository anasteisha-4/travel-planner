import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class BudgetPredictRequest(BaseModel):
    destination_id: uuid.UUID
    duration_days: int = Field(..., ge=1, le=365)
    people_count: int = Field(default=1, ge=1, le=20)
    travel_month: int = Field(..., ge=1, le=12)
    accommodation_tier: str = "mid"
    currency: str = "USD"
    origin_city_name: str | None = None
    origin_lat: float | None = Field(default=None, ge=-90, le=90)
    origin_lng: float | None = Field(default=None, ge=-180, le=180)


class BudgetAssumptions(BaseModel):
    duration_days: int
    people_count: int
    accommodation_tier: str
    travel_month: int
    currency: str
    origin_city_name: str | None
    origin_lat: float | None
    origin_lng: float | None
    origin_source: str
    travel_distance_km: float | None
    travel_cost_source: str
    origin_iata: str | None = None
    destination_iata: str | None = None
    flight_fare_strategy: str | None = None
    flight_trip_class: int | None = None
    flight_fare_found_at: str | None = None
    flight_fare_expires_at: str | None = None


class BudgetPredictResponse(BaseModel):
    destination_id: uuid.UUID
    duration_days: int
    people_count: int
    currency: str
    total_min: float
    total_mid: float
    total_max: float
    daily_cost_usd: float
    breakdown: dict[str, float]
    assumptions: BudgetAssumptions
    model_version: str


class ModelVersionResponse(BaseModel):
    id: str
    name: str
    version: str
    model_type: str
    is_active: bool
    metrics: dict | None
    trained_at: datetime | None
    created_at: datetime
