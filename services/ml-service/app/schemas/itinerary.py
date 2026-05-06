import uuid
from datetime import date

from pydantic import BaseModel, Field


class ItineraryGenerateRequest(BaseModel):
    destination_id: uuid.UUID
    duration_days: int = Field(..., ge=1, le=30)
    start_date: date
    preferred_activities: list[str] | None = None


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
    visit_duration_minutes: int | None = None


class ItineraryDay(BaseModel):
    day: int
    theme: str
    places: list[ItineraryPlace]


class ItineraryGenerateResponse(BaseModel):
    destination_id: uuid.UUID
    duration_days: int
    days: list[ItineraryDay]
    activity_tags: list[str]
    source: str = "template-based"
    has_template: bool = True
    message: str | None = None
