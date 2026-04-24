import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

EventType = Literal[
    "recommendation_shown",
    "recommendation_clicked",
    "destination_detail_opened",
    "budget_predicted",
    "trip_created",
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
