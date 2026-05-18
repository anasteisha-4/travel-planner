import uuid

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user_id
from app.exceptions import AppException
from app.models.llm_quality import LLMCandidatePOILog
from app.observability import record_llm_candidate_poi
from app.schemas.itinerary import (
    ItineraryDay,
    ItineraryGenerateRequest,
    ItineraryGenerateResponse,
    ItineraryPlace,
)
from app.schemas.llm_quality import LLMQualityReview, LLMReviewStatus
from app.services.analytics_events import emit_ml_quality_event
from app.services.llm.candidate_poi_validation import CandidatePOIValidationResult
from app.services.llm.external_route import generate_external_route
from app.services.llm.itinerary_adjustment_policy import ItineraryAdjustmentResult, apply_itinerary_quality_review
from app.services.llm.itinerary_context import build_itinerary_context
from app.services.llm.prompts import ITINERARY_QUALITY_PROMPT_VERSION
from app.services.llm.quality_gate import LLMQualityGate
from app.services.profile_client import _get_profile_sync

router = APIRouter()


def _data_service_secret() -> str:
    return settings.INTERNAL_API_SECRET or settings.DATA_SERVICE_SECRET


def _activity_preferences(profile: dict, request: ItineraryGenerateRequest) -> list[str]:
    if request.preferred_activities:
        return request.preferred_activities

    ranked = profile.get("vacation_preferences_ranked") or []
    if isinstance(ranked, list):
        values = [str(item.get("value") if isinstance(item, dict) else item) for item in ranked]
        values = [v for v in values if v and v != "None"]
        if values:
            return values

    vector = profile.get("activity_prefs_vector") or {}
    if isinstance(vector, dict):
        scored = sorted(
            ((str(key), float(value)) for key, value in vector.items() if value is not None),
            key=lambda item: item[1],
            reverse=True,
        )
        return [key for key, value in scored[:5] if value > 0]

    return []


def _params(request: ItineraryGenerateRequest, activities: list[str]) -> list[tuple[str, str | int | float]]:
    params: list[tuple[str, str | int | float]] = [
        ("duration_days", request.duration_days),
        ("start_date", request.start_date.isoformat()),
        ("variant_count", request.variant_count),
        ("pace", request.pace),
        ("day_start_time", request.day_start_time),
        ("day_end_time", request.day_end_time),
        ("rest_days_count", request.rest_days_count),
        ("people_count", request.people_count),
    ]
    if request.destination_id is not None:
        params.append(("destination_id", str(request.destination_id)))
    if request.variant_seed is not None:
        params.append(("variant_seed", request.variant_seed))
    if request.exclude_signature:
        params.append(("exclude_signature", request.exclude_signature))
    if request.trip_budget is not None:
        params.append(("trip_budget", request.trip_budget))
    params.extend(("preferred_activities", activity) for activity in activities)
    return params


def _normalize_variant(request: ItineraryGenerateRequest, payload: dict) -> ItineraryGenerateResponse:
    error = payload.get("error")
    if error:
        return ItineraryGenerateResponse(
            destination_id=request.destination_id,
            duration_days=request.duration_days,
            days=[],
            activity_tags=[],
            has_template=False,
            message=str(error),
        )

    days = [
        ItineraryDay(
            day=int(day.get("day") or index + 1),
            day_number=int(day.get("day_number") or day.get("day") or index + 1),
            theme=str(day.get("theme") or "urban"),
            start_time=day.get("start_time"),
            end_time=day.get("end_time"),
            places=[
                ItineraryPlace(
                    id=uuid.UUID(str(place.get("id") or place.get("poi_id"))),
                    name=str(place.get("name") or "Untitled place"),
                    name_original=place.get("name_original"),
                    name_ru=place.get("name_ru"),
                    display_name=place.get("display_name") or place.get("name_ru") or place.get("name"),
                    category=str(place.get("category") or "place"),
                    lat=place.get("lat"),
                    lng=place.get("lng"),
                    address=place.get("address"),
                    opening_hours=place.get("opening_hours"),
                    is_open_at_midday=place.get("is_open_at_midday"),
                    opening_status=place.get("opening_status"),
                    arrival_time=place.get("arrival_time"),
                    departure_time=place.get("departure_time"),
                    travel_from_previous_minutes=int(place.get("travel_from_previous_minutes") or 0),
                    visit_duration_minutes=place.get("visit_duration_minutes"),
                    duration_minutes=place.get("duration_minutes"),
                    price_tier=place.get("price_tier"),
                    entrance_fee_usd=place.get("entrance_fee_usd"),
                    score=place.get("score"),
                )
                for place in day.get("items", day.get("places", []))
                if place.get("id") or place.get("poi_id")
            ],
            items=[],
            total_score=day.get("total_score"),
        )
        for index, day in enumerate(payload.get("days", []))
    ]
    for day in days:
        day.items = day.places

    return ItineraryGenerateResponse(
        destination_id=uuid.UUID(str(payload.get("destination_id") or request.destination_id)),
        duration_days=int(payload.get("duration_days") or request.duration_days),
        variant_index=int(payload.get("variant_index") or 0),
        variant_seed=payload.get("variant_seed"),
        route_signature=payload.get("route_signature"),
        model_version=str(payload.get("model_version") or "itinerary-poi-ranker-v1"),
        days=days,
        activity_tags=[str(tag) for tag in payload.get("activity_tags", [])],
        source=str(payload.get("source") or "optimized-heuristic"),
        score_summary=payload.get("score_summary") or {},
    )


