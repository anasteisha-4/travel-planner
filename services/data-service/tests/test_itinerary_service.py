from datetime import datetime
from types import SimpleNamespace

from app.services.itinerary_service import dedupe_poi_ids, select_best_template


def _trajectory(duration_days: int, tags: list[str], poi_ids: list[str]) -> SimpleNamespace:
    return SimpleNamespace(
        duration_days=duration_days,
        activity_tags=tags,
        sequence_of_poi=[{"day": 1, "poi_ids": poi_ids}],
    )


def _poi(
    poi_id: str,
    *,
    name: str = "Museum",
    lat: float | None = 55.75,
    lng: float | None = 37.62,
    visit_duration_minutes: int | None = 120,
    popularity_score: float | None = 0.8,
    opening_hours: str | None = "Mo-Su 10:00-18:00",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=poi_id,
        name=name,
        lat=lat,
        lng=lng,
        visit_duration_minutes=visit_duration_minutes,
        popularity_score=popularity_score,
        opening_hours=opening_hours,
    )


def test_dedupe_poi_ids_skips_existing_and_day_duplicates():
    assert dedupe_poi_ids(["a", "b", "a", "c"], {"b"}) == ["a", "c"]


def test_select_best_template_prefers_activity_match_with_available_poi():
    weak = _trajectory(3, ["shopping"], ["missing"])
    strong = _trajectory(3, ["culture", "food"], ["poi-1", "poi-2"])
    poi_map = {"poi-1": _poi("poi-1"), "poi-2": _poi("poi-2")}

    selected = select_best_template(
        trajectories=[weak, strong],
        duration_days=3,
        preferred_activities=["culture"],
        poi_map=poi_map,
        start_date=datetime(2026, 6, 10),
    )

    assert selected is strong


def test_select_best_template_penalizes_unusable_poi():
    unusable = _trajectory(3, ["culture"], ["poi-1"])
    usable = _trajectory(3, ["culture"], ["poi-2"])
    poi_map = {
        "poi-1": _poi("poi-1", name="", lat=None),
        "poi-2": _poi("poi-2", name="Gallery"),
    }

    selected = select_best_template(
        trajectories=[unusable, usable],
        duration_days=3,
        preferred_activities=["culture"],
        poi_map=poi_map,
    )

    assert selected is usable
