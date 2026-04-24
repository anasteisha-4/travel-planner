import uuid
from datetime import datetime

from pydantic import BaseModel


class UserFeaturesResponse(BaseModel):
    user_id: uuid.UUID
    feature_version: int
    computed_at: datetime
    confidence: float | None

    activity_prefs_vector: list[float] | None
    budget_min_usd: float | None
    budget_max_usd: float | None
    preferred_duration_days: int | None
    origin_lat: float | None
    origin_lng: float | None

    viewed_destination_ids: list[str] | None
    clicked_destination_ids: list[str] | None
    session_count: int | None
    avg_session_events: float | None

    completed_trips_count: int | None
    avg_spend_ratio: float | None
    visited_destination_ids: list[str] | None
    avg_destination_rating: float | None
    would_revisit_ratio: float | None

    onboarding_completed: bool

    class Config:
        from_attributes = True
