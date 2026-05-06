"""Itinerary generation using pre-built trajectory templates."""

from datetime import datetime

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

    # Find closest template by duration
    trajectories = (
        db.query(Trajectory)
        .filter(Trajectory.destination_id == destination_id)
        .order_by(func.abs(Trajectory.duration_days - duration_days))
        .limit(3)
        .all()
    )

    template = None
    if trajectories:
        if preferred_activities:

            def _activity_overlap(t: "Trajectory") -> float:
                tags = t.activity_tags or []
                return len(set(tags) & set(preferred_activities)) / max(len(preferred_activities), 1)

            # Prefer exact duration match among activity-matching templates; fall back to best overlap
            exact = [t for t in trajectories if t.duration_days == duration_days]
            candidates = exact if exact else trajectories
            template = max(candidates, key=_activity_overlap)
        else:
            # No preferences: prefer exact duration match, otherwise closest
            for t in trajectories:
                if t.duration_days == duration_days:
                    template = t
                    break
            if not template:
                template = trajectories[0]

    if not template:
        return {
            "error": "No itinerary template available for this destination.",
            "destination_id": destination_id,
        }

    # Enrich POI data
    all_poi_ids = [poi_id for day_data in template.sequence_of_poi for poi_id in day_data.get("poi_ids", [])]
    poi_map = {str(p.id): p for p in db.query(POI).filter(POI.id.in_(all_poi_ids)).all()}
    poi_translations = load_translations(db, NameTranslationEntity.poi, [p.id for p in poi_map.values()])

    days = []
    for day_idx, day_data in enumerate(template.sequence_of_poi[:duration_days]):
        day_poi = []
        for poi_id in day_data.get("poi_ids", []):
            poi = poi_map.get(str(poi_id))
            if poi:
                # Construct visit datetime for this day
                # If no start_date provided, assume today; otherwise use start_date + day_idx
                # Assume midday visit (12:00) for checking opening hours
                if start_date:
                    from datetime import timedelta

                    visit_dt = start_date + timedelta(days=day_idx)
                    visit_dt = visit_dt.replace(hour=12, minute=0, second=0)
                else:
                    visit_dt = datetime.now().replace(hour=12, minute=0, second=0)

                is_open = OpeningHoursParser.is_open(poi.opening_hours, visit_dt)

                day_poi.append(
                    {
                        "id": str(poi.id),
                        "category": poi.category,
                        "lat": poi.lat,
                        "lng": poi.lng,
                        "popularity_score": poi.popularity_score,
                        "address": poi.address,
                        "opening_hours": poi.opening_hours,
                        "is_open_at_midday": is_open,
                        "visit_duration_minutes": poi.visit_duration_minutes,
                        **poi_display_payload(str(poi.id), poi.name, poi_translations),
                    }
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
