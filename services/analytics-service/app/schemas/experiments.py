import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ExperimentResponse(BaseModel):
    id: uuid.UUID
    key: str
    description: str | None
    status: str
    variants_json: list[str]
    metrics_json: dict[str, Any] | None
    guardrails_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExperimentAssignmentResponse(BaseModel):
    experiment_key: str
    variant: str


class ExperimentAssignmentsResponse(BaseModel):
    assignments: dict[str, ExperimentAssignmentResponse] = Field(default_factory=dict)


class ExperimentReportResponse(BaseModel):
    experiment_key: str
    variants: dict[str, dict[str, int]]
