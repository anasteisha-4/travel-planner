import uuid
from datetime import datetime, timedelta

from app.config import settings
from app.schemas.itinerary import ItineraryDay, ItineraryGenerateRequest, ItineraryGenerateResponse, ItineraryPlace


def generate_external_route(
    *,
    db,
    user_id,
    trip_id,
    request: ItineraryGenerateRequest,
    profile: dict,
    destination_info: dict | None,
    trigger: str,
) -> ItineraryGenerateResponse | None:
    del db, user_id, profile
    if not settings.LLM_EXTERNAL_ROUTE_ENABLED or not request.allow_external_route:
        return None

    destination_name = _destination_name(request, destination_info)
    destination_id = request.destination_id or uuid.uuid5(uuid.NAMESPACE_URL, f"triply:external:{destination_name}")
    rest_days = _rest_days(request.duration_days, request.rest_days_count)
    days: list[ItineraryDay] = []
    for day_number in range(1, request.duration_days + 1):
        if day_number in rest_days:
            days.append(
                ItineraryDay(
                    day=day_number,
                    day_number=day_number,
                    theme="rest",
                    start_time=request.day_start_time,
                    end_time=request.day_end_time,
                    places=[],
                    items=[],
                )
            )
            continue
        places = _fallback_places(destination_name, day_number, request)
        days.append(
            ItineraryDay(
                day=day_number,
                day_number=day_number,
                theme="overview" if day_number == 1 else "local",
                start_time=request.day_start_time,
                end_time=request.day_end_time,
                places=places,
                items=places,
            )
        )

    route_signature = (
        f"external-{uuid.uuid5(uuid.NAMESPACE_URL, f'{trip_id}:{destination_name}:{request.variant_seed}:{trigger}')}"
    )
    return ItineraryGenerateResponse(
        destination_id=destination_id,
        duration_days=request.duration_days,
        variant_index=0,
        variant_seed=request.variant_seed,
        route_signature=route_signature,
        model_version="external-fallback-v1",
        days=days,
        activity_tags=request.preferred_activities or [],
        source="external-fallback",
        has_template=True,
        message="Fallback itinerary generated because catalog route generation was unavailable.",
        score_summary={
            "fallback_reason": trigger,
            "external_candidate_route": True,
            "llm_external_route_enabled": settings.LLM_EXTERNAL_ROUTE_ENABLED,
        },
    )


def _destination_name(request: ItineraryGenerateRequest, destination_info: dict | None) -> str:
    if destination_info:
        for key in ("display_name", "name_ru", "name", "city"):
            value = destination_info.get(key)
            if value:
                return str(value)
    return request.destination_text or "направление"


def _rest_days(duration_days: int, rest_days_count: int) -> set[int]:
    if rest_days_count <= 0:
        return set()
    if rest_days_count >= duration_days:
        return set(range(2, duration_days + 1))
    step = duration_days / (rest_days_count + 1)
    return {max(1, min(duration_days, round(step * index))) for index in range(1, rest_days_count + 1)}


def _fallback_places(destination_name: str, day_number: int, request: ItineraryGenerateRequest) -> list[ItineraryPlace]:
    start = _parse_time(request.day_start_time)
    themes = _themes(request.preferred_activities or [])
    theme = themes[(day_number - 1) % len(themes)]
    names = [
        f"{destination_name}: центральный район",
        f"{destination_name}: {theme}",
        f"{destination_name}: вечерняя прогулка",
    ]
    places: list[ItineraryPlace] = []
    for index, name in enumerate(names):
        arrival = start + timedelta(hours=2 * index)
        departure = arrival + timedelta(minutes=90)
        places.append(
            ItineraryPlace(
                id=uuid.uuid5(uuid.NAMESPACE_URL, f"{destination_name}:{day_number}:{index}:{name}"),
                name=name,
                display_name=name,
                category=theme if index == 1 else "walk",
                arrival_time=arrival.strftime("%H:%M"),
                departure_time=departure.strftime("%H:%M"),
                travel_from_previous_minutes=20 if index else 0,
                visit_duration_minutes=90,
                duration_minutes=90,
                opening_status="unknown",
                score=0.5,
                external_candidate_source="fallback",
            )
        )
    return places


def _themes(preferred_activities: list[str]) -> list[str]:
    values = [str(item) for item in preferred_activities if item]
    return values or ["culture", "food", "walk"]


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.strptime(value, "%H:%M")
    except ValueError:
        parsed = datetime.strptime("09:30", "%H:%M")
    return parsed
