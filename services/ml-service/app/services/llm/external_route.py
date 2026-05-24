import json
import logging
import math
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any

import httpx

from app.config import settings
from app.schemas.itinerary import ItineraryDay, ItineraryGenerateRequest, ItineraryGenerateResponse, ItineraryPlace
from app.services.llm.prompts import compact_json
from app.services.llm.providers import LLMMessage, LLMProviderError, LLMRequest, get_provider

EXTERNAL_ROUTE_PROMPT_VERSION = "external_route_v2"
logger = logging.getLogger(__name__)
_GEOCODE_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="external-route-geocode")

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

_GEOCODE_PLACE_STOPWORDS = {
    "the",
    "and",
    "de",
    "del",
    "la",
    "le",
    "les",
    "of",
    "park",
    "world",
    "plaza",
    "beach",
    "playa",
    "platja",
    "viewpoint",
    "museum",
    "museu",
    "castell",
    "castle",
}

_EXTERNAL_ROUTE_SYSTEM_PROMPT = """
You generate complete travel itineraries as strict JSON for Triply.

Rules:
- Return real, specific POIs for the requested destination, never placeholders or generic labels.
- Each active day must contain geographically plausible POIs in visit order.
- Every place must include latitude, longitude, arrival_time, departure_time, category, and a short reason.
- Use the user's duration, pace, daily time window, rest days, notes, and preferred activities.
- Generate exactly one route variant. Never generate alternative route variants in the same response.
- For standard pace, return exactly 4 high-quality POIs per active day. For slow pace, return exactly 3. For fast pace, return exactly 5.
- Every POI must be inside or immediately near the requested destination city; do not include nearby major cities.
- Every POI coordinate must point to the real land/building/park location, never to nearby water, sea, beach water, or an approximate offshore point.
- Do not repeat the same POI across days.
- If a previous route signature or POI list is supplied, produce a materially different route with different POIs.
- Do not use catalog IDs. The backend will mark all places as external candidates for review.
- If unsure about a POI, still provide coordinates and mark confidence below 0.7.
- Do not include markdown or prose outside JSON.
""".strip()


def external_route_json_schema(max_variants: int = 1) -> dict:
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
                    "maxItems": max(1, min(1, max_variants)),
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
        logger.warning(
            "external_route_skipped reason=disabled_or_not_allowed trip_id=%s destination_text=%r "
            "enabled=%s allowed=%s",
            trip_id,
            request.destination_text,
            settings.LLM_EXTERNAL_ROUTE_ENABLED,
            request.allow_external_route,
        )
        return None

    destination_name = _destination_name(request, destination_info)
    destination_id = request.destination_id or uuid.uuid5(uuid.NAMESPACE_URL, f"triply:external:{destination_name}")
    effective_request = _external_route_request(request, trigger)
    geocoded_destination = None if destination_info else _geocode_destination_context(destination_name)
    destination_center = _destination_center(destination_info) or _destination_center(geocoded_destination)
    destination_name = _destination_name_with_geocode_context(destination_name, geocoded_destination)
    provider = get_provider()

    result = _generate_external_route_attempt(
        provider=provider,
        destination_id=destination_id,
        destination_name=destination_name,
        destination_info=destination_info,
        destination_center=destination_center,
        trip_id=trip_id,
        request=effective_request,
        trigger=trigger,
        coordinate_repair_enabled=settings.LLM_EXTERNAL_ROUTE_COORDINATE_REPAIR_ENABLED,
    )
    if result is not None:
        return result

    if settings.LLM_EXTERNAL_ROUTE_COORDINATE_REPAIR_ENABLED:
        relaxed_result = _generate_external_route_attempt(
            provider=get_provider(),
            destination_id=destination_id,
            destination_name=destination_name,
            destination_info=destination_info,
            destination_center=destination_center,
            trip_id=trip_id,
            request=effective_request,
            trigger=f"{trigger}_relaxed_coordinate_repair",
            coordinate_repair_enabled=False,
        )
        if relaxed_result is not None:
            return _mark_coordinate_repair_relaxed(relaxed_result)

    logger.warning(
        "external_route_failed reason=all_attempts_rejected trip_id=%s destination=%r duration_days=%s "
        "active_days=%s trigger=%s center=%s repair_enabled=%s",
        trip_id,
        destination_name,
        request.duration_days,
        _active_day_count(request),
        trigger,
        destination_center,
        settings.LLM_EXTERNAL_ROUTE_COORDINATE_REPAIR_ENABLED,
    )
    return None