def _normalize_response(request: ItineraryGenerateRequest, payload: dict) -> ItineraryGenerateResponse:
    normalized = _normalize_variant(request, payload)
    normalized.variants = [_normalize_variant(request, item) for item in payload.get("variants", [])]
    return normalized


def _destination_info(destination_id: uuid.UUID) -> dict | None:
    try:
        response = httpx.get(f"{settings.DATA_SERVICE_URL}/api/destinations/{destination_id}", timeout=2.0)
        if response.status_code == 200:
            return response.json()
    except httpx.HTTPError:
        return None
    return None


def _not_reviewed() -> LLMQualityReview:
    return LLMQualityReview(
        status=LLMReviewStatus.skipped,
        confidence=0,
        provider=None,
        model=None,
        prompt_version=ITINERARY_QUALITY_PROMPT_VERSION,
        issues=[],
        suggested_adjustments=[],
        user_summary_ru=None,
        defense_trace="Variant was not reviewed because itinerary quality gate reviews only the first variant by default.",
    )


def _review_response(
    *,
    db: Session,
    user_id: uuid.UUID,
    profile: dict,
    request: ItineraryGenerateRequest,
    response: ItineraryGenerateResponse,
) -> ItineraryGenerateResponse:
    if not response.has_template or not response.days:
        return response

    destination_info = _destination_info(response.destination_id) if request.destination_id else None
    if not settings.LLM_QUALITY_ENABLED:
        return response

    variants = response.variants or [response]
    reviewed_variants: list[ItineraryGenerateResponse] = []

    for index, variant in enumerate(variants):
        if index > 0:
            summary = _not_reviewed()
            reviewed_variants.append(
                variant.model_copy(
                    update={
                        "quality_review": summary,
                        "quality_model_version": settings.LLM_MODEL,
                        "score_summary": _quality_score_summary(variant, summary, [], []),
                    }
                )
            )
            continue

        context = build_itinerary_context(
            profile=profile,
            request=request,
            itinerary=variant,
            destination_info=destination_info,
        )
        review = LLMQualityGate().review_itinerary(
            db=db,
            user_id=user_id,
            itinerary_id=variant.route_signature or str(variant.variant_index),
            context=context,
        )
        if variant.source != "external-fallback" and _review_requests_external_route(review):
            external = generate_external_route(
                db=db,
                user_id=user_id,
                trip_id=request.trip_id,
                request=request,
                profile=profile,
                destination_info=destination_info,
                trigger="llm_reject_regenerate",
            )
            if external is not None:
                reviewed_variants.append(external)
                continue
        adjusted = apply_itinerary_quality_review(variant, review, db=db)
        priced_itinerary = adjusted.itinerary
        final_review = _review_after_repairs(review, adjusted)
        priced_itinerary = _attach_review_targets(priced_itinerary, final_review)
        if final_review is not review:
            priced_itinerary = _clear_item_quality_reviews(priced_itinerary)
        _save_candidate_poi_logs(
            db=db,
            destination_id=variant.destination_id,
            review=review,
            candidate_results=adjusted.candidate_results,
        )
        reviewed_variants.append(
            priced_itinerary.model_copy(
                update={
                    "quality_review": final_review,
                    "quality_model_version": settings.LLM_MODEL,
                    "score_summary": _quality_score_summary(
                        priced_itinerary,
                        final_review,
                        adjusted.applied_adjustments,
                        adjusted.ignored_adjustments,
                        adjusted.candidate_results,
                    ),
                }
            )
        )

    first = reviewed_variants[0] if reviewed_variants else response
    if response.variants:
        reviewed_variants = _prefer_non_rejected_variants(reviewed_variants)
        first = reviewed_variants[0] if reviewed_variants else first
        return first.model_copy(update={"variants": reviewed_variants})
    return first


