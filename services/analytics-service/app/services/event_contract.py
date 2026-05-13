import logging
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, get_args

CANONICAL_EVENT_VERSION = 1
CONTRACT_VERSION = "2026-05-13"

EventType = Literal[
    "app_opened",
    "page_viewed",
    "session_started",
    "session_ended",
    "login_started",
    "login_succeeded",
    "login_failed",
    "onboarding_step_completed",
    "onboarding_completed",
    "onboarding_abandoned",
    "recommendation_shown",
    "recommendation_impression",
    "recommendation_clicked",
    "destination_detail_opened",
    "recommendation_filter_changed",
    "recommendation_search_started",
    "recommendation_search_result_opened",
    "recommendation_empty_state_shown",
    "budget_predicted",
    "budget_prediction_viewed",
    "budget_prediction_changed",
    "budget_monitor_viewed",
    "budget_risk_shown",
    "validation_viewed",
    "validation_warning_expanded",
    "trip_created",
    "trip_opened",
    "trip_status_changed",
    "itinerary_generated",
    "itinerary_viewed",
    "itinerary_edited",
    "itinerary_variant_generated",
    "itinerary_approved",
    "itinerary_regenerated",
    "itinerary_poi_removed",
    "itinerary_poi_added",
    "itinerary_poi_pinned",
    "itinerary_poi_reordered",
    "itinerary_poi_moved",
    "itinerary_poi_visited",
    "itinerary_day_regenerated",
    "place_visit_marked_visited",
    "expense_added",
    "expense_updated",
    "expense_deleted",
    "post_trip_feedback_submitted",
    "post_trip_feedback_updated",
    "profile_viewed",
    "profile_updated",
    "profile_origin_changed",
    "profile_budget_changed",
    "profile_preferences_changed",
    "currency_changed",
    "rest_level_changed",
    "failed_api_request",
    "slow_api_request",
    "frontend_error",
    "frontend_unhandled_rejection",
    "service_worker_error",
    "network_status_changed",
    "external_api_call_completed",
    "budget_prediction_served",
    "budget_monitor_served",
    "itinerary_candidate_generated",
    "validation_result_served",
    "experiment_exposed",
]

CANONICAL_EVENT_TYPES = set(get_args(EventType))
ENTITY_TYPES = {"destination", "trip", "itinerary", "model", "profile", "user", "experiment"}
FORBIDDEN_CONTEXT_KEYS = {
    "access_token",
    "auth_token",
    "description",
    "email",
    "free_text",
    "login",
    "note",
    "notes",
    "oauth_id",
    "password",
    "refresh_token",
    "token",
}
FORBIDDEN_KEY_PARTS = ("password", "token", "secret", "email", "oauth")

EVENT_REQUIRED_CONTEXT: dict[str, set[str]] = {
    "page_viewed": {"path"},
    "recommendation_impression": {"recommendation_id", "destination_id", "rank", "score", "model_version"},
    "recommendation_shown": {"recommendation_id", "count", "model_version"},
    "recommendation_clicked": {"destination_id", "score"},
    "destination_detail_opened": {"destination_id"},
    "recommendation_filter_changed": {"filter", "value"},
    "validation_viewed": {"destination_id", "travel_month", "warnings_count", "warning_types"},
    "budget_prediction_viewed": {"destination_id", "duration_days", "people_count", "currency", "total_mid"},
    "budget_prediction_changed": {"destination_id", "duration_days", "people_count", "currency", "total_mid"},
    "budget_monitor_viewed": {"trip_id", "status", "projected_final", "currency"},
    "budget_risk_shown": {"trip_id", "risk_status"},
    "validation_warning_expanded": {"destination_id", "warning_type"},
    "trip_created": {"destination", "currency", "people_count", "source"},
    "trip_opened": {"trip_id", "destination", "status", "currency", "has_budget"},
    "trip_status_changed": {"trip_id", "status"},
    "itinerary_viewed": {"trip_id", "destination_id", "duration_days", "has_generated_itinerary"},
    "itinerary_generated": {"trip_id", "destination_id", "duration_days", "days_count", "places_count", "has_template"},
    "itinerary_edited": {"trip_id", "destination_id", "edit_type"},
    "itinerary_approved": {"trip_id", "destination_id"},
    "itinerary_regenerated": {"trip_id", "destination_id"},
    "itinerary_poi_moved": {"trip_id", "item_id"},
    "itinerary_poi_removed": {"trip_id", "item_id"},
    "itinerary_poi_added": {"trip_id"},
    "place_visit_marked_visited": {"trip_id", "place_id"},
    "expense_added": {"trip_id", "expense_id", "amount", "currency", "category"},
    "expense_updated": {"trip_id", "expense_id", "amount", "currency", "category"},
    "expense_deleted": {"trip_id", "expense_id", "currency", "category"},
    "post_trip_feedback_submitted": {"trip_id", "destination", "overall_rating"},
    "post_trip_feedback_updated": {"trip_id", "destination", "overall_rating"},
    "profile_viewed": {"has_preferences", "onboarding_completed"},
    "profile_updated": {"changed_fields"},
    "profile_origin_changed": {"origin_city_name", "has_origin_coords"},
    "profile_budget_changed": {"preferred_currency", "has_budget_min", "has_budget_max"},
    "profile_preferences_changed": {"vacation_preferences_count", "liked_destinations_count", "language_comfort_count"},
    "currency_changed": {"preferred_currency"},
    "rest_level_changed": {"rest_level"},
    "failed_api_request": {"method", "path"},
    "slow_api_request": {"method", "path", "duration_ms"},
    "frontend_error": {"message"},
    "network_status_changed": {"status"},
    "external_api_call_completed": {"provider", "duration_ms", "ok"},
    "budget_prediction_served": {"destination_id", "model_version", "p10", "p50", "p90", "currency"},
    "budget_monitor_served": {"trip_id", "model_version", "current_spend", "projected_final", "risk_status"},
    "itinerary_candidate_generated": {"trip_id", "itinerary_id", "ranker_version", "days", "places"},
    "validation_result_served": {"destination_id", "travel_month", "warnings_count", "warning_types"},
    "experiment_exposed": {"experiment_id", "variant"},
    "onboarding_step_completed": {"step"},
}

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ContractResult:
    event_type: str
    entity_type: str | None
    entity_id: str | None
    context: dict[str, Any] | None
    client_meta: dict[str, Any]
    warnings: list[str]