def _generate_external_route_attempt(
    *,
    provider,
    destination_id: uuid.UUID,
    destination_name: str,
    destination_info: dict | None,
    destination_center: tuple[float, float] | None,
    trip_id: uuid.UUID | None,
    request: ItineraryGenerateRequest,
    trigger: str,
    coordinate_repair_enabled: bool,
) -> ItineraryGenerateResponse | None:
    if _active_day_count(request) > 4:
        chunked = _generate_external_route_chunks(
            provider=provider,
            destination_id=destination_id,
            destination_name=destination_name,
            destination_info=destination_info,
            destination_center=destination_center,
            trip_id=trip_id,
            request=request,
            trigger=trigger,
            coordinate_repair_enabled=coordinate_repair_enabled,
        )
        if chunked is not None:
            return chunked
        logger.warning(
            "external_route_chunked_failed trying_single_fallback trip_id=%s destination=%r duration_days=%s trigger=%s",
            trip_id,
            destination_name,
            request.duration_days,
            trigger,
        )
        single_fallback = _generate_external_route_single(
            provider=get_provider(),
            destination_id=destination_id,
            destination_name=destination_name,
            destination_info=destination_info,
            destination_center=destination_center,
            trip_id=trip_id,
            request=request,
            trigger=f"{trigger}_single_fallback",
            coordinate_repair_enabled=coordinate_repair_enabled,
            timeout_cap_seconds=28.0,
            max_tokens_cap=7000,
            max_attempts=1,
        )
        if single_fallback is not None:
            return _mark_single_route_fallback(single_fallback)
        logger.warning(
            "external_route_single_fallback_failed trip_id=%s destination=%r duration_days=%s trigger=%s",
            trip_id,
            destination_name,
            request.duration_days,
            trigger,
        )
        return None

    return _generate_external_route_single(
        provider=provider,
        destination_id=destination_id,
        destination_name=destination_name,
        destination_info=destination_info,
        destination_center=destination_center,
        trip_id=trip_id,
        request=request,
        trigger=trigger,
        coordinate_repair_enabled=coordinate_repair_enabled,
    )


def _mark_coordinate_repair_relaxed(response: ItineraryGenerateResponse) -> ItineraryGenerateResponse:
    summary = dict(response.score_summary or {})
    summary["external_route_coordinate_repair_relaxed"] = True
    variants = [
        variant.model_copy(
            update={
                "score_summary": {
                    **dict(variant.score_summary or {}),
                    "external_route_coordinate_repair_relaxed": True,
                }
            }
        )
        for variant in (response.variants or [])
    ]
    return response.model_copy(update={"score_summary": summary, "variants": variants or response.variants})


def _mark_single_route_fallback(response: ItineraryGenerateResponse) -> ItineraryGenerateResponse:
    summary = dict(response.score_summary or {})
    summary["external_route_single_fallback"] = True
    variants = [
        variant.model_copy(
            update={
                "score_summary": {
                    **dict(variant.score_summary or {}),
                    "external_route_single_fallback": True,
                }
            }
        )
        for variant in (response.variants or [])
    ]
    return response.model_copy(update={"score_summary": summary, "variants": variants or response.variants})


