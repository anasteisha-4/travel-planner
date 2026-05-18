import json
import uuid
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import settings
from app.models.llm_quality import LLMReviewLog
from app.schemas.llm_quality import LLMQualityReview, LLMReviewStatus
from app.services.llm.cache import get_cached_review, make_cache_key, set_cached_review
from app.services.llm.prompts import (
    ITINERARY_QUALITY_PROMPT_VERSION,
    ITINERARY_QUALITY_TEMPLATE,
    RECOMMENDATION_QUALITY_PROMPT_VERSION,
    RECOMMENDATION_QUALITY_TEMPLATE,
    compact_json,
    quality_review_json_schema,
)
from app.services.llm.providers import LLMMessage, LLMProvider, LLMProviderError, LLMRequest, get_provider
from app.services.llm.sanitizer import sanitize_context

_LLM_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="llm-quality")


class LLMQualityGate:
    def __init__(self, provider: LLMProvider | None = None):
        self.provider = provider or get_provider()

    def review_recommendations(
        self,
        *,
        db: Session,
        user_id: uuid.UUID,
        recommendation_id: uuid.UUID,
        context: dict,
    ) -> LLMQualityReview:
        return self.review(
            db=db,
            user_id=user_id,
            entity_type="recommendation_set",
            entity_id=str(recommendation_id),
            prompt=RECOMMENDATION_QUALITY_TEMPLATE,
            prompt_version=RECOMMENDATION_QUALITY_PROMPT_VERSION,
            context=context,
            max_tokens=3200,
            timeout_seconds=min(settings.LLM_TIMEOUT_SECONDS, 12.0),
            max_retries=0,
        )

    def review_itinerary(
        self,
        *,
        db: Session,
        user_id: uuid.UUID,
        itinerary_id: str,
        context: dict,
    ) -> LLMQualityReview:
        return self.review(
            db=db,
            user_id=user_id,
            entity_type="itinerary",
            entity_id=itinerary_id,
            prompt=ITINERARY_QUALITY_TEMPLATE,
            prompt_version=ITINERARY_QUALITY_PROMPT_VERSION,
            context=context,
            max_tokens=2200,
            timeout_seconds=min(settings.LLM_TIMEOUT_SECONDS, 8.0),
            max_retries=0,
        )

    def review(
        self,
        *,
        db: Session,
        user_id: uuid.UUID,
        entity_type: str,
        entity_id: str,
        prompt: str,
        prompt_version: str,
        context: dict,
        cache_enabled: bool = True,
        max_tokens: int = 2200,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> LLMQualityReview:
        model = settings.LLM_MODEL
        sanitized_context = sanitize_context(context, max_note_chars=settings.LLM_NOTES_MAX_CHARS)
        cache_key = make_cache_key(
            entity_type=entity_type,
            entity_id=entity_id,
            model=model,
            prompt_version=prompt_version,
            context=sanitized_context,
        )
        if cache_enabled:
            cached = get_cached_review(cache_key)
            if cached:
                review = LLMQualityReview.model_validate(cached)
                review_id = self._save_log(
                    db=db,
                    user_id=user_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    review=review,
                    request_summary={"prompt_version": prompt_version, "context": sanitized_context},
                    response=review.model_dump(mode="json"),
                    latency_ms=0,
                    cache_hit=True,
                    error_code=None,
                    input_hash=cache_key.rsplit(":", 1)[-1],
                )
                return review.model_copy(update={"review_id": review_id})

        request = LLMRequest(
            model=model,
            temperature=0.1,
            max_tokens=max_tokens,
            messages=[
                LLMMessage(role="system", content=prompt),
                LLMMessage(
                    role="user", content=compact_json({"prompt_version": prompt_version, "context": sanitized_context})
                ),
            ],
            json_schema=quality_review_json_schema(),
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        response_payload: dict | None = None
        try:
            response, review, payload = self._complete_and_validate(
                request=request,
                provider_name=settings.LLM_PROVIDER,
                model=model,
                prompt_version=prompt_version,
                timeout_seconds=timeout_seconds,
            )
            response_payload = payload
            if cache_enabled:
                set_cached_review(cache_key, review.model_copy(update={"review_id": None}).model_dump(mode="json"))
            review_id = self._save_log(
                db=db,
                user_id=user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                review=review,
                request_summary={"prompt_version": prompt_version, "context": sanitized_context},
                response=payload,
                latency_ms=response.latency_ms,
                cache_hit=False,
                error_code=None,
                input_hash=cache_key.rsplit(":", 1)[-1],
            )
            return review.model_copy(update={"review_id": review_id})
        except Exception as exc:
            if not settings.LLM_FAIL_OPEN:
                raise
            error_code = _error_code(exc)
            response_payload = _failure_response_payload(exc)
            review = self._failure_review(
                provider=settings.LLM_PROVIDER,
                model=model,
                prompt_version=prompt_version,
                error_code=error_code,
                detail=str(exc),
            )
            review_id = self._save_log(
                db=db,
                user_id=user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                review=review,
                request_summary={"prompt_version": prompt_version, "context": sanitized_context},
                response=response_payload,
                latency_ms=None,
                cache_hit=False,
                error_code=error_code,
                input_hash=cache_key.rsplit(":", 1)[-1],
            )
            return review.model_copy(update={"review_id": review_id})

    def _complete_and_validate(
        self,
        *,
        request: LLMRequest,
        provider_name: str,
        model: str,
        prompt_version: str,
        timeout_seconds: float | None,
    ) -> tuple[Any, LLMQualityReview, dict]:
        response = _complete_with_deadline(self.provider, request, timeout_seconds)
        try:
            return _validate_response_payload(
                response=response,
                provider_name=provider_name,
                model=model,
                prompt_version=prompt_version,
            )
        except (json.JSONDecodeError, ValidationError):
            retry_request = LLMRequest(
                model=request.model,
                temperature=0,
                max_tokens=min(request.max_tokens, 2000),
                messages=_strict_retry_messages(request.messages),
                json_schema=request.json_schema,
                timeout_seconds=request.timeout_seconds,
                max_retries=0,
            )
            try:
                retry_response = _complete_with_deadline(self.provider, retry_request, timeout_seconds)
                return _validate_response_payload(
                    response=retry_response,
                    provider_name=provider_name,
                    model=model,
                    prompt_version=prompt_version,
                )
            except (json.JSONDecodeError, ValidationError) as retry_error:
                raise LLMInvalidReviewResponseError(
                    "invalid_json_or_schema",
                    "LLM response did not match the quality review contract",
                    response_content=response.content,
                    retry_response_content=getattr(locals().get("retry_response", None), "content", None),
                ) from retry_error
            except LLMProviderError:
                raise
            except Exception as retry_error:
                raise LLMInvalidReviewResponseError(
                    "invalid_json_or_schema",
                    "LLM review retry failed after initial invalid response",
                    response_content=response.content,
                ) from retry_error

    def _failure_review(
        self,
        *,
        provider: str,
        model: str,
        prompt_version: str,
        error_code: str,
        detail: str,
    ) -> LLMQualityReview:
        return LLMQualityReview(
            status=LLMReviewStatus.skipped,
            confidence=0,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            issues=[],
            suggested_adjustments=[],
            user_summary_ru=None,
            defense_trace=f"LLM quality review failed open: {error_code}: {detail}",
        )

    def _save_log(
        self,
        *,
        db: Session,
        user_id: uuid.UUID,
        entity_type: str,
        entity_id: str,
        review: LLMQualityReview,
        request_summary: dict | None,
        response: dict | None,
        latency_ms: int | None,
        cache_hit: bool,
        error_code: str | None,
        input_hash: str,
    ) -> uuid.UUID | None:
        try:
            log = LLMReviewLog(
                user_id=user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                provider=review.provider or settings.LLM_PROVIDER,
                model=review.model or settings.LLM_MODEL,
                prompt_version=review.prompt_version,
                input_hash=input_hash,
                status=review.status.value,
                latency_ms=latency_ms,
                issue_codes=[issue.code for issue in review.issues],
                cache_hit=cache_hit,
                error_code=error_code,
                request_summary=request_summary,
                response=response or review.model_dump(mode="json"),
            )
            db.add(log)
            db.commit()
            db.refresh(log)
            return log.id
        except Exception:
            db.rollback()
            return None


def _complete_with_deadline(provider: LLMProvider, request: LLMRequest, timeout_seconds: float | None):
    if timeout_seconds is None:
        return provider.complete(request)
    future = _LLM_EXECUTOR.submit(provider.complete, request)
    try:
        return future.result(timeout=timeout_seconds + 0.5)
    except TimeoutError as exc:
        future.cancel()
        raise LLMProviderError("provider_timeout", "LLM provider exceeded interactive deadline") from exc


class LLMInvalidReviewResponseError(LLMProviderError):
    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        response_content: str | None = None,
        retry_response_content: str | None = None,
    ):
        super().__init__(error_code, message)
        self.response_content = response_content
        self.retry_response_content = retry_response_content


def _error_code(exc: Exception) -> str:
    if isinstance(exc, json.JSONDecodeError | ValidationError):
        return "invalid_json_or_schema"
    return getattr(exc, "error_code", exc.__class__.__name__)


def _failure_response_payload(exc: Exception) -> dict | None:
    first = getattr(exc, "response_content", None)
    retry = getattr(exc, "retry_response_content", None)
    if first is None and retry is None:
        return None
    return {
        "raw_response_sample": _sample_text(first),
        "retry_raw_response_sample": _sample_text(retry),
    }


def _sample_text(value: Any, max_chars: int = 2000) -> str | None:
    if value is None:
        return None
    return str(value)[:max_chars]


def _strict_retry_messages(messages: list[LLMMessage]) -> list[LLMMessage]:
    strict_instruction = (
        "Return only one valid compact JSON object matching the supplied schema. "
        "No markdown. No comments. No trailing text. Use null for unknown nullable fields. "
        "Use at most 2 issues and at most 2 adjustments."
    )
    system_parts = [strict_instruction]
    user_messages: list[LLMMessage] = []
    for message in messages:
        if message.role == "system":
            system_parts.append(message.content)
        else:
            user_messages.append(message)
    return [LLMMessage(role="system", content=" ".join(system_parts)), *user_messages]


def _loads_json_object(content: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            return json.loads(content[start : end + 1])
        raise


def _validate_response_payload(
    *,
    response,
    provider_name: str,
    model: str,
    prompt_version: str,
) -> tuple[Any, LLMQualityReview, dict]:
    payload = _loads_json_object(response.content)
    payload = _normalize_review_payload(payload)
    payload["provider"] = provider_name
    payload["model"] = response.model or model
    payload["prompt_version"] = prompt_version
    review = LLMQualityReview.model_validate(payload)
    review = _normalize_review_status(review)
    return response, review, review.model_dump(mode="json")


def _normalize_review_payload(payload: dict) -> dict:
    normalized = dict(payload)
    raw_issues = (
        normalized.get("issues")
        or normalized.get("problems")
        or normalized.get("findings")
        or normalized.get("warnings")
        or normalized.get("review_issues")
    )
    raw_adjustments = (
        normalized.get("suggested_adjustments")
        or normalized.get("adjustments")
        or normalized.get("recommendation_adjustments")
        or normalized.get("ranking_adjustments")
        or normalized.get("suggestions")
    )
    normalized["issues"] = [_normalize_issue(item) for item in _as_list(raw_issues)]
    normalized["suggested_adjustments"] = [_normalize_adjustment(item) for item in _as_list(raw_adjustments)]
    normalized.setdefault("user_summary_ru", None)
    normalized.setdefault("defense_trace", None)
    return normalized


def _normalize_review_status(review: LLMQualityReview) -> LLMQualityReview:
    if review.status in {LLMReviewStatus.skipped, LLMReviewStatus.failed}:
        return review
    if any(issue.severity.value == "critical" for issue in review.issues):
        return review.model_copy(update={"status": LLMReviewStatus.reject})
    if any(issue.severity.value == "warning" for issue in review.issues):
        return review.model_copy(update={"status": LLMReviewStatus.caution})
    return review


def _normalize_issue(item: Any) -> dict:
    if not isinstance(item, Mapping):
        return {
            "code": "llm_quality_issue",
            "severity": "warning",
            "message": str(item),
            "evidence": [],
        }
    source = _flatten_nested_payload(item, ("issue", "problem", "details"))
    target_id = (
        source.get("destination_id")
        or source.get("target_destination_id")
        or source.get("target_id")
        or source.get("id")
    )
    code = source.get("code") or source.get("issue_code") or source.get("type") or source.get("category")
    code = code or _infer_issue_code(source.get("message") or source.get("reason") or source.get("description"))
    severity = _normalize_severity(source.get("severity"))
    message = (
        source.get("message") or source.get("reason") or source.get("description") or source.get("explanation") or code
    )
    return {
        **dict(source),
        "code": str(code),
        "severity": severity,
        "message": str(message),
        "evidence": _as_list(source.get("evidence")),
        "destination_id": _nullable_uuidish(target_id),
        "target_id": _nullable_uuidish(source.get("target_id")),
        "item_id": _nullable_uuidish(source.get("item_id")),
        "day": source.get("day"),
    }


def _normalize_adjustment(item: Any) -> dict:
    if not isinstance(item, Mapping):
        return {"action": "note", "reason": str(item)}
    source = _flatten_nested_payload(item, ("adjustment", "suggestion", "change"))
    action = source.get("action") or source.get("type") or "note"
    reason = source.get("reason") or source.get("message") or source.get("description") or str(action)
    target_id = (
        source.get("target_id")
        or source.get("destination_id")
        or source.get("target_destination_id")
        or source.get("id")
    )
    replacement_id = source.get("replacement_id") or source.get("replacement_destination_id")
    return {
        **dict(source),
        "action": _normalize_action(action),
        "reason": str(reason),
        "target_id": _nullable_uuidish(target_id),
        "target_destination_id": _nullable_uuidish(source.get("target_destination_id") or target_id),
        "replacement_id": _nullable_uuidish(replacement_id),
        "target_day": source.get("target_day"),
        "target_order": source.get("target_order"),
        "candidate_poi": _normalize_candidate_poi(source.get("candidate_poi")),
        "payload": _normalize_payload(source.get("payload")),
    }


def _flatten_nested_payload(item: Mapping, nested_keys: tuple[str, ...]) -> dict:
    merged = dict(item)
    for key in nested_keys:
        nested = item.get(key)
        if isinstance(nested, Mapping):
            merged.update(
                {nested_key: nested_value for nested_key, nested_value in nested.items() if nested_value is not None}
            )
    return merged


def _nullable_uuidish(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "n/a", "unknown"}:
        return None
    return text


def _normalize_candidate_poi(value: Any) -> dict | None:
    if not isinstance(value, Mapping):
        return None
    return {
        "name": str(value.get("name") or value.get("display_name") or "Suggested place"),
        "category": value.get("category"),
        "lat": value.get("lat") or value.get("latitude"),
        "lng": value.get("lng") or value.get("longitude"),
        "address": value.get("address"),
        "source_url": value.get("source_url"),
        "official_url": value.get("official_url"),
        "suggested_visit_duration_minutes": value.get("suggested_visit_duration_minutes")
        or value.get("visit_duration_minutes"),
        "opening_hours": value.get("opening_hours"),
        "estimated_price": value.get("estimated_price"),
        "estimated_price_currency": value.get("estimated_price_currency"),
        "price_source_url": value.get("price_source_url"),
        "confidence": value.get("confidence"),
        "reason": value.get("reason"),
    }


def _normalize_payload(value: Any) -> dict | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        note = value.get("notes") or value.get("reason") or value.get("message")
        return {"notes": str(note) if note is not None else None}
    return {"notes": str(value)}


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _normalize_severity(value: Any) -> str:
    normalized = str(value or "warning").lower()
    if normalized in {"critical", "high", "severe", "reject"}:
        return "critical"
    if normalized in {"info", "low", "note"}:
        return "info"
    return "warning"


def _normalize_action(value: Any) -> str:
    normalized = str(value or "note").lower()
    aliases = {
        "penalize": "demote",
        "penalty": "demote",
        "downrank": "demote",
        "lower_rank": "demote",
        "lower": "demote",
        "deprioritize": "demote",
        "delete": "remove",
        "exclude": "remove",
        "replace": "remove",
        "raise_rank": "promote",
        "up_rank": "promote",
    }
    normalized = aliases.get(normalized, normalized)
    allowed = {
        "note",
        "demote",
        "promote",
        "remove",
        "swap",
        "regenerate",
        "replace_item",
        "adjust_time",
        "add_candidate_poi",
        "generate_external_route",
    }
    return normalized if normalized in allowed else "note"


def _infer_issue_code(value: Any) -> str:
    text = str(value or "").lower()
    if any(part in text for part in ("safe", "risk", "crime", "conflict", "опас")):
        return "safety_fit"
    if any(part in text for part in ("beach", "пляж", "coast", "sea")):
        return "beach_fit"
    if any(part in text for part in ("budget", "expensive", "cost", "дорог")):
        return "budget_fit"
    if any(part in text for part in ("visa", "виза")):
        return "visa_fit"
    return "llm_quality_issue"
