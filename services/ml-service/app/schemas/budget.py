import uuid

from pydantic import BaseModel, Field


class BudgetPredictRequest(BaseModel):
    destination_id: uuid.UUID
    duration_days: int = Field(..., ge=1, le=365)
    people_count: int = Field(default=1, ge=1, le=20)
    travel_month: int = Field(..., ge=1, le=12)
    accommodation_tier: str = "mid"
    currency: str = "USD"


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
    model_version: str