def _generate_external_route_single(
    *,
    provider,
    destination_id: uuid.UUID,
    destination_name: str,
    destination_info: dict | None,
    destination_center: tuple[float, float] | None,
    trip_id: uuid.UUID | None,
    request: ItineraryGenerateRequest,
    trigger: str,
    coordinate_repair_enabled: bool,
    timeout_cap_seconds: float | None = None,
    max_tokens_cap: int = 3600,
    max_attempts: int = 2,
) -> ItineraryGenerateResponse | None:
    context = _external_route_context(
        request=request,
        destination_name=destination_name,
        destination_info=destination_info,
        trigger=trigger,
    )
    started_at = time.perf_counter()
    interactive_timeout_seconds = min(settings.LLM_EXTERNAL_ROUTE_TIMEOUT_SECONDS, timeout_cap_seconds or 18.0)
    for attempt in range(max_attempts):
        remaining_seconds = interactive_timeout_seconds - (time.perf_counter() - started_at)
        if remaining_seconds < 8:
            break
        try:
            response = provider.complete(
                LLMRequest(
                    model=settings.LLM_MODEL,
                    temperature=0.25 if attempt == 0 else 0,
                    max_tokens=min(settings.LLM_EXTERNAL_ROUTE_MAX_TOKENS, max_tokens_cap),
                    timeout_seconds=max(8.0, min(remaining_seconds, interactive_timeout_seconds)),
                    max_retries=0,
                    json_schema=external_route_json_schema(max_variants=request.variant_count),
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
        except (LLMProviderError, json.JSONDecodeError, ValueError, TypeError, KeyError) as exc:
            logger.warning(
                "external_route_llm_attempt_failed trigger=%s attempt=%s destination=%r error=%s",
                trigger,
                attempt,
                destination_name,
                str(exc)[:300],
            )
            continue

        variants = _normalize_external_variants(
            payload=payload,
            destination_id=destination_id,
            destination_name=destination_name,
            destination_center=destination_center,
            trip_id=trip_id,
            request=request,
            trigger=trigger,
            coordinate_repair_enabled=coordinate_repair_enabled,
        )
        if variants:
            return variants[0].model_copy(update={"variants": variants})
        logger.warning(
            "external_route_llm_attempt_rejected trigger=%s attempt=%s destination=%r duration_days=%s",
            trigger,
            attempt,
            destination_name,
            request.duration_days,
        )
    return None


def _generate_external_route_chunks(
    *,
    provider,
    destination_id: uuid.UUID,
    destination_name: str,
    destination_info: dict | None,
    destination_center: tuple[float, float] | None,
    trip_id: uuid.UUID | None,
    request: ItineraryGenerateRequest,
    trigger: str,
    coordinate_repair_enabled: bool,
) -> ItineraryGenerateResponse | None:
    rest_days = _rest_days(request.duration_days, request.rest_days_count)
    active_days = [day for day in range(1, request.duration_days + 1) if day not in rest_days]
    day_chunks = [active_days[index : index + 2] for index in range(0, len(active_days), 2)]
    combined: dict[int, ItineraryDay] = {
        day_number: ItineraryDay(
            day=day_number,
            day_number=day_number,
            theme="rest",
            start_time=None,
            end_time=None,
            places=[],
            items=[],
            total_score=0,
        )
        for day_number in rest_days
    }
    seed_base = request.variant_seed or 0
    seen_names: set[str] = set()
    for chunk_index, day_numbers in enumerate(day_chunks):
        if not day_numbers:
            continue
        chunk_notes = " ".join(
            part
            for part in [
                request.trip_notes,
                f"Generate only this segment of a longer {request.duration_days}-day trip: original days {day_numbers[0]}-{day_numbers[-1]}.",
            ]
            if part
        )
        chunk_request = request.model_copy(
            update={
                "duration_days": len(day_numbers),
                "rest_days_count": 0,
                "start_date": request.start_date + timedelta(days=day_numbers[0] - 1),
                "variant_count": 1,
                "variant_seed": seed_base + chunk_index,
                "exclude_signature": None,
                "trip_notes": chunk_notes,
            }
        )
        chunk = _generate_external_route_single(
            provider=get_provider(),
            destination_id=destination_id,
            destination_name=destination_name,
            destination_info=destination_info,
            destination_center=destination_center,
            trip_id=trip_id,
            request=chunk_request,
            trigger=f"{trigger}_chunk",
            coordinate_repair_enabled=coordinate_repair_enabled,
            timeout_cap_seconds=28.0,
            max_attempts=2,
        )
        if chunk is None:
            logger.warning(
                "external_route_chunk_failed reason=no_chunk trip_id=%s destination=%r chunk_index=%s days=%s",
                trip_id,
                destination_name,
                chunk_index,
                day_numbers,
            )
            return None
        chunk_days = [day for day in chunk.days if str(day.theme or "").lower() != "rest"]
        if len(chunk_days) < len(day_numbers):
            logger.warning(
                "external_route_chunk_failed reason=missing_days trip_id=%s destination=%r chunk_index=%s "
                "expected=%s got=%s",
                trip_id,
                destination_name,
                chunk_index,
                len(day_numbers),
                len(chunk_days),
            )
            return None
        for offset, original_day_number in enumerate(day_numbers):
            source_day = chunk_days[offset]
            places = source_day.places
            if len(places) < _validated_min_places_per_day(request.pace):
                logger.warning(
                    "external_route_chunk_failed reason=sparse_day trip_id=%s destination=%r day=%s places=%s",
                    trip_id,
                    destination_name,
                    original_day_number,
                    len(places),
                )
                return None
            for place in places:
                seen_names.add(_normalize_name(place.name))
            combined[original_day_number] = source_day.model_copy(
                update={
                    "day": original_day_number,
                    "day_number": original_day_number,
                    "places": places,
                    "items": places,
                }
            )

    days = [combined[day_number] for day_number in range(1, request.duration_days + 1) if day_number in combined]
    if not _is_complete_external_route(days, request, destination_center):
        logger.warning(
            "external_route_chunked_failed reason=incomplete_combined trip_id=%s destination=%r day_counts=%s",
            trip_id,
            destination_name,
            [len(day.places) for day in days],
        )
        return None
    signature_seed = compact_json(
        {
            "trip_id": str(trip_id) if trip_id else None,
            "destination": destination_name,
            "days": [[place.name for place in day.places] for day in days if day.places],
        }
    )
    route_signature = f"llm-external-{uuid.uuid5(uuid.NAMESPACE_URL, signature_seed)}"
    if request.exclude_signature and route_signature == request.exclude_signature:
        return None
    response = ItineraryGenerateResponse(
        destination_id=destination_id,
        duration_days=request.duration_days,
        variant_index=0,
        variant_seed=request.variant_seed,
        route_signature=route_signature,
        model_version=f"llm-external-route:{settings.LLM_MODEL}",
        days=days,
        activity_tags=request.preferred_activities or [],
        source="llm-external-draft",
        has_template=True,
        message=None,
        score_summary={
            "external_route_used": True,
            "external_route_prompt_version": EXTERNAL_ROUTE_PROMPT_VERSION,
            "external_route_trigger": trigger,
            "external_route_chunked": True,
            "external_route_chunks": len(day_chunks),
            "llm_external_route_model": settings.LLM_MODEL,
        },
    )
    return response.model_copy(update={"variants": [response]})


def _external_route_system_prompt(attempt: int) -> str:
    if attempt <= 0:
        return _EXTERNAL_ROUTE_SYSTEM_PROMPT
    return (
        f"{_EXTERNAL_ROUTE_SYSTEM_PROMPT}\n"
        "Previous output was rejected by validation. This time the single variant must include exactly all requested "
        "active days, the exact requested POI count per active day, valid coordinates, increasing "
        "arrival/departure times, and a route that differs from the excluded previous route. Return only JSON."
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
            "variant_seed": request.variant_seed,
            "exclude_signature": request.exclude_signature,
            "people_count": request.people_count,
            "budget": request.trip_budget,
            "currency": request.currency,
            "origin_city_name": request.origin_city_name,
            "notes": request.trip_notes,
            "trigger": trigger,
        },
        "quality_requirements": {
            "min_active_places_per_day": _min_places_per_day(request.pace),
            "max_active_places_per_day": _max_places_per_day(request.pace),
            "coordinates_required": True,
            "specific_real_poi_names_required": True,
            "coordinate_radius_km_from_destination_center": _coordinate_radius_km(request),
            "coordinates_must_be_on_land_or_exact_poi_location": True,
            "avoid_generic_names": sorted(_GENERIC_NAME_PARTS),
        },
    }


def _normalize_external_variants(
    *,
    payload: dict,
    destination_id: uuid.UUID,
    destination_name: str,
    destination_center: tuple[float, float] | None,
    trip_id: uuid.UUID | None,
    request: ItineraryGenerateRequest,
    trigger: str,
    coordinate_repair_enabled: bool,
) -> list[ItineraryGenerateResponse]:
    raw_variants = payload.get("variants")
    if not isinstance(raw_variants, list):
        return []

    normalized: list[ItineraryGenerateResponse] = []
    for fallback_index, raw_variant in enumerate(raw_variants[: _external_variant_count(request)]):
        if not isinstance(raw_variant, dict):
            continue
        days = _normalize_external_days(
            raw_days=raw_variant.get("days"),
            destination_name=destination_name,
            destination_center=destination_center,
            request=request,
            coordinate_repair_enabled=coordinate_repair_enabled,
        )
        if not _is_complete_external_route(days, request, destination_center):
            continue
        variant_index = int(raw_variant.get("variant_index") or fallback_index)
        signature_seed = compact_json(
            {
                "trip_id": str(trip_id) if trip_id else None,
                "destination": destination_name,
                "days": [[place.name for place in day.places] for day in days if day.places],
            }
        )
        route_signature = f"llm-external-{uuid.uuid5(uuid.NAMESPACE_URL, signature_seed)}"
        if request.exclude_signature and route_signature == request.exclude_signature:
            continue
        normalized.append(
            ItineraryGenerateResponse(
                destination_id=destination_id,
                duration_days=request.duration_days,
                variant_index=variant_index,
                variant_seed=(request.variant_seed or 0) + variant_index,
                route_signature=route_signature,
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
    destination_center: tuple[float, float] | None,
    request: ItineraryGenerateRequest,
    coordinate_repair_enabled: bool,
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
    coordinate_cache: dict[str, tuple[float, float]] = {}
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
            destination_center=destination_center,
            coordinate_cache=coordinate_cache,
            radius_km=_coordinate_radius_km(request),
            seen_names=seen_names,
            coordinate_repair_enabled=coordinate_repair_enabled,
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
    destination_center: tuple[float, float] | None,
    coordinate_cache: dict[str, tuple[float, float]],
    radius_km: float,
    seen_names: set[str],
    coordinate_repair_enabled: bool,
) -> list[ItineraryPlace]:
    if not isinstance(raw_places, list):
        return []
    places: list[ItineraryPlace] = []
    candidate_rows: list[tuple[int, dict, str, str, float, float]] = []
    for index, raw_place in enumerate(raw_places):
        if not isinstance(raw_place, dict):
            continue
        name = str(raw_place.get("name") or "").strip()
        normalized_name = _normalize_name(name)
        if not name or normalized_name in seen_names or _is_generic_place_name(name, destination_name):
            continue
        if _is_wrong_singular_island_place(
            place_name=name,
            place_address=raw_place.get("address"),
            destination_name=destination_name,
        ):
            continue
        lat = _float_or_none(raw_place.get("lat"))
        lng = _float_or_none(raw_place.get("lng"))
        if lat is None or lng is None or not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            continue
        candidate_rows.append((index, raw_place, name, normalized_name, lat, lng))

    repair_futures = {}
    if coordinate_repair_enabled:
        repair_futures = {
            index: _GEOCODE_EXECUTOR.submit(
                _repair_place_coordinates,
                name=name,
                address=raw_place.get("address"),
                original_lat=lat,
                original_lng=lng,
                destination_name=destination_name,
                destination_center=destination_center,
                radius_km=radius_km,
                cache=coordinate_cache,
                coordinate_repair_enabled=coordinate_repair_enabled,
            )
            for index, raw_place, name, _normalized_name, lat, lng in candidate_rows
        }

    for index, raw_place, name, normalized_name, lat, lng in candidate_rows:
        repaired = None
        if index in repair_futures:
            try:
                repaired = repair_futures[index].result(timeout=2.2)
            except Exception:
                repaired = None
        if repaired is not None:
            lat, lng = repaired
        elif _should_reject_unrepaired_coordinate(
            raw_place=raw_place,
            name=name,
            lat=lat,
            lng=lng,
            destination_center=destination_center,
            radius_km=radius_km,
            coordinate_repair_enabled=coordinate_repair_enabled,
        ):
            continue
        if any(
            existing.lat is not None
            and existing.lng is not None
            and _haversine_km(float(existing.lat), float(existing.lng), lat, lng) < 0.05
            for existing in places
        ):
            continue
        if (
            destination_center is not None
            and _haversine_km(lat, lng, destination_center[0], destination_center[1]) > radius_km
        ):
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
    return _repair_external_travel_minutes(places)


def _needs_coordinate_evidence(raw_place: dict, name: str) -> bool:
    category = _normalize_name(str(raw_place.get("category") or ""))
    normalized_name = _normalize_name(name)
    if any(token in category for token in ("beach", "view", "park", "nature", "coast", "water")):
        return True
    return bool(any(token in normalized_name for token in ("beach", "playa", "platja")))


def _should_reject_unrepaired_coordinate(
    *,
    raw_place: dict,
    name: str,
    lat: float,
    lng: float,
    destination_center: tuple[float, float] | None,
    radius_km: float,
    coordinate_repair_enabled: bool | None = None,
) -> bool:
    if destination_center is None:
        return False
    distance_km = _haversine_km(lat, lng, destination_center[0], destination_center[1])
    if distance_km > radius_km:
        return True
    if distance_km > _unverified_coordinate_radius_km(radius_km):
        return True
    if coordinate_repair_enabled is None:
        coordinate_repair_enabled = settings.LLM_EXTERNAL_ROUTE_COORDINATE_REPAIR_ENABLED
    if not coordinate_repair_enabled:
        return False
    confidence = _float_or_none(raw_place.get("confidence"))
    return _needs_coordinate_evidence(raw_place, name) and (confidence is None or confidence < 0.75)


def _repair_external_travel_minutes(places: list[ItineraryPlace]) -> list[ItineraryPlace]:
    repaired: list[ItineraryPlace] = []
    previous: ItineraryPlace | None = None
    for index, place in enumerate(places):
        travel_minutes = int(place.travel_from_previous_minutes or 0)
        if index == 0:
            travel_minutes = 0
        elif (
            travel_minutes <= 0
            and previous
            and previous.lat is not None
            and previous.lng is not None
            and place.lat is not None
            and place.lng is not None
        ):
            distance_km = _haversine_km(float(previous.lat), float(previous.lng), float(place.lat), float(place.lng))
            travel_minutes = max(5, min(75, int(distance_km / 4.5 * 60) + 3))
        repaired_place = place.model_copy(update={"travel_from_previous_minutes": travel_minutes})
        repaired.append(repaired_place)
        previous = repaired_place
    return repaired


def _clean_external_days(days: list[ItineraryDay], request: ItineraryGenerateRequest) -> list[ItineraryDay]:
    days = _remove_coordinate_outliers(days, max_distance_km=max(35.0, _coordinate_radius_km(request)))
    max_places = _max_places_per_day(request.pace)
    cleaned: list[ItineraryDay] = []
    for day in days:
        if str(day.theme or "").lower() == "rest":
            cleaned.append(day)
            continue
        places = day.places[:max_places]
        cleaned.append(day.model_copy(update={"places": places, "items": places}))
    return cleaned


def _remove_coordinate_outliers(days: list[ItineraryDay], *, max_distance_km: float = 35.0) -> list[ItineraryDay]:
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
            and _haversine_km(float(place.lat), float(place.lng), median_lat, median_lng) <= max_distance_km
        ]
        cleaned.append(day.model_copy(update={"places": places, "items": places}))
    return cleaned


def _destination_center(destination_info: dict | None) -> tuple[float, float] | None:
    if not destination_info:
        return None
    lat = _float_or_none(destination_info.get("lat"))
    lng = _float_or_none(destination_info.get("lng"))
    if lat is None or lng is None:
        return None
    return lat, lng


def _destination_name_with_geocode_context(destination_name: str, geocoded: dict[str, Any] | None) -> str:
    if not geocoded:
        return destination_name
    address = str(geocoded.get("fullAddress") or "").strip()
    if not address:
        return destination_name
    normalized_name = _normalize_name(destination_name)
    normalized_address = _normalize_name(address)
    if normalized_name and normalized_name in normalized_address:
        country = _country_context_from_address(address)
        if country and country not in destination_name:
            return f"{destination_name}, {country}"[:200]
    return destination_name


def _country_context_from_address(address: str) -> str | None:
    normalized = _normalize_name(address)
    if "испания" in normalized or "spain" in normalized or "españa" in normalized:
        return "Испания"
    if "франция" in normalized or "france" in normalized:
        return "Франция"
    if "италия" in normalized or "italy" in normalized:
        return "Италия"
    if "турция" in normalized or "turkey" in normalized:
        return "Турция"
    if "великобритания" in normalized or "united kingdom" in normalized or "uk" in normalized:
        return "Великобритания"
    if "япония" in normalized or "japan" in normalized:
        return "Япония"
    if "сша" in normalized or "usa" in normalized or "united states" in normalized:
        return "США"
    return None


def _geocode_destination_center(destination_name: str) -> tuple[float, float] | None:
    selected = _geocode_destination_context(destination_name)
    return _destination_center(selected)


def _geocode_destination_context(destination_name: str) -> dict[str, Any] | None:
    if not settings.LLM_EXTERNAL_ROUTE_COORDINATE_REPAIR_ENABLED:
        return None
    try:
        response = httpx.get(
            f"{settings.DATA_SERVICE_URL}/api/geocode/search",
            params={"q": destination_name, "results": 5},
            timeout=3.0,
        )
        if response.status_code != 200:
            return None
        items = response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        return None
    if not isinstance(items, list) or not items:
        return None
    selected = _select_destination_geocode_match(destination_name, items)
    if selected is None:
        return None
    return {
        **selected,
        "lng": selected.get("lon") or selected.get("lng"),
    }


def _select_destination_geocode_match(destination_name: str, items: list[Any]) -> dict[str, Any] | None:
    normalized_query = _normalize_name(destination_name)
    query_tokens = {
        token
        for token in re.split(r"\s+|,", normalized_query)
        if len(token) >= 4 and token not in _GEOCODE_COUNTRY_STOPWORDS
    }
    scored: list[tuple[float, dict[str, Any]]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        lat = _float_or_none(item.get("lat"))
        lng = _float_or_none(item.get("lon") or item.get("lng"))
        if lat is None or lng is None:
            continue
        name = _normalize_name(str(item.get("name") or ""))
        address = _normalize_name(str(item.get("fullAddress") or item.get("address") or ""))
        haystack = f"{name} {address}"
        locality_score = _destination_geocode_locality_score(name, address)
        score = 0.0
        if name == normalized_query:
            score += 12.0
        if normalized_query and normalized_query in name:
            score += 8.0
        if normalized_query and normalized_query in address:
            score += 6.0
        if query_tokens:
            matched = sum(1 for token in query_tokens if token in haystack)
            score += matched * 5.0
            if matched == 0:
                score -= 10.0
        if any(token in haystack for token in ("испания", "spain", "españa")):
            score += 3.0
        if any(token in haystack for token in ("франция", "france")):
            score += 3.0
        score += locality_score
        if any(token in haystack for token in ("россия", "russia", "украина", "ukraine")) and not any(
            token in normalized_query for token in ("россия", "russia", "украина", "ukraine")
        ):
            score -= 4.0
        score -= index * 0.1
        scored.append((score, item))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    if scored[0][0] >= 4.0:
        return scored[0][1]
    if len(scored) == 1 and scored[0][0] >= 0.0:
        return scored[0][1]
    return None


_GEOCODE_COUNTRY_STOPWORDS = {
    "spain",
    "испания",
    "france",
    "франция",
    "turkey",
    "турция",
    "thailand",
    "таиланд",
    "germany",
    "германия",
    "russia",
    "россия",
    "ukraine",
    "украина",
}


_GEOCODE_STREET_HINTS = {
    "street",
    "straße",
    "strasse",
    "straat",
    "landstraße",
    "landstrasse",
    "улица",
    "проспект",
    "переулок",
    "шоссе",
    "road",
    "rd",
    "avenue",
    "ave",
    "bahnhof",
}


_GEOCODE_LOCALITY_HINTS = {
    "district",
    "province",
    "region",
    "область",
    "регион",
    "район",
    "остров",
    "island",
    "islands",
    "город",
    "city",
}


def _destination_geocode_locality_score(name: str, address: str) -> float:
    score = 0.0
    if any(hint in address for hint in _GEOCODE_STREET_HINTS):
        score -= 28.0
    if re.search(r"\b\d{1,5}[a-zа-я]?\b", address):
        score -= 8.0
    if any(hint in f"{name} {address}" for hint in _GEOCODE_LOCALITY_HINTS):
        score += 10.0
    return score


def _is_wrong_singular_island_place(*, place_name: str, place_address: object, destination_name: str) -> bool:
    destination_text = _normalize_name(destination_name.split(",", 1)[0])
    if not _is_singular_island_destination(destination_text):
        return False
    destination_aliases = _singular_island_aliases(destination_text)
    if not destination_aliases:
        return False
    place_text = _normalize_name(f"{place_name} {place_address or ''}")
    island_mentions = re.findall(r"\b(?:ko|koh)\s+[\w']+", place_text)
    if not island_mentions and " island" not in place_text:
        return False
    return not any(alias in place_text for alias in destination_aliases)


def _is_singular_island_destination(destination_text: str) -> bool:
    if any(token in destination_text for token in ("islands", "острова", "archipelago")):
        return False
    return bool(
        re.search(r"\b(?:ko|koh)\s+[\w']+", destination_text)
        or " island" in destination_text
        or "остров " in destination_text
    )


def _singular_island_aliases(destination_text: str) -> set[str]:
    aliases = {destination_text}
    for match in re.finditer(r"\b(ko|koh)\s+([\w']+)", destination_text):
        island_name = match.group(2)
        aliases.add(f"ko {island_name}")
        aliases.add(f"koh {island_name}")
    if destination_text.endswith(" island"):
        base = destination_text[: -len(" island")].strip()
        if base:
            aliases.add(base)
            aliases.add(f"{base} island")
    return {alias for alias in aliases if alias}


def _repair_place_coordinates(
    *,
    name: str,
    address: object,
    original_lat: float,
    original_lng: float,
    destination_name: str,
    destination_center: tuple[float, float] | None,
    radius_km: float,
    cache: dict[str, tuple[float, float]],
    coordinate_repair_enabled: bool,
) -> tuple[float, float] | None:
    if not coordinate_repair_enabled or destination_center is None:
        return None
    queries = _coordinate_repair_queries(name=name, address=address, destination_name=destination_name)
    cache_key = _normalize_name("|".join(queries))
    if cache_key in cache:
        return cache[cache_key]
    for query in queries:
        try:
            response = httpx.get(
                f"{settings.DATA_SERVICE_URL}/api/geocode/search",
                params={
                    "q": query,
                    "results": 3,
                    "bias_lat": destination_center[0],
                    "bias_lon": destination_center[1],
                },
                timeout=1.8,
            )
            if response.status_code != 200:
                continue
            items = response.json()
        except (httpx.HTTPError, ValueError, TypeError):
            continue
        if not isinstance(items, list) or not items:
            continue
        for item in items[:3]:
            if _is_destination_only_geocode_result(item, name, destination_name):
                continue
            if not _geocode_item_matches_place(item, name):
                continue
            lat = _float_or_none(item.get("lat"))
            lng = _float_or_none(item.get("lon") or item.get("lng"))
            if lat is None or lng is None:
                continue
            if _haversine_km(lat, lng, destination_center[0], destination_center[1]) > radius_km:
                continue
            cache[cache_key] = (lat, lng)
            return cache[cache_key]
    return None


def _coordinate_repair_queries(*, name: str, address: object, destination_name: str) -> list[str]:
    address_text = str(address or "").strip()
    clean_name = _clean_geocode_place_name(name)
    names = [clean_name]
    base_name = clean_name.split(" - ", 1)[0].strip()
    if base_name and base_name not in names:
        names.append(base_name)
    spaced_name = base_name.replace("PortAventura", "Port Aventura").strip()
    if spaced_name and spaced_name not in names:
        names.append(spaced_name)
    compact_words = ["main entrance", "entrance", "branch"]
    for word in compact_words:
        lowered = base_name.lower()
        if word in lowered:
            cleaned = base_name[: lowered.find(word)].strip(" -,:")
            if cleaned and cleaned not in names:
                names.append(cleaned)
    for suffix in (" world",):
        lowered = base_name.lower()
        if lowered.endswith(suffix):
            cleaned = base_name[: -len(suffix)].strip(" -,:")
            spaced_cleaned = cleaned.replace("PortAventura", "Port Aventura").strip()
            for value in (cleaned, spaced_cleaned):
                if value and value not in names:
                    names.append(value)

    queries: list[str] = []
    for candidate_name in names:
        plain_query = ", ".join(part for part in [candidate_name, destination_name] if part)
        if plain_query not in queries:
            queries.append(plain_query)
        parts = [candidate_name]
        if address_text:
            parts.append(address_text)
        parts.append(destination_name)
        query = ", ".join(part for part in parts if part)
        if query not in queries:
            queries.append(query)
    return queries


def _clean_geocode_place_name(name: str) -> str:
    cleaned = re.sub(r"\([^)]*\)", "", name).strip()
    cleaned = re.sub(r"\b(external view|plaza|viewpoint|view point|main entrance|entrance)\b", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -,:")
    return cleaned or name.strip()


def _is_destination_only_geocode_result(item: dict, place_name: str, destination_name: str) -> bool:
    result_name = _normalize_name(str(item.get("name") or ""))
    normalized_place = _normalize_name(place_name)
    normalized_destination = _normalize_name(destination_name.split(",")[0])
    if not result_name or result_name == normalized_place:
        return False
    return result_name == normalized_destination


def _geocode_item_matches_place(item: dict, place_name: str) -> bool:
    result_text = _normalize_name(
        " ".join(str(item.get(key) or "") for key in ("name", "fullAddress", "address", "display_name"))
    )
    if not result_text:
        return False
    place_text = _normalize_name(place_name)
    compact_result = result_text.replace(" ", "")
    compact_place = place_text.replace(" ", "")
    if compact_place and compact_place in compact_result:
        return True
    tokens = {
        token
        for token in re.findall(r"[\w']+", place_text)
        if len(token) >= 4 and token not in _GEOCODE_PLACE_STOPWORDS
    }
    if not tokens:
        return True
    return any(token in result_text or token.replace("'", "") in compact_result for token in tokens)


def _coordinate_radius_km(request: ItineraryGenerateRequest) -> float:
    destination_text = f"{request.destination_text or ''}".lower()
    if "islands" in destination_text or "острова" in destination_text or "archipelago" in destination_text:
        return 250.0
    if (
        "koh " in destination_text
        or "ko " in destination_text
        or "island" in destination_text
        or "остров" in destination_text
    ):
        return 45.0
    if request.duration_days >= 7:
        return 45.0
    if request.duration_days >= 4:
        return 35.0
    return 12.0


def _unverified_coordinate_radius_km(radius_km: float) -> float:
    if radius_km >= 45.0:
        return radius_km
    if radius_km >= 35.0:
        return 18.0
    return 5.0


def _max_places_per_day(pace: str | None) -> int:
    normalized = str(pace or "").lower()
    if normalized in {"slow", "relaxed", "low"}:
        return 3
    if normalized in {"fast", "intense", "high"}:
        return 5
    return 4


def _min_places_per_day(pace: str | None) -> int:
    normalized = str(pace or "").lower()
    if normalized in {"slow", "relaxed", "low"}:
        return 3
    if normalized in {"fast", "intense", "high"}:
        return 4
    return 4


def _external_variant_count(request: ItineraryGenerateRequest) -> int:
    return max(1, min(1, request.variant_count))


def _external_route_request(request: ItineraryGenerateRequest, trigger: str) -> ItineraryGenerateRequest:
    if trigger in {"manual_destination", "data_service_no_feasible", "data_service_no_template"}:
        return request.model_copy(update={"variant_count": 1})
    return request.model_copy(update={"variant_count": 1})


def _active_day_count(request: ItineraryGenerateRequest) -> int:
    return request.duration_days - len(_rest_days(request.duration_days, request.rest_days_count))


def _is_complete_external_route(
    days: list[ItineraryDay],
    request: ItineraryGenerateRequest,
    destination_center: tuple[float, float] | None,
) -> bool:
    if len(days) != request.duration_days:
        return False
    active_places = [place for day in days if str(day.theme or "").lower() != "rest" for place in day.places]
    if destination_center is not None and active_places:
        median_lat = sorted(float(place.lat) for place in active_places if place.lat is not None)[
            len(active_places) // 2
        ]
        median_lng = sorted(float(place.lng) for place in active_places if place.lng is not None)[
            len(active_places) // 2
        ]
        if _haversine_km(
            median_lat, median_lng, destination_center[0], destination_center[1]
        ) > _route_cluster_radius_km(request):
            return False
    for day in days:
        if str(day.theme or "").lower() == "rest":
            continue
        if len(day.places) < _validated_min_places_per_day(request.pace):
            return False
        if any(place.lat is None or place.lng is None for place in day.places):
            return False
    return True


def _route_cluster_radius_km(request: ItineraryGenerateRequest) -> float:
    return max(6.0, _coordinate_radius_km(request) * 0.7)


def _validated_min_places_per_day(pace: str | None) -> int:
    return max(2, _min_places_per_day(pace) - 2)


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
