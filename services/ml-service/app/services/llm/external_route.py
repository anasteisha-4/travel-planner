import json
import math
import uuid
from datetime import datetime
from typing import Any

from app.config import settings
from app.schemas.itinerary import ItineraryDay, ItineraryGenerateRequest, ItineraryGenerateResponse, ItineraryPlace
from app.services.llm.prompts import compact_json
from app.services.llm.providers import LLMMessage, LLMProviderError, LLMRequest, get_provider

EXTERNAL_ROUTE_PROMPT_VERSION = "external_route_v2"
_MIN_ACTIVE_PLACES_PER_DAY = 2

_GENERIC_NAME_PARTS = {
    "центральный район",
    "central district",
    "city center",
    "old town",
    "evening walk",
    "вечерняя прогулка",
    "culture",
    "food",
    "walk",
    "местная культура",
}

_EXTERNAL_ROUTE_SYSTEM_PROMPT = """
You generate complete travel itineraries as strict JSON for Triply.

Rules:
- Return real, specific POIs for the requested destination, never placeholders or generic labels.
- Each active day must contain geographically plausible POIs in visit order.
- Every place must include latitude, longitude, arrival_time, departure_time, category, and a short reason.
- Use the user's duration, pace, daily time window, rest days, notes, and preferred activities.
- Generate the requested number of route variants when possible.
- For standard pace, return exactly 3 high-quality POIs per active day. For slow pace, return 2-3. For fast pace, return 3-4.
- Every POI must be inside or immediately near the requested destination city; do not include nearby major cities.
- Do not repeat the same POI across days or variants.
- Do not use catalog IDs. The backend will mark all places as external candidates for review.
- If unsure about a POI, still provide coordinates and mark confidence below 0.7.
- Do not include markdown or prose outside JSON.
""".strip()


def external_route_json_schema() -> dict:
    place_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "name",
            "category",
            "lat",
            "lng",
            "address",
            "arrival_time",
            "departure_time",
            "visit_duration_minutes",
            "travel_from_previous_minutes",
            "reason",
            "confidence",
        ],
        "properties": {
            "name": {"type": "string"},
            "category": {"type": "string"},
            "lat": {"type": "number"},
            "lng": {"type": "number"},
            "address": {"type": ["string", "null"]},
            "arrival_time": {"type": "string"},
            "departure_time": {"type": "string"},
            "visit_duration_minutes": {"type": "integer"},
            "travel_from_previous_minutes": {"type": "integer"},
            "reason": {"type": "string"},
            "confidence": {"type": "number"},
        },
    }
    day_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["day_number", "theme", "places"],
        "properties": {
            "day_number": {"type": "integer"},
            "theme": {"type": "string"},
            "places": {"type": "array", "items": place_schema},
        },
    }
    variant_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["variant_index", "title", "days"],
        "properties": {
            "variant_index": {"type": "integer"},
            "title": {"type": "string"},
            "days": {"type": "array", "items": day_schema},
        },
    }
    return {
        "name": "triply_external_route",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["variants"],
            "properties": {
                "variants": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 3,
                    "items": variant_schema,
                }
            },
        },
    }


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
    context = _external_route_context(
        request=request,
        destination_name=destination_name,
        destination_info=destination_info,
        trigger=trigger,
    )
    provider = get_provider()
    for attempt in range(2):
        try:
            response = provider.complete(
                LLMRequest(
                    model=settings.LLM_MODEL,
                    temperature=0.25 if attempt == 0 else 0,
                    max_tokens=settings.LLM_EXTERNAL_ROUTE_MAX_TOKENS,
                    timeout_seconds=max(settings.LLM_TIMEOUT_SECONDS, 30.0),
                    max_retries=0,
                    json_schema=external_route_json_schema(),
                    messages=[
                        LLMMessage(role="system", content=_external_route_system_prompt(attempt)),
                        LLMMessage(
                            role="user",
                            content=compact_json({"prompt_version": EXTERNAL_ROUTE_PROMPT_VERSION, "context": context}),
                        ),
                    ],
                )
            )
            payload = _loads_json_object(response.content)
        except (LLMProviderError, json.JSONDecodeError, ValueError, TypeError, KeyError):
            continue

        variants = _normalize_external_variants(
            payload=payload,
            destination_id=destination_id,
            destination_name=destination_name,
            trip_id=trip_id,
            request=request,
            trigger=trigger,
        )
        if variants:
            return variants[0].model_copy(update={"variants": variants})
    return None


def _external_route_system_prompt(attempt: int) -> str:
    if attempt <= 0:
        return _EXTERNAL_ROUTE_SYSTEM_PROMPT
    return (
        f"{_EXTERNAL_ROUTE_SYSTEM_PROMPT}\n"
        "Previous output was rejected by validation. This time every variant must include exactly all requested "
        "active days, at least two specific non-generic POIs per active day, valid coordinates, and increasing "
        "arrival/departure times. Return only JSON."
    )


