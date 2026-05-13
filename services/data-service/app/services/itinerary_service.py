"""Itinerary generation using POI scoring and constrained template optimization."""

import hashlib
import math
import random
from datetime import datetime, time, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.lib import OpeningHoursParser
from app.models import NameTranslationEntity
from app.services.name_translation_service import load_translations, poi_display_payload


def generate_itinerary(
    db: Session,
    destination_id: str,
    duration_days: int,
    preferred_activities: list[str],
    start_date: datetime | None = None,
    variant_count: int = 1,
    variant_seed: int | None = None,
    pace: str = "standard",
    day_start_time: time = time(9, 30),
    day_end_time: time = time(19, 0),
    rest_days_count: int = 0,
    exclude_signature: str | None = None,
    trip_budget: float | None = None,
    people_count: int = 1,
) -> dict:
    from app.models import POI, Trajectory

    trajectories = (
        db.query(Trajectory)
        .filter(Trajectory.destination_id == destination_id)
        .order_by(func.abs(Trajectory.duration_days - duration_days))
        .limit(10)
        .all()
    )

    if not trajectories:
        return {
            "error": "No itinerary template available for this destination.",
            "destination_id": destination_id,
        }

    all_poi_ids = sorted(
        {
            poi_id
            for trajectory in trajectories
            for day_data in trajectory.sequence_of_poi
            for poi_id in day_data.get("poi_ids", [])
        }
    )
    poi_map = {str(p.id): p for p in db.query(POI).filter(POI.id.in_(all_poi_ids)).all()}
    templates = select_best_templates(
        trajectories=trajectories,
        duration_days=duration_days,
        preferred_activities=preferred_activities,
        poi_map=poi_map,
        start_date=start_date,
    )
    if not templates:
        return {
            "error": "No itinerary template available for this destination.",
            "destination_id": destination_id,
        }

    poi_translations = load_translations(db, NameTranslationEntity.poi, [p.id for p in poi_map.values()])
    variants = []
    seed = int(variant_seed or 7301)
    attempts = max(variant_count * 3, variant_count)
    for offset in range(attempts):
        template = templates[offset % len(templates)]
        variant = build_variant(
            template=template,
            poi_map=poi_map,
            translations=poi_translations,
            destination_id=destination_id,
            duration_days=duration_days,
            preferred_activities=preferred_activities,
            start_date=start_date,
            variant_seed=seed + offset,
            variant_index=len(variants),
            pace=pace,
            day_start_time=day_start_time,
            day_end_time=day_end_time,
            rest_days_count=rest_days_count,
            trip_budget=trip_budget,
            people_count=people_count,
        )
        if variant is None:
            continue
        if variant["route_signature"] == exclude_signature:
            continue
        if variant["route_signature"] in {v["route_signature"] for v in variants}:
            continue
        variants.append(variant)
        if len(variants) >= variant_count:
            break

    if not variants:
        return {
            "error": "No feasible itinerary for the selected trip parameters.",
            "destination_id": destination_id,
            "duration_days": duration_days,
            "variants": [],
        }

    first = variants[0]
    return {
        **first,
        "variants": variants,
        "activity_tags": first["activity_tags"],
    }


def visit_datetime(start_date: datetime | None, day_idx: int) -> datetime:
    visit_dt = (start_date + timedelta(days=day_idx)) if start_date else datetime.now()
    return visit_dt.replace(hour=12, minute=0, second=0)


def visit_datetime_at(start_date: datetime | None, day_idx: int, current_time: time) -> datetime:
    visit_dt = (start_date + timedelta(days=day_idx)) if start_date else datetime.now()
    return visit_dt.replace(hour=current_time.hour, minute=current_time.minute, second=0, microsecond=0)


def dedupe_poi_ids(poi_ids: list[Any], used_poi_ids: set[str] | None = None) -> list[Any]:
    used = used_poi_ids or set()
    seen: set[str] = set()
    result = []
    for poi_id in poi_ids:
        key = str(poi_id)
        if key in seen or key in used:
            continue
        seen.add(key)
        result.append(poi_id)
    return result


def is_usable_poi(poi: Any) -> bool:
    name = str(getattr(poi, "name", "") or "").strip()
    return bool(name and getattr(poi, "lat", None) is not None and getattr(poi, "lng", None) is not None)


