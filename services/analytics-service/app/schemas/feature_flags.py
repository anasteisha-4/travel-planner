import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FeatureFlagResponse(BaseModel):
    id: uuid.UUID
    key: str
    description: str | None
    enabled: bool
    rollout_percentage: float
    environment: str
    targeting_json: dict[str, Any] | None
    payload_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FeatureFlagUpdate(BaseModel):
    description: str | None = None
    enabled: bool | None = None
    rollout_percentage: float | None = Field(default=None, ge=0, le=100)
    environment: str | None = None
    targeting_json: dict[str, Any] | None = None
    payload_json: dict[str, Any] | None = None


class EvaluatedFlag(BaseModel):
    key: str
    enabled: bool
    payload: dict[str, Any] = Field(default_factory=dict)


class EvaluatedFlagsResponse(BaseModel):
    flags: dict[str, EvaluatedFlag]
