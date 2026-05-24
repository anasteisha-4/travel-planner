"""Itinerary generation using POI scoring and constrained template optimization."""

import hashlib
import itertools
import math
import random
import re
from datetime import date, datetime, time, timedelta
from types import SimpleNamespace
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.lib import OpeningHoursParser
from app.models import NameTranslationEntity
from app.services.name_translation_service import load_translations, poi_display_payload

_LOW_SIGNAL_NAMES = {
    "book",
    "книга",
    "family",
    "семья",
    "love stone",
    "камень любви",
    "direction sign",
    "указатель направлений",
    "strange girl",
    "странная девушка",
}

# Category priors separate "destination-defining" POI (heritage, museums,
# nature) from supporting stops (shopping, nightlife). They are small enough to
# be overridden by user preferences and POI quality.
_CATEGORY_PRIOR = {
    "heritage": 1.1,
    "museum": 1.0,
    "historic": 0.9,
    "viewpoint": 0.8,
    "nature": 0.75,
    "beach": 0.75,
    "food": 0.55,
    "urban": 0.35,
    "shopping": 0.25,
    "culture": 0.2,
    "nightlife": 0.15,
}

_ROUTE_TRAVEL_MINUTE_PENALTY = 0.015
_ROUTE_CATEGORY_REPEAT_PENALTY = 0.12
_MAX_CROSS_DAY_SWAP_ATTEMPTS = 700
_ROUTE_DISTANCE_PENALTY_CAP = 2.0
_ROUTE_DISTANCE_PENALTY_DIVISOR_KM = 12.0
_POI_MIN_SCORE = 1.65
_DEFAULT_DESTINATION_RADIUS_KM = 35.0
_MIN_DESTINATION_RADIUS_KM = 12.0
_MAX_DESTINATION_RADIUS_KM = 60.0
_DESTINATION_RADIUS_MULTIPLIER = 1.6
_ISLAND_DESTINATION_RADIUS_KM = 120.0
_MIN_CANDIDATE_QUERY_LIMIT = 300
_MAX_CANDIDATE_QUERY_LIMIT = 1800
_CANDIDATE_POOL_MULTIPLIER = 18
_CROWD_INDEX_HIGH_THRESHOLD = 0.72
_LOW_POPULARITY_IN_CROWDED_DESTINATION = 0.35
_CROWDED_DESTINATION_LOW_POI_PENALTY = 0.25
_SAME_DAY_CATEGORY_REPEAT_PENALTY = 0.35
_SAME_DAY_CATEGORY_DIVERSITY_BONUS = 0.25
_PAID_POI_BUDGET_SHARE_THRESHOLD = 0.08
_PAID_POI_BUDGET_PENALTY = 0.7
_DWELL_BUFFER_MINUTES = 20
_ASSUMED_ROUTE_SPEED_KMH = 20.0
_TRAVEL_TIME_FIXED_BUFFER_MINUTES = 5
_MIN_TRAVEL_MINUTES = 5
_MAX_TRAVEL_MINUTES = 75


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
    poi_sources: list[str] | None = None,
) -> dict:
    from app.models import POI, Destination, DestinationPopularity, Trajectory

    destination = db.query(Destination).filter(Destination.id == destination_id).first()
    destination_center = (float(destination.lat), float(destination.lng)) if destination else None
    destination_radius_km = _destination_radius_km(destination)
    travel_month = int(start_date.month) if start_date else datetime.now().month
    destination_popularity = (
        db.query(DestinationPopularity)
        .filter(DestinationPopularity.destination_id == destination_id, DestinationPopularity.month == travel_month)
        .first()
    )

    trajectories = (
        db.query(Trajectory)
        .filter(Trajectory.destination_id == destination_id)
        .order_by(func.abs(Trajectory.duration_days - duration_days))
        .limit(10)
        .all()
    )

    all_poi_ids = sorted(
        {
            poi_id
            for trajectory in trajectories
            for day_data in trajectory.sequence_of_poi
            for poi_id in day_data.get("poi_ids", [])
        }
    )
    template_query = db.query(POI).filter(POI.id.in_(all_poi_ids)) if all_poi_ids else None
    supplemental_query = db.query(POI).filter(
        POI.destination_id == destination_id, POI.lat.isnot(None), POI.lng.isnot(None)
    )
    if poi_sources:
        template_query = template_query.filter(POI.source.in_(poi_sources)) if template_query is not None else None
        supplemental_query = supplemental_query.filter(POI.source.in_(poi_sources))
    template_pois = template_query.all() if template_query is not None else []
    supplemental_pois = (
        supplemental_query.order_by(POI.popularity_score.desc().nullslast())
        .limit(_candidate_query_limit(duration_days, pace, rest_days_count))
        .all()
    )
    trajectory_prior = _trajectory_prior_counts(trajectories)
    candidate_pois = _ranked_destination_pois(
        _dedupe_pois([*template_pois, *supplemental_pois]),
        preferred_activities=preferred_activities,
        destination_center=destination_center,
        destination_radius_km=destination_radius_km,
        start_date=start_date,
        trip_budget=trip_budget,
        people_count=people_count,
        trajectory_prior=trajectory_prior,
        crowd_index=float(destination_popularity.crowd_index) if destination_popularity else None,
    )
    if not candidate_pois:
        return {
            "error": "No usable POI pool available for this destination.",
            "reason_code": "no_usable_poi_pool",
            "destination_id": destination_id,
        }

    poi_translations = load_translations(db, NameTranslationEntity.poi, [p.id for p in candidate_pois])
    variants = []
    seed = int(variant_seed or 7301)
    attempts = max(variant_count * 5, variant_count)
    fallback_pace_used: str | None = None
    for attempted_pace in _feasible_pace_sequence(pace):
        for offset in range(attempts):
            variant = build_personalized_variant(
                candidate_pois=candidate_pois,
                translations=poi_translations,
                destination_id=destination_id,
                duration_days=duration_days,
                preferred_activities=preferred_activities,
                start_date=start_date,
                variant_seed=seed + offset,
                variant_index=len(variants),
                pace=attempted_pace,
                day_start_time=day_start_time,
                day_end_time=day_end_time,
                rest_days_count=rest_days_count,
                trip_budget=trip_budget,
                people_count=people_count,
                destination_popularity=destination_popularity,
                trajectories_available=bool(trajectories),
                trajectory_prior=trajectory_prior,
            )
            if variant is None:
                continue
            if variant["route_signature"] == exclude_signature:
                continue
            if variant["route_signature"] in {v["route_signature"] for v in variants}:
                continue
            if attempted_pace != pace:
                fallback_pace_used = attempted_pace
                summary = dict(variant.get("score_summary") or {})
                summary["requested_pace"] = pace
                summary["fallback_pace"] = attempted_pace
                summary["fallback_reason"] = "requested_pace_infeasible_after_constraints"
                variant["score_summary"] = summary
                variant["model_version"] = f"{variant.get('model_version', 'orienteering-heuristic-v2')}:fallback-pace"
            variants.append(variant)
            if len(variants) >= variant_count:
                break
        if variants:
            break

    if not variants:
        return {
            "error": "No feasible itinerary for the selected trip parameters.",
            "reason_code": "insufficient_feasible_poi_after_constraints",
            "destination_id": destination_id,
            "duration_days": duration_days,
            "variants": [],
        }

    first = variants[0]
    if fallback_pace_used:
        variants = [
            {
                **variant,
                "score_summary": {
                    **dict(variant.get("score_summary") or {}),
                    "requested_pace": pace,
                    "fallback_pace": fallback_pace_used,
                    "fallback_reason": "requested_pace_infeasible_after_constraints",
                },
            }
            for variant in variants
        ]
        first = variants[0]
    return {
        **first,
        "variants": variants,
        "activity_tags": first["activity_tags"],
    }


