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


def _params(request: ItineraryGenerateRequest, activities: list[str]) -> list[tuple[str, str | int]]:
    params: list[tuple[str, str | int]] = [
        ("destination_id", str(request.destination_id)),
        ("duration_days", request.duration_days),
        ("start_date", request.start_date.isoformat()),
    ]
    params.extend(("preferred_activities", activity) for activity in activities)
    return params


def _normalize_response(request: ItineraryGenerateRequest, payload: dict) -> ItineraryGenerateResponse:
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
            theme=str(day.get("theme") or "urban"),
            places=[
                ItineraryPlace(
                    id=uuid.UUID(str(place["id"])),
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
                    visit_duration_minutes=place.get("visit_duration_minutes"),
                )
                for place in day.get("places", [])
                if place.get("id")
            ],
        )
        for index, day in enumerate(payload.get("days", []))
    ]

    return ItineraryGenerateResponse(
        destination_id=uuid.UUID(str(payload.get("destination_id") or request.destination_id)),
        duration_days=int(payload.get("duration_days") or request.duration_days),
        days=days,
        activity_tags=[str(tag) for tag in payload.get("activity_tags", [])],
    )


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
