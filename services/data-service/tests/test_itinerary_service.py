import random
from datetime import datetime
from types import SimpleNamespace

from app.services.itinerary_service import (
    _seeded_candidate_pool,
    build_variant,
    dedupe_poi_ids,
    rest_day_numbers,
    select_best_template,
)


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
        category="culture",
        lat=lat,
        lng=lng,
        visit_duration_minutes=visit_duration_minutes,
        popularity_score=popularity_score,
        opening_hours=opening_hours,
    )


def test_dedupe_poi_ids_skips_existing_and_day_duplicates():
    assert dedupe_poi_ids(["a", "b", "a", "c"], {"b"}) == ["a", "c"]


def test_rest_day_numbers_are_evenly_distributed_and_exact():
    assert rest_day_numbers(7, 2) == {3, 5}
    assert rest_day_numbers(5, 0) == set()
    assert rest_day_numbers(3, 3) == {1, 2, 3}


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


def test_build_variant_returns_requested_day_count_when_template_is_shorter():
    template = _trajectory(1, ["culture"], [])

    variant = build_variant(
        template=template,
        poi_map={},
        translations={},
        destination_id="11111111-1111-1111-1111-111111111111",
        duration_days=4,
        preferred_activities=["culture"],
        start_date=datetime(2026, 6, 10),
        variant_seed=42,
        variant_index=0,
        pace="standard",
        day_start_time=datetime.strptime("09:30", "%H:%M").time(),
        day_end_time=datetime.strptime("19:00", "%H:%M").time(),
        rest_days_count=4,
        trip_budget=None,
        people_count=1,
    )

    assert variant["duration_days"] == 4
    assert [day["day_number"] for day in variant["days"]] == [1, 2, 3, 4]
    assert [day["theme"] for day in variant["days"]] == ["rest", "rest", "rest", "rest"]


def test_build_variant_rejects_empty_active_days():
    template = _trajectory(1, ["culture"], [])

    variant = build_variant(
        template=template,
        poi_map={},
        translations={},
        destination_id="11111111-1111-1111-1111-111111111111",
        duration_days=1,
        preferred_activities=["culture"],
        start_date=datetime(2026, 6, 10),
        variant_seed=42,
        variant_index=0,
        pace="standard",
        day_start_time=datetime.strptime("09:30", "%H:%M").time(),
        day_end_time=datetime.strptime("19:00", "%H:%M").time(),
        rest_days_count=0,
        trip_budget=None,
        people_count=1,
    )

    assert variant is None


def test_seeded_candidate_pool_varies_close_candidates_without_promoting_weak_items():
    candidates = [(_score, 0.0, f"poi-{index}") for index, _score in enumerate([5.0, 4.8, 4.7, 4.6, 2.0])]

    first = _seeded_candidate_pool(candidates, max_per_day=3, rng=random.Random(1))
    second = _seeded_candidate_pool(candidates, max_per_day=3, rng=random.Random(2))

    assert first != second
    assert "poi-4" not in first[:3]
    assert "poi-4" not in second[:3]