def _feasible_pace_sequence(pace: str) -> list[str]:
    normalized = str(pace or "standard").lower()
    if normalized in {"fast", "intense", "high"}:
        return [pace, "standard", "relaxed"]
    if normalized in {"standard", "medium", "normal"}:
        return [pace, "relaxed"]
    return [pace]


def _as_datetime(value: date | datetime | None) -> datetime:
    if value is None:
        return datetime.now()
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, time.min)


def visit_datetime(start_date: date | datetime | None, day_idx: int) -> datetime:
    visit_dt = _as_datetime(start_date) + timedelta(days=day_idx)
    return visit_dt.replace(hour=12, minute=0, second=0)


def visit_datetime_at(start_date: date | datetime | None, day_idx: int, current_time: time) -> datetime:
    visit_dt = _as_datetime(start_date) + timedelta(days=day_idx)
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


def _name_quality_score(name: str) -> float:
    normalized = " ".join(name.casefold().replace('"', "").split())
    if not normalized:
        return -2.0
    score = 0.0
    if normalized in _LOW_SIGNAL_NAMES:
        score -= 2.0
    if len(normalized) <= 4:
        score -= 0.5
    if re.fullmatch(r"[а-яёa-z]+", normalized) and len(normalized) <= 8:
        score -= 0.55
    if re.search(r"\b[а-яё]\.\s*[а-яё]\.|\b[a-z]\.\s*[a-z]\.", normalized, re.I):
        score -= 1.0
    if re.search(r"\b(ту|tu|boeing|airbus|yak|як|ил|il)-?\d", normalized, re.I):
        score -= 1.0
    if re.search(r"\b(street|улица|ул\.?|avenue|road)\b.*\d|\d+,\s*[a-zа-яё ]+$", normalized, re.I):
        score -= 2.0
    if re.search(r"\b(building|house of|complex|корпус|здание)\b", normalized, re.I):
        score -= 0.45
    if re.search(r"\b(museum|музей|gallery|галерея|theatre|театр|cathedral|собор|park|парк)\b", normalized, re.I):
        score += 0.45
    if len(normalized.split()) >= 2:
        score += 0.2
    return score