def _external_route_context(
    *,
    request: ItineraryGenerateRequest,
    destination_name: str,
    destination_info: dict | None,
    trigger: str,
) -> dict:
    rest_days = sorted(_rest_days(request.duration_days, request.rest_days_count))
    active_days = [day for day in range(1, request.duration_days + 1) if day not in set(rest_days)]
    return {
        "destination": {
            "name": destination_name,
            "catalog_destination_id": str(request.destination_id) if request.destination_id else None,
            "catalog_info": destination_info,
            "manual_destination_text": request.destination_text,
        },
        "trip": {
            "duration_days": request.duration_days,
            "active_days": active_days,
            "rest_days": rest_days,
            "start_date": request.start_date.isoformat(),
            "pace": request.pace,
            "day_start_time": request.day_start_time,
            "day_end_time": request.day_end_time,
            "preferred_activities": request.preferred_activities or [],
            "variant_count": request.variant_count,
            "people_count": request.people_count,
            "budget": request.trip_budget,
            "currency": request.currency,
            "origin_city_name": request.origin_city_name,
            "notes": request.trip_notes,
            "trigger": trigger,
        },
        "quality_requirements": {
            "min_active_places_per_day": _MIN_ACTIVE_PLACES_PER_DAY,
            "max_active_places_per_day": _max_places_per_day(request.pace),
            "coordinates_required": True,
            "specific_real_poi_names_required": True,
            "avoid_generic_names": sorted(_GENERIC_NAME_PARTS),
        },
    }


def _normalize_external_variants(
    *,
    payload: dict,
    destination_id: uuid.UUID,
    destination_name: str,
    trip_id: uuid.UUID | None,
    request: ItineraryGenerateRequest,
    trigger: str,
) -> list[ItineraryGenerateResponse]:
    raw_variants = payload.get("variants")
    if not isinstance(raw_variants, list):
        return []

    normalized: list[ItineraryGenerateResponse] = []
    for fallback_index, raw_variant in enumerate(raw_variants[: request.variant_count]):
        if not isinstance(raw_variant, dict):
            continue
        days = _normalize_external_days(
            raw_days=raw_variant.get("days"),
            destination_name=destination_name,
            request=request,
        )
        if not _is_complete_external_route(days, request):
            continue
        variant_index = int(raw_variant.get("variant_index") or fallback_index)
        signature_seed = compact_json(
            {
                "trip_id": str(trip_id) if trip_id else None,
                "destination": destination_name,
                "variant_index": variant_index,
                "seed": request.variant_seed,
                "trigger": trigger,
                "days": [[place.name for place in day.places] for day in days if day.places],
            }
        )
        normalized.append(
            ItineraryGenerateResponse(
                destination_id=destination_id,
                duration_days=request.duration_days,
                variant_index=variant_index,
                variant_seed=(request.variant_seed or 0) + variant_index,
                route_signature=f"llm-external-{uuid.uuid5(uuid.NAMESPACE_URL, signature_seed)}",
                model_version=f"llm-external-route:{settings.LLM_MODEL}",
                days=days,
                activity_tags=request.preferred_activities or [],
                source="llm-external-draft",
                has_template=True,
                message="External LLM itinerary generated because catalog POI route generation was unavailable.",
                score_summary={
                    "fallback_reason": trigger,
                    "external_route_used": True,
                    "external_route_prompt_version": EXTERNAL_ROUTE_PROMPT_VERSION,
                    "catalog_mutation_allowed": False,
                    "variant_title": raw_variant.get("title"),
                    "llm_external_route_model": settings.LLM_MODEL,
                },
            )
        )
    return normalized


def _normalize_external_days(
    *,
    raw_days: Any,
    destination_name: str,
    request: ItineraryGenerateRequest,
) -> list[ItineraryDay]:
    if not isinstance(raw_days, list):
        return []
    raw_by_day: dict[int, dict] = {}
    for raw_day in raw_days:
        if not isinstance(raw_day, dict):
            continue
        try:
            day_number = int(raw_day.get("day_number") or raw_day.get("day"))
        except (TypeError, ValueError):
            continue
        raw_by_day[day_number] = raw_day

    rest_days = _rest_days(request.duration_days, request.rest_days_count)
    days: list[ItineraryDay] = []
    seen_names: set[str] = set()
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
        raw_day = raw_by_day.get(day_number)
        if raw_day is None:
            return []
        places = _normalize_external_places(
            raw_places=raw_day.get("places"),
            day_number=day_number,
            destination_name=destination_name,
            seen_names=seen_names,
        )
        days.append(
            ItineraryDay(
                day=day_number,
                day_number=day_number,
                theme=str(raw_day.get("theme") or "local"),
                start_time=request.day_start_time,
                end_time=request.day_end_time,
                places=places,
                items=places,
            )
        )
    return _clean_external_days(days, request)