def poi_quality_score(poi: Any, visit_dt: datetime | None = None) -> float:
    if not is_usable_poi(poi):
        return -2.0
    score = 1.0
    if getattr(poi, "visit_duration_minutes", None):
        score += 0.25
    if getattr(poi, "popularity_score", None) is not None:
        score += min(0.4, max(0.0, float(poi.popularity_score)) / 2.5)
    if str(getattr(poi, "name", "") or "").strip().lower() in {"untitled place", "unknown", "без названия"}:
        score -= 0.4
    opening_hours = getattr(poi, "opening_hours", None)
    if visit_dt is not None and opening_hours:
        score += 0.2 if OpeningHoursParser.is_open(opening_hours, visit_dt) else -0.3
    return score


def poi_relevance_score(
    poi: Any,
    preferred_activities: list[str],
    visit_dt: datetime | None,
    trip_budget: float | None,
    people_count: int,
) -> float:
    score = poi_quality_score(poi, visit_dt)
    prefs = {item.lower() for item in preferred_activities}
    category = str(getattr(poi, "category", "") or "").lower()
    tags = {str(tag).lower() for tag in (getattr(poi, "tags", None) or [])}
    if category in prefs or tags & prefs:
        score += 1.4
    popularity = getattr(poi, "popularity_score", None)
    if popularity is not None:
        score += min(1.0, max(0.0, float(popularity)))
    fee = getattr(poi, "entrance_fee_usd", None)
    if fee and trip_budget is not None:
        party_fee = float(fee) * max(people_count, 1)
        if party_fee > trip_budget * 0.08:
            score -= 0.7
    return score


def template_score(
    trajectory: Any,
    duration_days: int,
    preferred_activities: list[str],
    poi_map: dict[str, Any],
    start_date: datetime | None = None,
) -> float:
    duration_gap = abs(int(trajectory.duration_days) - duration_days)
    prefs = {str(item).lower() for item in preferred_activities}
    tags = {str(item).lower() for item in (trajectory.activity_tags or [])}
    activity_overlap = len(tags & prefs) / max(len(prefs), 1) if prefs else 0.0

    requested_days = trajectory.sequence_of_poi[:duration_days]
    poi_ids = [poi_id for day_data in requested_days for poi_id in day_data.get("poi_ids", [])]
    unique_poi_ids = dedupe_poi_ids(poi_ids)
    available = [poi_map[str(poi_id)] for poi_id in unique_poi_ids if str(poi_id) in poi_map]
    availability = len(available) / max(len(unique_poi_ids), 1)
    quality = sum(
        poi_quality_score(poi, visit_datetime(start_date, 0) if start_date else None) for poi in available
    ) / max(len(available), 1)

    return (
        (1.0 if duration_gap == 0 else 0.0)
        - duration_gap * 0.35
        + activity_overlap * 1.8
        + availability * 1.2
        + quality * 0.35
    )


def select_best_template(
    trajectories: list[Any],
    duration_days: int,
    preferred_activities: list[str],
    poi_map: dict[str, Any],
    start_date: datetime | None = None,
) -> Any | None:
    if not trajectories:
        return None
    return select_best_templates(
        trajectories=trajectories,
        duration_days=duration_days,
        preferred_activities=preferred_activities,
        poi_map=poi_map,
        start_date=start_date,
    )[0]


def select_best_templates(
    trajectories: list[Any],
    duration_days: int,
    preferred_activities: list[str],
    poi_map: dict[str, Any],
    start_date: datetime | None = None,
) -> list[Any]:
    if not trajectories:
        return []
    return sorted(
        trajectories,
        key=lambda trajectory: template_score(
            trajectory=trajectory,
            duration_days=duration_days,
            preferred_activities=preferred_activities,
            poi_map=poi_map,
            start_date=start_date,
        ),
        reverse=True,
    )


def route_signature(days: list[dict]) -> str:
    poi_ids = [str(place["poi_id"]) for day in days for place in day.get("items", []) if place.get("poi_id")]
    return hashlib.sha1("|".join(poi_ids).encode("utf-8")).hexdigest()[:24]