def poi_quality_score(poi: Any, visit_dt: datetime | None = None) -> float:
    if not is_usable_poi(poi):
        return -2.0
    score = 1.0
    name = str(getattr(poi, "name", "") or "").strip()
    score += _name_quality_score(name)
    score += _CATEGORY_PRIOR.get(str(getattr(poi, "category", "") or "").lower(), 0.0)
    if getattr(poi, "visit_duration_minutes", None):
        score += 0.25
    if getattr(poi, "popularity_score", None) is not None:
        score += min(0.9, max(0.0, float(poi.popularity_score)) / 1.4)
    if name.lower() in {"untitled place", "unknown", "без названия"}:
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
        if party_fee > trip_budget * _PAID_POI_BUDGET_SHARE_THRESHOLD:
            score -= _PAID_POI_BUDGET_PENALTY
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


def _destination_radius_km(destination: Any | None) -> float:
    if destination is None:
        return _DEFAULT_DESTINATION_RADIUS_KM
    name = str(getattr(destination, "name", "") or "").casefold()
    radius_m = int(getattr(destination, "radius_m", 0) or 0)
    base = max(
        _MIN_DESTINATION_RADIUS_KM,
        min(
            _MAX_DESTINATION_RADIUS_KM,
            radius_m / 1000 * _DESTINATION_RADIUS_MULTIPLIER if radius_m else _DEFAULT_DESTINATION_RADIUS_KM,
        ),
    )
    if any(token in name for token in ("island", "islands", "canary", "остров")):
        return max(base, _ISLAND_DESTINATION_RADIUS_KM)
    return base


def _candidate_query_limit(duration_days: int, pace: str, rest_days_count: int) -> int:
    max_per_day = {"relaxed": 3, "standard": 4, "intense": 5}.get(pace, 4)
    active_days = max(1, duration_days - min(rest_days_count, duration_days))
    return max(
        _MIN_CANDIDATE_QUERY_LIMIT,
        min(_MAX_CANDIDATE_QUERY_LIMIT, active_days * max_per_day * _CANDIDATE_POOL_MULTIPLIER),
    )


