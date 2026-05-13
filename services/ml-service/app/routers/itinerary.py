import uuid

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user_id
from app.exceptions import AppException
from app.schemas.itinerary import ItineraryDay, ItineraryGenerateRequest, ItineraryGenerateResponse, ItineraryPlace
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
        ("destination_id", str(request.destination_id)),
        ("duration_days", request.duration_days),
        ("start_date", request.start_date.isoformat()),
        ("variant_count", request.variant_count),
        ("pace", request.pace),
        ("day_start_time", request.day_start_time),
        ("day_end_time", request.day_end_time),
        ("rest_days_count", request.rest_days_count),
        ("people_count", request.people_count),
    ]
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


@router.post("/itinerary", response_model=ItineraryGenerateResponse)
def generate_itinerary(
    request: ItineraryGenerateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ItineraryGenerateResponse:
    secret = _data_service_secret()
    if not secret:
        raise AppException(
            status_code=503,
            code="ITINERARY_UNAVAILABLE",
            message="Itinerary generation is temporarily unavailable.",
        )

    profile = _get_profile_sync(db, user_id)
    activities = _activity_preferences(profile, request)

    try:
        response = httpx.post(
            f"{settings.DATA_SERVICE_URL}/internal/itinerary",
            params=_params(request, activities),
            headers={"X-Internal-Secret": secret},
            timeout=5.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise AppException(
            status_code=503,
            code="ITINERARY_UNAVAILABLE",
            message="Itinerary generation is temporarily unavailable.",
        ) from exc

    return _normalize_response(request, response.json())
