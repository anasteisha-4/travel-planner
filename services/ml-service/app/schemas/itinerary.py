import uuid
from datetime import date

from pydantic import BaseModel, Field

from app.schemas.llm_quality import LLMCandidatePOI, LLMQualityReview


class ItineraryGenerateRequest(BaseModel):
    trip_id: uuid.UUID | None = None
    destination_id: uuid.UUID | None = None
    destination_text: str | None = Field(default=None, max_length=200)
    duration_days: int = Field(..., ge=1, le=30)
    start_date: date
    preferred_activities: list[str] | None = None
    variant_count: int = Field(default=1, ge=1, le=3)
    variant_seed: int | None = None
    pace: str = "standard"
    day_start_time: str = "09:30"
    day_end_time: str = "19:00"
    rest_days_count: int = Field(default=0, ge=0, le=30)
    exclude_signature: str | None = None
    trip_budget: float | None = Field(default=None, ge=0)
    currency: str = "USD"
    people_count: int = Field(default=1, ge=1, le=20)
    trip_notes: str | None = None
    origin_city_name: str | None = Field(default=None, max_length=120)
    allow_external_route: bool = False


class ItineraryPlace(BaseModel):
    id: uuid.UUID
    name: str
    name_original: str | None = None
    name_ru: str | None = None
    display_name: str | None = None
    category: str
    lat: float | None = None
    lng: float | None = None
    address: str | None = None
    opening_hours: str | None = None
    is_open_at_midday: bool | None = None
    opening_status: str | None = None
    arrival_time: str | None = None
    departure_time: str | None = None
    travel_from_previous_minutes: int = 0
    visit_duration_minutes: int | None = None
    duration_minutes: int | None = None
    price_tier: str | None = None
    entrance_fee_usd: float | None = None
    score: float | None = None
    quality_review: LLMQualityReview | None = None
    external_candidate_source: str | None = None


class ItineraryDay(BaseModel):
    day: int
    day_number: int | None = None
    theme: str
    start_time: str | None = None
    end_time: str | None = None
    places: list[ItineraryPlace]
    items: list[ItineraryPlace] = Field(default_factory=list)
    total_score: float | None = None
    quality_review: LLMQualityReview | None = None


class ItineraryGenerateResponse(BaseModel):
    destination_id: uuid.UUID
    duration_days: int
    variant_index: int = 0
    variant_seed: int | None = None
    route_signature: str | None = None
    model_version: str = "itinerary-poi-ranker-v1"
    days: list[ItineraryDay]
    activity_tags: list[str]
    source: str = "optimized-heuristic"
    has_template: bool = True
    message: str | None = None
    score_summary: dict = Field(default_factory=dict)
    quality_model_version: str | None = None
    quality_review: LLMQualityReview | None = None
    candidate_poi: list[LLMCandidatePOI] = Field(default_factory=list)
    variants: list["ItineraryGenerateResponse"] = Field(default_factory=list)