def _dedupe_pois(pois: list[Any]) -> list[Any]:
    result = []
    seen: set[str] = set()
    for poi in pois:
        key = str(getattr(poi, "id", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(poi)
    return result


def _trajectory_prior_counts(trajectories: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for trajectory in trajectories:
        for day_data in trajectory.sequence_of_poi or []:
            for poi_id in day_data.get("poi_ids", []):
                key = str(poi_id)
                counts[key] = counts.get(key, 0) + 1
    return counts


def _ranked_destination_pois(
    pois: list[Any],
    *,
    preferred_activities: list[str],
    destination_center: tuple[float, float] | None,
    destination_radius_km: float,
    start_date: datetime | None,
    trip_budget: float | None,
    people_count: int,
    trajectory_prior: dict[str, int] | None = None,
    crowd_index: float | None = None,
) -> list[Any]:
    visit_dt = visit_datetime(start_date, 0) if start_date else None
    ranked: list[tuple[float, Any]] = []
    prior = trajectory_prior or {}
    for poi in pois:
        if not is_usable_poi(poi):
            continue
        distance_penalty = 0.0
        if destination_center is not None:
            distance = haversine_km(float(poi.lat), float(poi.lng), destination_center[0], destination_center[1])
            if distance > destination_radius_km:
                continue
            distance_penalty = min(1.2, distance / max(destination_radius_km, 1.0))
        score = (
            poi_relevance_score(poi, preferred_activities, visit_dt, trip_budget, people_count)
            - distance_penalty
            + min(0.7, prior.get(str(getattr(poi, "id", "")), 0) * 0.18)
        )
        if (
            crowd_index is not None
            and crowd_index >= _CROWD_INDEX_HIGH_THRESHOLD
            and float(getattr(poi, "popularity_score", 0) or 0) < _LOW_POPULARITY_IN_CROWDED_DESTINATION
        ):
            score -= _CROWDED_DESTINATION_LOW_POI_PENALTY
        if score < _POI_MIN_SCORE:
            continue
        ranked.append((score, poi))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [poi for _score, poi in ranked]


def _fallback_templates_from_poi(
    *,
    supplemental_pois: list[Any],
    duration_days: int,
    preferred_activities: list[str],
    pace: str,
    rest_days_count: int,
) -> list[Any]:
    active_days = [
        day for day in range(1, duration_days + 1) if day not in rest_day_numbers(duration_days, rest_days_count)
    ]
    if not active_days:
        active_days = list(range(1, duration_days + 1))
    max_per_day = {"relaxed": 3, "standard": 4, "intense": 5}.get(pace, 4)
    required = len(active_days) * max_per_day
    pool = supplemental_pois[: max(required * 2, required + 12)]
    if len(pool) < max(1, len(active_days) * 2):
        return []

    sequences = []
    offset = 0
    for day_number in active_days:
        day_pois = pool[offset : offset + max_per_day]
        offset += max_per_day
        sequences.append(
            {
                "day": day_number,
                "theme": _theme_for_pois(day_pois, preferred_activities),
                "poi_ids": [str(poi.id) for poi in day_pois],
            }
        )
    return [
        SimpleNamespace(
            duration_days=duration_days,
            activity_tags=preferred_activities or sorted({_category_for(poi) for poi in pool[:required]})[:5],
            sequence_of_poi=sequences,
        )
    ]


def _category_for(poi: Any) -> str:
    return str(getattr(poi, "category", "") or "urban").lower()


def _theme_for_pois(pois: list[Any], preferred_activities: list[str]) -> str:
    categories = [_category_for(poi) for poi in pois]
    for preference in preferred_activities:
        if str(preference).lower() in categories:
            return str(preference).lower()
    return max(set(categories), key=categories.count) if categories else "urban"


def template_day_payload(template: Any, active_day_idx: int) -> dict:
    if active_day_idx < len(template.sequence_of_poi):
        return template.sequence_of_poi[active_day_idx]
    if template.sequence_of_poi:
        return template.sequence_of_poi[active_day_idx % len(template.sequence_of_poi)]
    return {"day": active_day_idx + 1, "theme": "free", "poi_ids": []}


def build_personalized_variant(
    *,
    candidate_pois: list[Any],
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
    destination_popularity: Any | None,
    trajectories_available: bool,
    trajectory_prior: dict[str, int],
) -> dict | None:
    rng = random.Random(variant_seed)
    max_per_day = {"relaxed": 3, "standard": 4, "intense": 5}.get(pace, 4)
    min_per_day = max(2, max_per_day - 1)
    rest_days = rest_day_numbers(duration_days, rest_days_count)
    active_day_numbers = [day for day in range(1, duration_days + 1) if day not in rest_days]
    if not active_day_numbers:
        active_day_numbers = list(range(1, duration_days + 1))
    required_min_poi = len(active_day_numbers) * min_per_day
    if len(candidate_pois) < required_min_poi:
        return None

    candidates = _variant_candidate_order(candidate_pois, rng=rng, variant_index=variant_index)
    used_poi_ids: set[str] = set()
    days = []
    total_score = 0.0
    total_travel = 0
    opening_warnings = 0

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

        day_items, day_score, day_travel, day_opening_warnings = schedule_day(
            candidates=candidates,
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
        if len(day_items) < min_per_day:
            return None
        total_score += day_score
        total_travel += day_travel
        opening_warnings += day_opening_warnings
        days.append(
            {
                "day": day_number,
                "day_number": day_number,
                "theme": _theme_for_items(day_items, preferred_activities),
                "start_time": day_start_time.isoformat(timespec="minutes"),
                "end_time": day_end_time.isoformat(timespec="minutes"),
                "places": day_items,
                "items": day_items,
                "total_score": round(day_score, 4),
            }
        )

    optimization = _optimize_variant_days(
        days=days,
        start_date=start_date,
        day_start_time=day_start_time,
        day_end_time=day_end_time,
        preferred_activities=preferred_activities,
        trip_budget=trip_budget,
        people_count=people_count,
        min_per_day=min_per_day,
    )
    days = optimization["days"]
    signature = route_signature(days)
    total_poi = sum(len(day["items"]) for day in days)
    total_score = float(optimization["total_score"])
    total_travel = int(optimization["travel_overhead_minutes"])
    opening_warnings = int(optimization["opening_hours_warnings"])
    return {
        "destination_id": destination_id,
        "duration_days": duration_days,
        "variant_index": variant_index,
        "variant_seed": variant_seed,
        "route_signature": signature,
        "model_version": "orienteering-heuristic-v2",
        "days": days,
        "activity_tags": preferred_activities or _top_route_categories(days),
        "source": "personalized-orienteering-heuristic",
        "has_template": True,
        "score_summary": {
            "algorithm": "greedy_team_orienteering_with_time_windows_v3",
            "mathematical_model": "maximize weighted POI utility subject to day time windows, rest days, deduplication, route-distance penalties, budget and opening-hour constraints",
            "optimizer": optimization["optimizer"],
            "objective_weights": {
                "preference_match": 1.4,
                "poi_popularity_quality": 1.9,
                "category_prior": 1.1,
                "trajectory_prior": 0.18,
                "route_distance_penalty": (
                    f"min({_ROUTE_DISTANCE_PENALTY_CAP}, distance_km / {_ROUTE_DISTANCE_PENALTY_DIVISOR_KM:g})"
                ),
                "local_search_travel_penalty_per_minute": _ROUTE_TRAVEL_MINUTE_PENALTY,
                "local_search_category_repeat_penalty": _ROUTE_CATEGORY_REPEAT_PENALTY,
                "destination_crowd_penalty": 0.25,
            },
            "total_pois": total_poi,
            "total_score": round(total_score, 4),
            "travel_overhead_minutes": total_travel,
            "opening_hours_warnings": opening_warnings,
            "opening_hours_violations": opening_warnings,
            "rest_days_count": len(rest_days),
            "avg_relevance": round(total_score / max(total_poi, 1), 4),
            "route_optimization": {
                "same_day_reorders": optimization["same_day_reorders"],
                "cross_day_swaps": optimization["cross_day_swaps"],
                "travel_before_minutes": optimization["travel_before_minutes"],
                "travel_after_minutes": optimization["travel_overhead_minutes"],
                "objective_before": optimization["objective_before"],
                "objective_after": optimization["objective_after"],
            },
            "candidate_pool_size": len(candidate_pois),
            "trajectories_available": trajectories_available,
            "trajectory_prior_poi_count": len(trajectory_prior),
            "destination_crowd_index": float(destination_popularity.crowd_index) if destination_popularity else None,
            "destination_popularity_source": "destination_popularity" if destination_popularity else "not_available",
            "fallback_reason": None,
        },
    }


def _variant_candidate_order(candidate_pois: list[Any], *, rng: random.Random, variant_index: int) -> list[Any]:
    if variant_index <= 0:
        return list(candidate_pois)
    window = min(len(candidate_pois), max(12, variant_index * 8))
    head = list(candidate_pois[:window])
    tail = list(candidate_pois[window:])
    rng.shuffle(head)
    return sorted(head, key=lambda poi: round(float(getattr(poi, "popularity_score", 0) or 0), 1), reverse=True) + tail


def _theme_for_items(items: list[dict], preferred_activities: list[str]) -> str:
    categories = [str(item.get("category") or "urban").lower() for item in items]
    for preference in preferred_activities:
        if str(preference).lower() in categories:
            return str(preference).lower()
    return max(set(categories), key=categories.count) if categories else "urban"


def _top_route_categories(days: list[dict]) -> list[str]:
    counts: dict[str, int] = {}
    for day in days:
        for item in day.get("items", []):
            category = str(item.get("category") or "urban").lower()
            counts[category] = counts.get(category, 0) + 1
    return [category for category, _count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:5]]


def _optimize_variant_days(
    *,
    days: list[dict],
    start_date: date | datetime | None,
    day_start_time: time,
    day_end_time: time,
    preferred_activities: list[str],
    trip_budget: float | None,
    people_count: int,
    min_per_day: int,
) -> dict[str, Any]:
    optimized_days = [_copy_day(day) for day in days]
    before = _route_metrics(optimized_days)
    same_day_reorders = 0
    cross_day_swaps = 0

    for day_index, day in enumerate(optimized_days):
        if _is_rest_day(day):
            continue
        current_items = list(day.get("items", []))
        best = _best_day_schedule(
            current_items,
            start_date=start_date,
            day_idx=day_index,
            day_start_time=day_start_time,
            day_end_time=day_end_time,
            preferred_activities=preferred_activities,
            trip_budget=trip_budget,
            people_count=people_count,
            min_per_day=min_per_day,
        )
        if best is None:
            continue
        current_objective = _day_objective(current_items)
        best_objective = _day_objective(best["items"])
        if best_objective > current_objective + 1e-6:
            _replace_day_items(day, best)
            same_day_reorders += 1

    swap_attempts = 0
    improved = True
    while improved and swap_attempts < _MAX_CROSS_DAY_SWAP_ATTEMPTS:
        improved = False
        active_indices = [
            index
            for index, day in enumerate(optimized_days)
            if not _is_rest_day(day) and len(day.get("items", [])) >= min_per_day
        ]
        for left_pos, left_index in enumerate(active_indices):
            if swap_attempts >= _MAX_CROSS_DAY_SWAP_ATTEMPTS:
                break
            for right_index in active_indices[left_pos + 1 :]:
                if swap_attempts >= _MAX_CROSS_DAY_SWAP_ATTEMPTS:
                    break
                accepted = _try_improve_by_cross_day_swap(
                    optimized_days=optimized_days,
                    left_index=left_index,
                    right_index=right_index,
                    start_date=start_date,
                    day_start_time=day_start_time,
                    day_end_time=day_end_time,
                    preferred_activities=preferred_activities,
                    trip_budget=trip_budget,
                    people_count=people_count,
                    min_per_day=min_per_day,
                )
                swap_attempts += 1
                if accepted:
                    cross_day_swaps += 1
                    improved = True
                    break
            if improved:
                break

    after = _route_metrics(optimized_days)
    _strip_optimizer_fields(optimized_days)
    return {
        "days": optimized_days,
        "optimizer": "bounded_local_search_v1",
        "same_day_reorders": same_day_reorders,
        "cross_day_swaps": cross_day_swaps,
        "travel_before_minutes": before["travel_overhead_minutes"],
        "travel_overhead_minutes": after["travel_overhead_minutes"],
        "opening_hours_warnings": after["opening_hours_warnings"],
        "total_score": after["total_score"],
        "objective_before": round(before["objective"], 4),
        "objective_after": round(after["objective"], 4),
    }


def _try_improve_by_cross_day_swap(
    *,
    optimized_days: list[dict],
    left_index: int,
    right_index: int,
    start_date: date | datetime | None,
    day_start_time: time,
    day_end_time: time,
    preferred_activities: list[str],
    trip_budget: float | None,
    people_count: int,
    min_per_day: int,
) -> bool:
    left_day = optimized_days[left_index]
    right_day = optimized_days[right_index]
    left_items = list(left_day.get("items", []))
    right_items = list(right_day.get("items", []))
    current_objective = _day_objective(left_items) + _day_objective(right_items)

    best_pair: tuple[float, dict[str, Any], dict[str, Any]] | None = None
    for left_item_index, left_item in enumerate(left_items):
        for right_item_index, right_item in enumerate(right_items):
            candidate_left = list(left_items)
            candidate_right = list(right_items)
            candidate_left[left_item_index] = right_item
            candidate_right[right_item_index] = left_item
            left_schedule = _best_day_schedule(
                candidate_left,
                start_date=start_date,
                day_idx=left_index,
                day_start_time=day_start_time,
                day_end_time=day_end_time,
                preferred_activities=preferred_activities,
                trip_budget=trip_budget,
                people_count=people_count,
                min_per_day=min_per_day,
            )
            if left_schedule is None:
                continue
            right_schedule = _best_day_schedule(
                candidate_right,
                start_date=start_date,
                day_idx=right_index,
                day_start_time=day_start_time,
                day_end_time=day_end_time,
                preferred_activities=preferred_activities,
                trip_budget=trip_budget,
                people_count=people_count,
                min_per_day=min_per_day,
            )
            if right_schedule is None:
                continue
            objective = _day_objective(left_schedule["items"]) + _day_objective(right_schedule["items"])
            if objective <= current_objective + 1e-6:
                continue
            if best_pair is None or objective > best_pair[0]:
                best_pair = (objective, left_schedule, right_schedule)

    if best_pair is None:
        return False
    _replace_day_items(left_day, best_pair[1])
    _replace_day_items(right_day, best_pair[2])
    return True


def _best_day_schedule(
    items: list[dict],
    *,
    start_date: date | datetime | None,
    day_idx: int,
    day_start_time: time,
    day_end_time: time,
    preferred_activities: list[str],
    trip_budget: float | None,
    people_count: int,
    min_per_day: int,
) -> dict[str, Any] | None:
    if len(items) < min_per_day:
        return None
    best: dict[str, Any] | None = None
    # Pace keeps day cardinality at <= 5; permutations are exact for the selected day POI set.
    for ordered_items in itertools.permutations(items):
        candidate = _reschedule_day_items(
            list(ordered_items),
            start_date=start_date,
            day_idx=day_idx,
            day_start_time=day_start_time,
            day_end_time=day_end_time,
            preferred_activities=preferred_activities,
            trip_budget=trip_budget,
            people_count=people_count,
        )
        if candidate is None:
            continue
        if best is None or _day_objective(candidate["items"]) > _day_objective(best["items"]):
            best = candidate
    return best


def _reschedule_day_items(
    items: list[dict],
    *,
    start_date: date | datetime | None,
    day_idx: int,
    day_start_time: time,
    day_end_time: time,
    preferred_activities: list[str],
    trip_budget: float | None,
    people_count: int,
) -> dict[str, Any] | None:
    current_dt = visit_datetime_at(start_date, day_idx, day_start_time)
    end_dt = visit_datetime_at(start_date, day_idx, day_end_time)
    previous: dict | None = None
    scheduled: list[dict] = []
    total_score = 0.0
    total_travel = 0
    opening_warnings = 0

    for raw_item in items:
        item = dict(raw_item)
        item.setdefault("_base_score", float(item.get("score") or 0.0))
        travel_minutes = _estimate_payload_travel_minutes(previous, item) if previous else 0
        arrival_dt = current_dt + timedelta(minutes=travel_minutes)
        duration = int(
            item.get("visit_duration_minutes")
            or item.get("duration_minutes")
            or default_duration(item.get("category", ""))
        )
        departure_dt = arrival_dt + timedelta(minutes=duration)
        if departure_dt > end_dt:
            return None
        opening_status = _payload_opening_status(item, arrival_dt)
        if opening_status == "closed":
            opening_warnings += 1
            return None
        score = _payload_relevance_score(item, preferred_activities, trip_budget, people_count)
        item.update(
            {
                "arrival_time": arrival_dt.time().isoformat(timespec="minutes"),
                "departure_time": departure_dt.time().isoformat(timespec="minutes"),
                "travel_from_previous_minutes": travel_minutes,
                "opening_status": opening_status,
                "is_open_at_midday": _payload_opening_status(item, visit_datetime(start_date, day_idx)) == "open",
                "score": round(score, 4),
            }
        )
        scheduled.append(item)
        total_score += score
        total_travel += travel_minutes
        current_dt = departure_dt + timedelta(minutes=_DWELL_BUFFER_MINUTES)
        previous = item

    return {
        "items": scheduled,
        "total_score": round(total_score, 4),
        "travel_overhead_minutes": total_travel,
        "opening_hours_warnings": opening_warnings,
    }


def _payload_relevance_score(
    item: dict,
    preferred_activities: list[str],
    trip_budget: float | None,
    people_count: int,
) -> float:
    del preferred_activities, trip_budget, people_count
    return float(item.get("_base_score", item.get("score") or 0.0))


def _payload_opening_status(item: dict, visit_dt: datetime) -> str:
    opening_hours = item.get("opening_hours")
    if not opening_hours:
        return "unknown"
    return "open" if OpeningHoursParser.is_open(opening_hours, visit_dt) else "closed"


def _estimate_payload_travel_minutes(previous: dict | None, current: dict) -> int:
    if previous is None:
        return 0
    if (
        previous.get("lat") is None
        or previous.get("lng") is None
        or current.get("lat") is None
        or current.get("lng") is None
    ):
        return max(0, int(current.get("travel_from_previous_minutes") or 20))
    distance = haversine_km(
        float(previous["lat"]), float(previous["lng"]), float(current["lat"]), float(current["lng"])
    )
    return max(
        _MIN_TRAVEL_MINUTES,
        min(_MAX_TRAVEL_MINUTES, int(distance / _ASSUMED_ROUTE_SPEED_KMH * 60) + _TRAVEL_TIME_FIXED_BUFFER_MINUTES),
    )


def _day_objective(items: list[dict]) -> float:
    score = sum(float(item.get("score") or 0.0) for item in items)
    travel = sum(max(0, int(item.get("travel_from_previous_minutes") or 0)) for item in items)
    repeated_categories = max(0, len(items) - len({str(item.get("category") or "") for item in items}))
    return score - travel * _ROUTE_TRAVEL_MINUTE_PENALTY - repeated_categories * _ROUTE_CATEGORY_REPEAT_PENALTY


def _route_metrics(days: list[dict]) -> dict[str, float | int]:
    total_score = 0.0
    travel_overhead = 0
    opening_warnings = 0
    objective = 0.0
    for day in days:
        items = list(day.get("items", []))
        total_score += sum(float(item.get("score") or 0.0) for item in items)
        travel_overhead += sum(max(0, int(item.get("travel_from_previous_minutes") or 0)) for item in items)
        opening_warnings += sum(1 for item in items if item.get("opening_status") == "closed")
        objective += _day_objective(items)
    return {
        "total_score": round(total_score, 4),
        "travel_overhead_minutes": travel_overhead,
        "opening_hours_warnings": opening_warnings,
        "objective": round(objective, 4),
    }


def _copy_day(day: dict) -> dict:
    copied = dict(day)
    copied["items"] = [dict(item) for item in day.get("items", day.get("places", []))]
    copied["places"] = copied["items"]
    return copied


def _replace_day_items(day: dict, schedule: dict[str, Any]) -> None:
    day["items"] = schedule["items"]
    day["places"] = schedule["items"]
    day["total_score"] = schedule["total_score"]


def _is_rest_day(day: dict) -> bool:
    return str(day.get("theme") or "").lower() == "rest"


def _strip_optimizer_fields(days: list[dict]) -> None:
    for day in days:
        for item in day.get("items", []):
            item.pop("_base_score", None)


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
    supplemental_pois: list[Any] | None = None,
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
        candidates = _with_supplemental_candidates(
            candidates,
            supplemental_pois or [],
            used_poi_ids=used_poi_ids,
            target_count=max_per_day,
        )
        scored_candidates = [
            (
                poi_relevance_score(
                    poi,
                    preferred_activities,
                    visit_datetime_at(start_date, day_idx, day_start_time),
                    trip_budget,
                    people_count,
                ),
                rng.random(),
                poi,
            )
            for poi in candidates
        ]
        scored_candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        candidate_pool = _seeded_candidate_pool(scored_candidates, max_per_day=max_per_day, rng=rng)
        day_items, day_score, day_travel, day_opening_warnings = schedule_day(
            candidates=candidate_pool,
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


def _seeded_candidate_pool(scored_candidates: list[tuple[float, float, Any]], *, max_per_day: int, rng) -> list[Any]:
    if not scored_candidates:
        return []
    pool_size = min(len(scored_candidates), max(max_per_day + 2, max_per_day * 2))
    top = scored_candidates[:pool_size]
    best_score = top[0][0]
    flexible = [item for item in top if best_score - item[0] <= 1.25]
    lower_quality = [item for item in top if best_score - item[0] > 1.25]
    rng.shuffle(flexible)
    ordered = sorted(flexible, key=lambda item: (round(item[0] * 2) / 2, item[1]), reverse=True) + lower_quality
    return [item[2] for item in ordered]


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
    remaining = list(candidates)
    used_categories: set[str] = set()
    while remaining and len(result) < max_per_day:
        poi = _select_next_day_poi(
            remaining=remaining,
            previous=prev,
            arrival_base=current_dt,
            preferred_activities=preferred_activities,
            trip_budget=trip_budget,
            people_count=people_count,
            used_categories=used_categories,
        )
        remaining.remove(poi)
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
        used_categories.add(_category_for(poi))
        total_score += score
        total_travel += travel_minutes
        current_dt = departure_dt + timedelta(minutes=_DWELL_BUFFER_MINUTES)
        prev = poi
    return result, total_score, total_travel, opening_warnings


def _select_next_day_poi(
    *,
    remaining: list[Any],
    previous: Any | None,
    arrival_base: datetime,
    preferred_activities: list[str],
    trip_budget: float | None,
    people_count: int,
    used_categories: set[str],
) -> Any:
    best: tuple[float, Any] | None = None
    for poi in remaining:
        travel_minutes = estimate_travel_minutes(previous, poi) if previous else 0
        score = poi_relevance_score(
            poi,
            preferred_activities,
            arrival_base + timedelta(minutes=travel_minutes),
            trip_budget,
            people_count,
        )
        if previous is not None:
            distance = haversine_km(float(previous.lat), float(previous.lng), float(poi.lat), float(poi.lng))
            score -= min(_ROUTE_DISTANCE_PENALTY_CAP, distance / _ROUTE_DISTANCE_PENALTY_DIVISOR_KM)
        category = _category_for(poi)
        if category in used_categories:
            score -= _SAME_DAY_CATEGORY_REPEAT_PENALTY
        elif used_categories:
            score += _SAME_DAY_CATEGORY_DIVERSITY_BONUS
        if best is None or score > best[0]:
            best = (score, poi)
    return best[1] if best is not None else remaining[0]


def _with_supplemental_candidates(
    candidates: list[Any],
    supplemental_pois: list[Any],
    *,
    used_poi_ids: set[str],
    target_count: int,
) -> list[Any]:
    if len(candidates) >= target_count:
        return candidates
    result = list(candidates)
    seen = {str(poi.id) for poi in result}
    for poi in supplemental_pois:
        key = str(getattr(poi, "id", ""))
        if not key or key in seen or key in used_poi_ids or not is_usable_poi(poi):
            continue
        result.append(poi)
        seen.add(key)
        if len(result) >= max(target_count * 3, target_count + 6):
            break
    return result


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
    return max(
        _MIN_TRAVEL_MINUTES,
        min(_MAX_TRAVEL_MINUTES, int(distance / _ASSUMED_ROUTE_SPEED_KMH * 60) + _TRAVEL_TIME_FIXED_BUFFER_MINUTES),
    )


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