def _prefer_non_rejected_variants(variants: list[ItineraryGenerateResponse]) -> list[ItineraryGenerateResponse]:
    if len(variants) <= 1:
        return variants
    rejected = [
        variant
        for variant in variants
        if variant.quality_review is not None and variant.quality_review.status == LLMReviewStatus.reject
    ]
    if not rejected:
        return variants
    preferred = [
        variant
        for variant in variants
        if variant.quality_review is None or variant.quality_review.status != LLMReviewStatus.reject
    ]
    return preferred + rejected


def _review_requests_external_route(review: LLMQualityReview) -> bool:
    if review.status != LLMReviewStatus.reject:
        return False
    return any(
        adjustment.action.value in {"generate_external_route", "regenerate"}
        for adjustment in review.suggested_adjustments
    )


def _has_empty_active_day(itinerary: ItineraryGenerateResponse) -> bool:
    return any(str(day.theme or "").lower() != "rest" and not day.places for day in itinerary.days)


def _quality_score_summary(
    variant: ItineraryGenerateResponse,
    review: LLMQualityReview,
    applied: list[dict],
    ignored: list[dict],
    candidate_results: list[CandidatePOIValidationResult] | None = None,
) -> dict:
    summary = dict(variant.score_summary or {})
    summary["llm_quality_model_version"] = settings.LLM_MODEL
    summary["llm_quality_review"] = review.model_dump(mode="json")
    summary["llm_quality_applied_adjustments"] = applied
    summary["llm_quality_ignored_adjustments"] = ignored
    if candidate_results:
        summary["llm_candidate_poi"] = [
            {
                **result.candidate.model_dump(mode="json"),
                "status": result.status,
                "display_allowed": result.display_allowed,
                "duplicate_warnings": result.duplicate_warnings,
                "missing_fields": result.missing_fields,
                "rejection_reasons": result.rejection_reasons,
            }
            for result in candidate_results
        ]
    elif variant.candidate_poi:
        summary["llm_candidate_poi"] = [candidate.model_dump(mode="json") for candidate in variant.candidate_poi]
    day_reviews = {
        str(day.day_number or day.day): day.quality_review.model_dump(mode="json")
        for day in variant.days
        if day.quality_review is not None
    }
    item_reviews = {
        str(place.id): place.quality_review.model_dump(mode="json")
        for day in variant.days
        for place in day.places
        if place.quality_review is not None
    }
    if day_reviews:
        summary["llm_quality_day_reviews"] = day_reviews
    if item_reviews:
        summary["llm_quality_item_reviews"] = item_reviews
    return summary


def _review_after_repairs(
    review: LLMQualityReview,
    adjusted: ItineraryAdjustmentResult,
) -> LLMQualityReview:
    applied = adjusted.applied_adjustments
    meaningful_ignored = [
        item
        for item in adjusted.ignored_adjustments
        if item.get("action") != "note" and item.get("reason") != "unsupported_or_missing_target"
    ]
    if review.status in {LLMReviewStatus.caution, LLMReviewStatus.reject} and applied and not meaningful_ignored:
        return review.model_copy(
            update={
                "status": LLMReviewStatus.ok,
                "issues": [],
                "suggested_adjustments": [],
                "user_summary_ru": "Маршрут скорректирован по результатам проверки.",
                "defense_trace": f"{review.defense_trace or ''} Applied all LLM itinerary adjustments.".strip(),
            }
        )
    return review


def _clear_item_quality_reviews(itinerary: ItineraryGenerateResponse) -> ItineraryGenerateResponse:
    days = []
    for day in itinerary.days:
        places = [place.model_copy(update={"quality_review": None}) for place in day.places]
        days.append(day.model_copy(update={"quality_review": None, "places": places, "items": places}))
    return itinerary.model_copy(update={"days": days})


def _attach_review_targets(
    itinerary: ItineraryGenerateResponse,
    review: LLMQualityReview,
) -> ItineraryGenerateResponse:
    if review.status in {LLMReviewStatus.ok, LLMReviewStatus.skipped}:
        return itinerary

    target_days = {
        value
        for value in [
            *(issue.day for issue in review.issues),
            *(adjustment.target_day for adjustment in review.suggested_adjustments),
        ]
        if value is not None
    }
    target_items = {
        value
        for value in [
            *(issue.item_id or issue.target_id for issue in review.issues),
            *(adjustment.target_id for adjustment in review.suggested_adjustments),
        ]
        if value is not None
    }

    days = []
    for day in itinerary.days:
        day_number = day.day_number or day.day
        should_mark_day = (not target_days and not target_items) or day_number in target_days
        places = [
            place.model_copy(
                update={
                    "quality_review": review
                    if place.id in target_items or (should_mark_day and (target_days or len(day.places) == 1))
                    else place.quality_review
                }
            )
            for place in day.places
        ]
        days.append(
            day.model_copy(
                update={
                    "quality_review": review if should_mark_day else day.quality_review,
                    "places": places,
                    "items": places,
                }
            )
        )
    return itinerary.model_copy(update={"days": days})


