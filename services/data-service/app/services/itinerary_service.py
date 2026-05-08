"""Itinerary generation using pre-built trajectory templates."""

from datetime import datetime, timedelta
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
    template = select_best_template(
        trajectories=trajectories,
        duration_days=duration_days,
        preferred_activities=preferred_activities,
        poi_map=poi_map,
        start_date=start_date,
    )
    if not template:
        return {
            "error": "No itinerary template available for this destination.",
            "destination_id": destination_id,
        }

    poi_translations = load_translations(db, NameTranslationEntity.poi, [p.id for p in poi_map.values()])
    days = []
    used_poi_ids: set[str] = set()
    for day_idx, day_data in enumerate(template.sequence_of_poi[:duration_days]):
        day_poi = []
        for poi_id in dedupe_poi_ids(day_data.get("poi_ids", []), used_poi_ids):
            poi = poi_map.get(str(poi_id))
            if poi and is_usable_poi(poi):
                used_poi_ids.add(str(poi_id))
                day_poi.append(
                    itinerary_place_payload(
                        poi=poi,
                        translations=poi_translations,
                        visit_dt=visit_datetime(start_date, day_idx),
                    )
                )
        days.append(
            {
                "day": day_data["day"],
                "theme": day_data.get("theme", "urban"),
                "places": day_poi,
            }
        )

    return {
        "destination_id": destination_id,
        "duration_days": duration_days,
        "days": days,
        "activity_tags": template.activity_tags,
    }


def visit_datetime(start_date: datetime | None, day_idx: int) -> datetime:
    visit_dt = (start_date + timedelta(days=day_idx)) if start_date else datetime.now()
    return visit_dt.replace(hour=12, minute=0, second=0)


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
    return max(
        trajectories,
        key=lambda trajectory: template_score(
            trajectory=trajectory,
            duration_days=duration_days,
            preferred_activities=preferred_activities,
            poi_map=poi_map,
            start_date=start_date,
        ),
    )


def itinerary_place_payload(poi: Any, translations: dict, visit_dt: datetime) -> dict:
    return {
        "id": str(poi.id),
        "category": poi.category,
        "lat": poi.lat,
        "lng": poi.lng,
        "popularity_score": poi.popularity_score,
        "address": poi.address,
        "opening_hours": poi.opening_hours,
        "is_open_at_midday": OpeningHoursParser.is_open(poi.opening_hours, visit_dt),
        "visit_duration_minutes": poi.visit_duration_minutes,
        **poi_display_payload(str(poi.id), poi.name, translations),
    }