def rest_day_numbers(duration_days: int, rest_days_count: int) -> set[int]:
    rest_count = max(0, min(rest_days_count, duration_days))
    if rest_count == 0:
        return set()
    if rest_count == duration_days:
        return set(range(1, duration_days + 1))
    positions = {
        min(duration_days, max(1, round((idx + 1) * (duration_days + 1) / (rest_count + 1))))
        for idx in range(rest_count)
    }
    candidate = 1
    while len(positions) < rest_count:
        positions.add(candidate)
        candidate += 1
    return positions


def template_day_payload(template: Any, active_day_idx: int) -> dict:
    if active_day_idx < len(template.sequence_of_poi):
        return template.sequence_of_poi[active_day_idx]
    if template.sequence_of_poi:
        return template.sequence_of_poi[active_day_idx % len(template.sequence_of_poi)]
    return {"day": active_day_idx + 1, "theme": "free", "poi_ids": []}


def build_variant(
    template: Any,
    poi_map: dict[str, Any],
    translations: dict,
    destination_id: str,
    duration_days: int,
    preferred_activities: list[str],
    start_date: datetime | None,
    variant_seed: int,
    variant_index: int,
    pace: str,
    day_start_time: time,
    day_end_time: time,
    rest_days_count: int,
    trip_budget: float | None,
    people_count: int,
) -> dict | None:
    rng = random.Random(variant_seed)
    max_per_day = {"relaxed": 3, "standard": 4, "intense": 5}.get(pace, 4)
    used_poi_ids: set[str] = set()
    rest_days = rest_day_numbers(duration_days, rest_days_count)
    days = []
    total_score = 0.0
    total_travel = 0
    opening_warnings = 0
    active_day_idx = 0
    for day_idx in range(duration_days):
        day_number = day_idx + 1
        if day_number in rest_days:
            days.append(
                {
                    "day": day_number,
                    "day_number": day_number,
                    "theme": "rest",
                    "start_time": None,
                    "end_time": None,
                    "places": [],
                    "items": [],
                    "total_score": 0.0,
                }
            )
            continue

        day_data = template_day_payload(template, active_day_idx)
        active_day_idx += 1
        candidates = []
        for poi_id in dedupe_poi_ids(day_data.get("poi_ids", []), used_poi_ids):
            poi = poi_map.get(str(poi_id))
            if poi and is_usable_poi(poi):
                candidates.append(poi)
        candidates.sort(
            key=lambda poi: (
                poi_relevance_score(
                    poi,
                    preferred_activities,
                    visit_datetime_at(start_date, day_idx, day_start_time),
                    trip_budget,
                    people_count,
                ),
                rng.random(),
            ),
            reverse=True,
        )
        day_items, day_score, day_travel, day_opening_warnings = schedule_day(
            candidates=candidates[: max_per_day + 2],
            translations=translations,
            start_date=start_date,
            day_idx=day_idx,
            day_start_time=day_start_time,
            day_end_time=day_end_time,
            preferred_activities=preferred_activities,
            trip_budget=trip_budget,
            people_count=people_count,
            max_per_day=max_per_day,
            used_poi_ids=used_poi_ids,
        )
        total_score += day_score
        total_travel += day_travel
        opening_warnings += day_opening_warnings
        if not day_items:
            return None
        days.append(
            {
                "day": day_number,
                "day_number": day_number,
                "theme": day_data.get("theme", "urban"),
                "start_time": day_start_time.isoformat(timespec="minutes"),
                "end_time": day_end_time.isoformat(timespec="minutes"),
                "places": day_items,
                "items": day_items,
                "total_score": round(day_score, 4),
            }
        )

    signature = route_signature(days)
    total_poi = sum(len(day["items"]) for day in days)
    return {
        "destination_id": destination_id,
        "duration_days": duration_days,
        "variant_index": variant_index,
        "variant_seed": variant_seed,
        "route_signature": signature,
        "model_version": "itinerary-poi-ranker-v1",
        "days": days,
        "activity_tags": template.activity_tags,
        "source": "optimized-heuristic",
        "has_template": True,
        "score_summary": {
            "total_pois": total_poi,
            "total_score": round(total_score, 4),
            "travel_overhead_minutes": total_travel,
            "opening_hours_warnings": opening_warnings,
            "opening_hours_violations": opening_warnings,
            "rest_days_count": len(rest_days),
            "avg_relevance": round(total_score / max(total_poi, 1), 4),
        },
    }