def _is_forbidden_key(key: str) -> bool:
    normalized = key.lower()
    return normalized in FORBIDDEN_CONTEXT_KEYS or any(part in normalized for part in FORBIDDEN_KEY_PARTS)


def sanitize_json(value: Any, removed_keys: set[str] | None = None) -> Any:
    if removed_keys is None:
        removed_keys = set()

    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            if _is_forbidden_key(key):
                removed_keys.add(key)
                continue
            sanitized[key] = sanitize_json(raw_value, removed_keys)
        return sanitized

    if isinstance(value, list):
        return [sanitize_json(item, removed_keys) for item in value]

    return value


def normalize_entity(
    event_type: str, entity_type: str | None, entity_id: str | None, context: Mapping[str, Any]
) -> tuple[str | None, str | None]:
    normalized_type = entity_type.lower().strip() if entity_type else None
    normalized_id = str(entity_id).strip() if entity_id is not None else None

    if normalized_type not in ENTITY_TYPES:
        normalized_type = None

    if normalized_type is None:
        if destination_id := context.get("destination_id"):
            normalized_type = "destination"
            normalized_id = str(destination_id)
        elif trip_id := context.get("trip_id"):
            normalized_type = "trip"
            normalized_id = str(trip_id)
        elif itinerary_id := context.get("itinerary_id"):
            normalized_type = "itinerary"
            normalized_id = str(itinerary_id)
        elif event_type.startswith("profile_") or event_type.startswith("onboarding_"):
            normalized_type = "profile"

    return normalized_type, normalized_id


def validate_event_contract(
    *,
    event_id: uuid.UUID | None,
    event_type: str,
    entity_type: str | None,
    entity_id: str | None,
    context: dict[str, Any] | None,
    client_meta: dict[str, Any] | None,
    request_id: str | None,
    environment: str,
    service_version: str,
) -> ContractResult:
    warnings: list[str] = []
    removed_context_keys: set[str] = set()
    removed_meta_keys: set[str] = set()
    sanitized_context = sanitize_json(context or {}, removed_context_keys)
    sanitized_meta = sanitize_json(client_meta or {}, removed_meta_keys)

    if event_type not in CANONICAL_EVENT_TYPES:
        warnings.append(f"unknown_event_type:{event_type}")
    else:
        required = EVENT_REQUIRED_CONTEXT.get(event_type, set())
        missing = sorted(required.difference(sanitized_context.keys()))
        if missing:
            warnings.append(f"missing_context:{event_type}:{','.join(missing)}")

    if removed_context_keys:
        warnings.append(f"removed_forbidden_context_keys:{','.join(sorted(removed_context_keys))}")
    if removed_meta_keys:
        warnings.append(f"removed_forbidden_client_meta_keys:{','.join(sorted(removed_meta_keys))}")

    normalized_entity_type, normalized_entity_id = normalize_entity(
        event_type,
        entity_type,
        entity_id,
        sanitized_context,
    )

    server_meta = {
        "service": "analytics-service",
        "service_version": service_version,
        "environment": environment,
        "event_contract_version": CONTRACT_VERSION,
        "event_version_default": CANONICAL_EVENT_VERSION,
        "request_id": request_id,
    }
    merged_meta = {
        **sanitized_meta,
        "event_id": str(event_id) if event_id else None,
        "server": server_meta,
    }
    if warnings:
        merged_meta["contract_warnings"] = warnings
        logger.warning("analytics event contract warnings", extra={"event_type": event_type, "warnings": warnings})

    return ContractResult(
        event_type=event_type,
        entity_type=normalized_entity_type,
        entity_id=normalized_entity_id,
        context=sanitized_context or None,
        client_meta=merged_meta,
        warnings=warnings,
    )
