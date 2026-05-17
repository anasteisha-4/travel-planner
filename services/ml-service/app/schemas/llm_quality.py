import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class LLMReviewStatus(StrEnum):
    ok = "ok"
    caution = "caution"
    reject = "reject"
    skipped = "skipped"
    failed = "failed"


class LLMReviewSeverity(StrEnum):
    info = "info"
    warning = "warning"
    critical = "critical"


class LLMReviewAction(StrEnum):
    note = "note"
    demote = "demote"
    promote = "promote"
    remove = "remove"
    swap = "swap"
    regenerate = "regenerate"
    replace_item = "replace_item"
    adjust_time = "adjust_time"
    add_candidate_poi = "add_candidate_poi"
    generate_external_route = "generate_external_route"


class LLMCandidatePOI(BaseModel):
    candidate_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: str | None = None
    lat: float | None = None
    lng: float | None = None
    address: str | None = None
    source_url: str | None = None
    official_url: str | None = None
    suggested_visit_duration_minutes: int | None = None
    opening_hours: str | None = None
    estimated_price: float | None = None
    estimated_price_currency: str | None = None
    price_source_url: str | None = None
    confidence: float | None = None
    reason: str | None = None
    evidence: dict[str, Any] | None = None


class LLMReviewIssue(BaseModel):
    code: str
    severity: LLMReviewSeverity
    message: str
    evidence: list[str] = Field(default_factory=list)
    destination_id: uuid.UUID | None = None
    target_id: uuid.UUID | None = None
    item_id: uuid.UUID | None = None
    day: int | None = None


class LLMReviewAdjustment(BaseModel):
    action: LLMReviewAction
    reason: str
    target_id: uuid.UUID | None = None
    target_destination_id: uuid.UUID | None = None
    replacement_id: uuid.UUID | None = None
    target_day: int | None = None
    target_order: int | None = None
    candidate_poi: LLMCandidatePOI | None = None
    payload: dict[str, Any] | None = None


class LLMQualityReview(BaseModel):
    review_id: uuid.UUID | None = None
    status: LLMReviewStatus
    confidence: float = Field(default=0, ge=0, le=1)
    provider: str | None = None
    model: str | None = None
    prompt_version: str
    issues: list[LLMReviewIssue] = Field(default_factory=list)
    suggested_adjustments: list[LLMReviewAdjustment] = Field(default_factory=list)
    user_summary_ru: str | None = None
    defense_trace: str | None = None
