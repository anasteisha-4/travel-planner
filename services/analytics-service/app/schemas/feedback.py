import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PostTripFeedbackCreate(BaseModel):
    trip_id: str = Field(..., max_length=50)
    destination: str = Field(..., max_length=200)
    overall_rating: int = Field(..., ge=1, le=5)
    destination_rating: int | None = Field(None, ge=1, le=5)
    value_rating: int | None = Field(None, ge=1, le=5)
    actual_total_cost: float | None = None
    actual_currency: str | None = Field(None, max_length=3)
    would_revisit: bool | None = None
    free_text: str | None = None


class PostTripFeedbackUpdate(BaseModel):
    overall_rating: int | None = Field(None, ge=1, le=5)
    destination_rating: int | None = Field(None, ge=1, le=5)
    value_rating: int | None = Field(None, ge=1, le=5)
    actual_total_cost: float | None = None
    actual_currency: str | None = Field(None, max_length=3)
    would_revisit: bool | None = None
    free_text: str | None = None


class PostTripFeedbackResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    trip_id: str
    destination: str
    overall_rating: int
    destination_rating: int | None
    value_rating: int | None
    actual_total_cost: float | None
    actual_currency: str | None
    would_revisit: bool | None
    free_text: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class PendingFeedbackItem(BaseModel):
    trip_id: str
    destination: str
    completed_at: str | None
