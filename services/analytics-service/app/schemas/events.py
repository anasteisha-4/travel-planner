import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.services.event_contract import EventType as EventType


class EventPayload(BaseModel):
    event_id: uuid.UUID | None = None
    session_id: uuid.UUID
    event_type: str = Field(..., min_length=1, max_length=80)
    event_version: int | None = Field(None, ge=1)
    entity_type: str | None = Field(None, max_length=30)
    entity_id: str | None = Field(None, max_length=50)
    context: dict | None = Field(default=None)
    client_meta: dict | None = Field(default=None)
    occurred_at: datetime | None = None

    @field_validator("event_type")
    @classmethod
    def normalize_event_type(cls, value: str) -> str:
        return value.strip()


class EventsBatchRequest(BaseModel):
    events: list[EventPayload] = Field(..., min_length=1, max_length=100)


class EventsBatchResponse(BaseModel):
    accepted: int
    warning_count: int = 0
    warnings: list[str] = Field(default_factory=list)
