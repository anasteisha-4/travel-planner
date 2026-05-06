import uuid

from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    travel_month: int = Field(..., ge=1, le=12)
    limit: int = Field(default=10, ge=1, le=50)
    exclude_destination_ids: list[uuid.UUID] = Field(default_factory=list)
    region: str | None = None
    citizenship_code: str = "RU"
    model_version: str | None = None


class ScoredDestination(BaseModel):
    destination_id: uuid.UUID
    name: str
    name_original: str | None = None
    name_ru: str | None = None
    display_name: str | None = None
    country_code: str
    region: str
    score: float
    score_breakdown: dict[str, float]
    explanation_tags: list[str]
    avg_daily_cost_usd: float | None
    season_score: float | None
    safety_score: float | None


class RecommendResponse(BaseModel):
    recommendation_id: uuid.UUID
    model_version: str
    results: list[ScoredDestination]
