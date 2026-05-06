import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

EventType = Literal[
    "recommendation_shown",
    "recommendation_impression",
    "recommendation_clicked",
    "destination_detail_opened",
    "budget_predicted",
    "budget_prediction_viewed",
    "budget_prediction_changed",
    "validation_viewed",
    "trip_created",
    "trip_created_from_recommendation",
    "trip_opened",
    "trip_status_changed",
    "itinerary_generated",
    "itinerary_viewed",
    "itinerary_edited",
    "expense_added",
    "expense_updated",
    "post_trip_feedback_submitted",
    "post_trip_feedback_updated",
    "profile_viewed",
    "profile_updated",
    "profile_origin_changed",
    "profile_budget_changed",
    "profile_preferences_changed",
    "recommendation_filter_changed",
    "onboarding_step_completed",
    "onboarding_completed",
]


class EventPayload(BaseModel):
    session_id: uuid.UUID
    event_type: EventType
    entity_type: str | None = Field(None, max_length=30)
    entity_id: str | None = Field(None, max_length=50)
    context: dict | None = None
    client_meta: dict | None = None
    occurred_at: datetime | None = None


class EventsBatchRequest(BaseModel):
    events: list[EventPayload] = Field(..., min_length=1, max_length=100)


class EventsBatchResponse(BaseModel):
    accepted: int
