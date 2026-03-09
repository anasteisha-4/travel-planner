from datetime import date
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class TripStatus(str, Enum):
    planned = "planned"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class TripCreate(BaseModel):
    title: str
    destination: str
    start_date: date
    end_date: date
    budget: float | None = None
    currency: str = "RUB"
    people_count: int = 1
    notes: str | None = None


class TripUpdate(BaseModel):
    title: str | None = None
    destination: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    budget: float | None = None
    currency: str | None = None
    people_count: int | None = None
    status: TripStatus | None = None
    notes: str | None = None


class TripResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    destination: str
    start_date: date
    end_date: date
    budget: float | None
    currency: str
    people_count: int
    status: TripStatus
    notes: str | None
    created_at: str
    updated_at: str | None

    class Config:
        from_attributes = True