def _save_candidate_poi_logs(
    *,
    db: Session,
    destination_id: uuid.UUID,
    review: LLMQualityReview,
    candidate_results: list[CandidatePOIValidationResult],
) -> None:
    if not candidate_results:
        return
    try:
        for result in candidate_results:
            payload = result.candidate.model_dump(mode="json")
            payload["validation"] = {
                "status": result.status,
                "display_allowed": result.display_allowed,
                "duplicate_warnings": result.duplicate_warnings,
                "missing_fields": result.missing_fields,
                "rejection_reasons": result.rejection_reasons,
            }
            db.add(
                LLMCandidatePOILog(
                    destination_id=destination_id,
                    review_log_id=review.review_id,
                    name=result.candidate.name,
                    category=result.candidate.category,
                    lat=result.candidate.lat,
                    lng=result.candidate.lng,
                    address=result.candidate.address,
                    payload=payload,
                    status=_candidate_audit_status(result),
                )
            )
            record_llm_candidate_poi(result.status)
            emit_ml_quality_event(
                "llm_candidate_poi_created",
                {
                    "status": result.status,
                    "display_allowed": result.display_allowed,
                    "destination_id": str(destination_id),
                    "review_id": str(review.review_id) if review.review_id else None,
                    "rejection_reasons": result.rejection_reasons,
                },
                entity_type="llm_candidate_poi",
                entity_id=result.candidate.candidate_id,
            )
        db.commit()
    except Exception:
        db.rollback()


def _candidate_audit_status(result: CandidatePOIValidationResult) -> str:
    if result.display_allowed:
        return "pending"
    if result.status in {"duplicate", "needs_data"}:
        return "rejected"
    return result.status


@router.post("/itinerary", response_model=ItineraryGenerateResponse)
def generate_itinerary(
    request: ItineraryGenerateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ItineraryGenerateResponse:
    secret = _data_service_secret()
    if request.destination_id and not secret:
        raise AppException(
            status_code=503,
            code="ITINERARY_UNAVAILABLE",
            message="Itinerary generation is temporarily unavailable.",
        )

    profile = _get_profile_sync(db, user_id)
    activities = _activity_preferences(profile, request)

    if not request.destination_id:
        external = generate_external_route(
            db=db,
            user_id=user_id,
            trip_id=request.trip_id,
            request=request,
            profile=profile,
            destination_info=None,
            trigger="manual_destination",
        )
        if external is not None:
            return _review_response(db=db, user_id=user_id, profile=profile, request=request, response=external)
        raise AppException(
            status_code=422,
            code="ITINERARY_NO_FEASIBLE_ROUTE",
            message="External route generation is disabled or unavailable for this destination.",
        )

    try:
        response = httpx.post(
            f"{settings.DATA_SERVICE_URL}/internal/itinerary",
            params=_params(request, activities),
            headers={"X-Internal-Secret": secret},
            timeout=5.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        external = generate_external_route(
            db=db,
            user_id=user_id,
            trip_id=request.trip_id,
            request=request,
            profile=profile,
            destination_info=_destination_info(request.destination_id),
            trigger="data_service_no_feasible",
        )
        if external is not None:
            return _review_response(db=db, user_id=user_id, profile=profile, request=request, response=external)
        raise AppException(
            status_code=503,
            code="ITINERARY_UNAVAILABLE",
            message="Itinerary generation is temporarily unavailable.",
        ) from exc

    normalized = _normalize_response(request, response.json())
    if not normalized.has_template or not normalized.days or _has_empty_active_day(normalized):
        message = normalized.message or ""
        trigger = "data_service_no_feasible" if "feasible" in message.lower() else "data_service_no_template"
        if _has_empty_active_day(normalized):
            trigger = "data_service_no_feasible"
        external = generate_external_route(
            db=db,
            user_id=user_id,
            trip_id=request.trip_id,
            request=request,
            profile=profile,
            destination_info=_destination_info(request.destination_id),
            trigger=trigger,
        )
        if external is not None:
            return _review_response(db=db, user_id=user_id, profile=profile, request=request, response=external)
        if trigger == "data_service_no_feasible":
            raise AppException(
                status_code=422,
                code="ITINERARY_NO_FEASIBLE_ROUTE",
                message="Could not build a route for the selected trip parameters.",
            )
    return _review_response(db=db, user_id=user_id, profile=profile, request=request, response=normalized)
