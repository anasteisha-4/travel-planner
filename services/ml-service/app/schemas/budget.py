import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class BudgetPredictRequest(BaseModel):
    destination_id: uuid.UUID
    duration_days: int = Field(..., ge=1, le=365)
    people_count: int = Field(default=1, ge=1, le=20)
    travel_month: int = Field(..., ge=1, le=12)
    accommodation_tier: str = "mid"
    currency: str = "USD"
    budget_limit_usd: float | None = Field(default=None, ge=0)
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


class BudgetMonitorExpense(BaseModel):
    amount: float = Field(..., ge=0)
    currency: str = "USD"
    category: str
    expense_date: date | None = None
    description: str | None = None
    converted_amount: float | None = Field(default=None, ge=0)


class BudgetMonitorItinerarySummary(BaseModel):
    generated_days_count: int = Field(default=0, ge=0, le=365)
    remaining_days_count: int = Field(default=0, ge=0, le=365)
    remaining_poi_count: int = Field(default=0, ge=0)
    remaining_food_poi_count: int = Field(default=0, ge=0)
    remaining_paid_poi_count: int = Field(default=0, ge=0)
    remaining_estimated_entrance_fees: float = Field(default=0, ge=0)
    avg_visit_duration_minutes: float | None = Field(default=None, ge=0)


class BudgetMonitorPreTripPrediction(BaseModel):
    total_min: float | None = Field(default=None, ge=0)
    total_mid: float | None = Field(default=None, ge=0)
    total_max: float | None = Field(default=None, ge=0)
    breakdown: dict[str, float] = Field(default_factory=dict)
    model_version: str | None = None


class BudgetMonitorRequest(BaseModel):
    trip_id: uuid.UUID | None = None
    destination_id: uuid.UUID | None = None
    start_date: date
    end_date: date
    as_of_date: date | None = None
    people_count: int = Field(default=1, ge=1, le=20)
    currency: str = "USD"
    trip_budget: float | None = Field(default=None, ge=0)
    accommodation_tier: str = "mid"
    expenses: list[BudgetMonitorExpense] = Field(default_factory=list)
    pre_trip_prediction: BudgetMonitorPreTripPrediction | None = None
    itinerary_summary: BudgetMonitorItinerarySummary | None = None


class BudgetMonitorCategoryContribution(BaseModel):
    category: str
    spent: float
    remaining_mid: float
    kind: str


class BudgetMonitorResponse(BaseModel):
    currency: str
    current_spent: float
    locked_fixed_costs: float
    recurring_spent: float
    optional_activity_spent: float
    remaining_min: float
    remaining_mid: float
    remaining_max: float
    projected_final_min: float
    projected_final_mid: float
    projected_final_max: float
    budget_limit: float | None = None
    budget_gap_mid: float | None = None
    budget_usage_projected_pct: float | None = None
    risk_status: str
    category_contributions: list[BudgetMonitorCategoryContribution]
    assumptions: dict
    model_version: str
    baseline_version: str
    used_ml_model: bool


class ModelVersionResponse(BaseModel):
    id: str
    name: str
    version: str
    model_type: str
    is_active: bool
    metrics: dict | None
    trained_at: datetime | None
    created_at: datetime