def schedule_day(
    candidates: list[Any],
    translations: dict,
    start_date: datetime | None,
    day_idx: int,
    day_start_time: time,
    day_end_time: time,
    preferred_activities: list[str],
    trip_budget: float | None,
    people_count: int,
    max_per_day: int,
    used_poi_ids: set[str],
) -> tuple[list[dict], float, int, int]:
    current_dt = visit_datetime_at(start_date, day_idx, day_start_time)
    end_dt = visit_datetime_at(start_date, day_idx, day_end_time)
    prev = None
    result = []
    total_score = 0.0
    total_travel = 0
    opening_warnings = 0
    for poi in candidates:
        if len(result) >= max_per_day:
            break
        key = str(poi.id)
        if key in used_poi_ids:
            continue
        travel_minutes = estimate_travel_minutes(prev, poi) if prev else 0
        arrival_dt = current_dt + timedelta(minutes=travel_minutes)
        duration = int(getattr(poi, "visit_duration_minutes", None) or default_duration(getattr(poi, "category", "")))
        departure_dt = arrival_dt + timedelta(minutes=duration)
        if departure_dt > end_dt:
            continue
        opening_status = opening_status_for(poi, arrival_dt)
        if opening_status == "closed":
            opening_warnings += 1
            continue
        score = poi_relevance_score(poi, preferred_activities, arrival_dt, trip_budget, people_count)
        payload = itinerary_place_payload(
            poi=poi,
            translations=translations,
            visit_dt=arrival_dt,
            arrival_dt=arrival_dt,
            departure_dt=departure_dt,
            travel_minutes=travel_minutes,
            opening_status=opening_status,
            score=score,
        )
        result.append(payload)
        used_poi_ids.add(key)
        total_score += score
        total_travel += travel_minutes
        current_dt = departure_dt + timedelta(minutes=20)
        prev = poi
    return result, total_score, total_travel, opening_warnings


def default_duration(category: str) -> int:
    return {
        "museum": 120,
        "culture": 90,
        "historic": 90,
        "heritage": 90,
        "nature": 120,
        "beach": 180,
        "food": 60,
        "nightlife": 120,
        "shopping": 75,
        "viewpoint": 35,
    }.get(str(category).lower(), 90)


def estimate_travel_minutes(prev: Any, poi: Any) -> int:
    distance = haversine_km(float(prev.lat), float(prev.lng), float(poi.lat), float(poi.lng))
    return max(5, min(75, int(distance / 20 * 60) + 5))


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return radius * 2 * math.asin(math.sqrt(a))


def opening_status_for(poi: Any, visit_dt: datetime) -> str:
    opening_hours = getattr(poi, "opening_hours", None)
    if not opening_hours:
        return "unknown"
    return "open" if OpeningHoursParser.is_open(opening_hours, visit_dt) else "closed"


def itinerary_place_payload(
    poi: Any,
    translations: dict,
    visit_dt: datetime,
    arrival_dt: datetime | None = None,
    departure_dt: datetime | None = None,
    travel_minutes: int = 0,
    opening_status: str | None = None,
    score: float | None = None,
) -> dict:
    return {
        "id": str(poi.id),
        "poi_id": str(poi.id),
        "category": poi.category,
        "lat": poi.lat,
        "lng": poi.lng,
        "popularity_score": poi.popularity_score,
        "address": poi.address,
        "opening_hours": poi.opening_hours,
        "is_open_at_midday": OpeningHoursParser.is_open(poi.opening_hours, visit_dt),
        "opening_status": opening_status or opening_status_for(poi, visit_dt),
        "arrival_time": (arrival_dt or visit_dt).time().isoformat(timespec="minutes"),
        "departure_time": (departure_dt or visit_dt).time().isoformat(timespec="minutes"),
        "travel_from_previous_minutes": travel_minutes,
        "visit_duration_minutes": poi.visit_duration_minutes,
        "duration_minutes": poi.visit_duration_minutes,
        "price_tier": getattr(poi, "price_tier", None),
        "entrance_fee_usd": getattr(poi, "entrance_fee_usd", None),
        "score": round(float(score), 4) if score is not None else None,
        **poi_display_payload(str(poi.id), poi.name, translations),
    }