def _normalize_external_places(
    *,
    raw_places: Any,
    day_number: int,
    destination_name: str,
    seen_names: set[str],
) -> list[ItineraryPlace]:
    if not isinstance(raw_places, list):
        return []
    places: list[ItineraryPlace] = []
    for index, raw_place in enumerate(raw_places):
        if not isinstance(raw_place, dict):
            continue
        name = str(raw_place.get("name") or "").strip()
        normalized_name = _normalize_name(name)
        if not name or normalized_name in seen_names or _is_generic_place_name(name, destination_name):
            continue
        lat = _float_or_none(raw_place.get("lat"))
        lng = _float_or_none(raw_place.get("lng"))
        if lat is None or lng is None or not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            continue
        arrival_time = _valid_time(raw_place.get("arrival_time"))
        departure_time = _valid_time(raw_place.get("departure_time"))
        if not arrival_time or not departure_time or departure_time <= arrival_time:
            continue
        duration = _int_or_none(raw_place.get("visit_duration_minutes"))
        if duration is None or duration < 20:
            duration = max(20, _minutes_between(arrival_time, departure_time))
        places.append(
            ItineraryPlace(
                id=uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"triply:external-route:{destination_name}:{day_number}:{index}:{name}",
                ),
                name=name,
                display_name=name,
                category=str(raw_place.get("category") or "place"),
                lat=lat,
                lng=lng,
                address=raw_place.get("address"),
                arrival_time=arrival_time,
                departure_time=departure_time,
                travel_from_previous_minutes=max(0, _int_or_none(raw_place.get("travel_from_previous_minutes")) or 0),
                visit_duration_minutes=duration,
                duration_minutes=duration,
                opening_status="unknown",
                score=_float_or_none(raw_place.get("confidence")) or 0.7,
                external_candidate_source="llm_external_route",
            )
        )
        seen_names.add(normalized_name)
    return places


def _clean_external_days(days: list[ItineraryDay], request: ItineraryGenerateRequest) -> list[ItineraryDay]:
    days = _remove_coordinate_outliers(days)
    max_places = _max_places_per_day(request.pace)
    cleaned: list[ItineraryDay] = []
    for day in days:
        if str(day.theme or "").lower() == "rest":
            cleaned.append(day)
            continue
        places = day.places[:max_places]
        cleaned.append(day.model_copy(update={"places": places, "items": places}))
    return cleaned


def _remove_coordinate_outliers(days: list[ItineraryDay]) -> list[ItineraryDay]:
    places_with_coords = [
        place for day in days for place in day.places if place.lat is not None and place.lng is not None
    ]
    if len(places_with_coords) < 4:
        return days
    median_lat = sorted(float(place.lat) for place in places_with_coords)[len(places_with_coords) // 2]
    median_lng = sorted(float(place.lng) for place in places_with_coords)[len(places_with_coords) // 2]
    cleaned: list[ItineraryDay] = []
    for day in days:
        if str(day.theme or "").lower() == "rest":
            cleaned.append(day)
            continue
        places = [
            place
            for place in day.places
            if place.lat is not None
            and place.lng is not None
            and _haversine_km(float(place.lat), float(place.lng), median_lat, median_lng) <= 35
        ]
        cleaned.append(day.model_copy(update={"places": places, "items": places}))
    return cleaned


def _max_places_per_day(pace: str | None) -> int:
    normalized = str(pace or "").lower()
    if normalized in {"slow", "relaxed", "low"}:
        return 3
    if normalized in {"fast", "intense", "high"}:
        return 4
    return 3


def _is_complete_external_route(days: list[ItineraryDay], request: ItineraryGenerateRequest) -> bool:
    if len(days) != request.duration_days:
        return False
    for day in days:
        if str(day.theme or "").lower() == "rest":
            continue
        if len(day.places) < _MIN_ACTIVE_PLACES_PER_DAY:
            return False
        if any(place.lat is None or place.lng is None for place in day.places):
            return False
    return True


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    value = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * radius_km * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def _loads_json_object(content: str) -> dict:
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start < 0 or end <= start:
            raise
        value = json.loads(content[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("LLM external route response must be a JSON object")
    return value


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


def _valid_time(value: Any) -> str | None:
    try:
        return datetime.strptime(str(value), "%H:%M").strftime("%H:%M")
    except (TypeError, ValueError):
        return None


def _minutes_between(start: str, end: str) -> int:
    return int((datetime.strptime(end, "%H:%M") - datetime.strptime(start, "%H:%M")).total_seconds() // 60)


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _normalize_name(value: str | None) -> str:
    return " ".join(str(value or "").casefold().split())


def _is_generic_place_name(name: str, destination_name: str) -> bool:
    normalized = _normalize_name(name)
    destination = _normalize_name(destination_name)
    stripped_destination_prefix = normalized.removeprefix(f"{destination}:").strip()
    if stripped_destination_prefix in _GENERIC_NAME_PARTS:
        return True
    if normalized in _GENERIC_NAME_PARTS:
        return True
    return bool(destination and normalized in {destination, f"{destination} city", f"{destination} center"})
