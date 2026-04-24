import uuid

import pytest

from app.services.content_scorer import (
    ContentScorer,
    _activity_match_score,
    _budget_fit_score,
    _climate_match,
    _crowd_score,
    _explanation_tags,
    _language_score,
    _percentile_rank,
    _region_boost,
    _safety_score,
)

# --- Unit tests for scorer functions ---


def test_percentile_rank_empty():
    assert _percentile_rank(0.5, []) == 0.5


def test_percentile_rank_all_lower():
    assert _percentile_rank(1.0, [0.1, 0.2, 0.3]) == pytest.approx(1.0)


def test_percentile_rank_all_higher():
    assert _percentile_rank(0.0, [0.5, 0.6, 0.7]) == pytest.approx(0.0)


def test_percentile_rank_mid():
    result = _percentile_rank(0.5, [0.0, 0.25, 0.5, 0.75, 1.0])
    # 2 values < 0.5 → 2/5 = 0.4
    assert result == pytest.approx(0.4)


def test_activity_match_empty_prefs():
    score = _activity_match_score([], {"beach": 0.9}, [0.5])
    assert score == 0.5


def test_activity_match_empty_activities():
    score = _activity_match_score(["beach"], {}, [0.5])
    assert score == 0.5


def test_activity_match_perfect():
    # beach gets weight 5, score 1.0 → raw = 1.0
    score = _activity_match_score(["beach"], {"beach": 1.0}, [0.0, 0.5, 0.9])
    assert score > 0.5  # should be in upper half


def test_activity_match_no_global():
    score = _activity_match_score(["beach"], {"beach": 0.8}, [])
    assert score == pytest.approx(0.8)


def test_budget_fit_no_budget():
    # falls back to 1 - abs(cost_index - 0.5), so cost_index=0.5 → 1.0
    score = _budget_fit_score(None, None, 0.5, None, None)
    assert score == pytest.approx(1.0)


def test_budget_fit_no_budget_extreme_cost():
    # cost_index=1.0 → 1 - abs(1.0 - 0.5) = 0.5
    score = _budget_fit_score(None, None, 1.0, None, None)
    assert score == pytest.approx(0.5)


def test_budget_fit_within_range():
    # cost fits exactly in budget
    score = _budget_fit_score(500, 2000, 0.3, 100.0, "standard")  # 100*10=1000 within [500,2000]
    assert score == pytest.approx(1.0)


def test_budget_fit_too_expensive():
    # daily=500, duration=10 → 5000, budget max=1000
    score = _budget_fit_score(500, 1000, 0.8, 500.0, "standard")
    assert score < 1.0
    assert score >= 0.0


def test_budget_fit_too_cheap():
    # daily=5, duration=10 → 50, budget min=500
    score = _budget_fit_score(500, 1000, 0.1, 5.0, "standard")
    assert score < 1.0


def test_safety_score_above_threshold():
    score = _safety_score(0.8, 3)  # threshold=0.40
    assert score > 0.5  # should be 0.5 + 0.5*0.8 = 0.9


def test_safety_score_below_threshold():
    score = _safety_score(0.1, 1)  # threshold=0.70 → below
    assert score < 0.5


def test_safety_score_no_tolerance():
    score = _safety_score(0.5, None)  # default threshold=0.40
    assert score >= 0.5


def test_language_score_any():
    score = _language_score({"script_difficulty": 0.0}, ["any"])
    assert score >= 0.5


def test_language_score_ru_match():
    score = _language_score({"russian_speaking_score": 0.9, "english_speaking_score": 0.1, "script_difficulty": 0.0}, ["ru"])
    assert score >= 0.8


def test_language_score_en_match():
    score = _language_score({"russian_speaking_score": 0.1, "english_speaking_score": 0.9, "script_difficulty": 0.0}, ["en"])
    assert score >= 0.8


def test_crowd_score_prefers_quiet():
    quiet = _crowd_score(0.1, 1)
    lively = _crowd_score(0.9, 1)
    assert quiet > lively


def test_crowd_score_prefers_lively():
    quiet = _crowd_score(0.1, 5)
    lively = _crowd_score(0.9, 5)
    assert lively > quiet


def test_climate_match_any():
    score = _climate_match({}, ["any"])
    assert score == pytest.approx(0.7)


def test_climate_match_cold_snow_with_ski():
    score = _climate_match({"has_ski": True}, ["cold_snow"])
    assert score == pytest.approx(1.0)


def test_climate_match_cold_snow_without_ski():
    score = _climate_match({"has_ski": False}, ["cold_snow"])
    assert score == pytest.approx(0.0)


def test_region_boost_no_liked():
    boost = _region_boost("Europe", "Western Europe", [])
    assert boost == 0.0


def test_region_boost_same_subregion():
    boost = _region_boost("Europe", "Western Europe", [{"region": "Europe", "subregion": "Western Europe"}])
    assert boost > 0.0


def test_region_boost_capped():
    liked = [{"region": "Europe", "subregion": "Western Europe"}] * 10
    boost = _region_boost("Europe", "Western Europe", liked)
    assert boost <= 0.15


def test_explanation_tags_visa_free():
    tags = _explanation_tags({}, {}, visa_score=1.0, safety_score=0.8)
    assert "visa_free" in tags


def test_explanation_tags_easy_visa():
    tags = _explanation_tags({}, {}, visa_score=0.6, safety_score=0.5)
    assert "easy_visa" in tags


def test_explanation_tags_beach():
    tags = _explanation_tags({}, {"is_coastal": True}, visa_score=1.0, safety_score=0.5)
    assert "beach" in tags


def test_explanation_tags_safe():
    tags = _explanation_tags({}, {}, visa_score=0.2, safety_score=0.8)
    assert "safe" in tags


def test_explanation_tags_affordable():
    tags = _explanation_tags({}, {"avg_daily_cost_usd": 40}, visa_score=0.2, safety_score=0.5)
    assert "affordable" in tags


def test_explanation_tags_max_5():
    tags = _explanation_tags(
        {"season": 0.9, "activity_match": 0.9},
        {"is_coastal": True, "has_ski": True, "has_thermal": True, "avg_daily_cost_usd": 30},
        visa_score=1.0,
        safety_score=0.9,
    )
    assert len(tags) <= 5


# --- Integration: ContentScorer.score ---


def _make_dest(dest_id: uuid.UUID, name: str = "TestCity") -> dict:
    return {"id": str(dest_id), "name": name, "country_code": "XX", "region": "TestRegion", "subregion": "TestSub"}


def _make_features(dest_id: uuid.UUID, **overrides) -> tuple[uuid.UUID, dict]:
    base = {
        "visa_score": 1.0,
        "safety_score": 0.7,
        "cost_index": 0.4,
        "avg_daily_cost_usd": 80.0,
        "connectivity_score": 0.5,
        "activities": {"beach": 0.8, "culture": 0.6},
        "seasonality": {7: 0.85},
        "crowd_by_month": {7: 0.3},
        "russian_speaking_score": 0.5,
        "english_speaking_score": 0.7,
        "script_difficulty": 0.1,
        "is_coastal": True,
        "has_ski": False,
        "region": "TestRegion",
        "subregion": "TestSub",
    }
    base.update(overrides)
    return dest_id, base


def _make_profile(**overrides) -> dict:
    base = {
        "vacation_preferences_ranked": ["beach", "culture"],
        "budget_min_usd": 500.0,
        "budget_max_usd": 2000.0,
        "typical_duration": "standard",
        "risk_tolerance": 3,
        "visa_tolerance": "any_visa",
        "language_comfort": ["en"],
        "crowd_preference": 2,
        "climate_preferences": ["any"],
        "liked_destination_ids": [],
        "origin_lat": 55.75,
    }
    base.update(overrides)
    return base


def test_scorer_returns_results():
    scorer = ContentScorer()
    dest_id = uuid.uuid4()
    dests = [_make_dest(dest_id)]
    feat_id, feat = _make_features(dest_id)
    results = scorer.score(
        user_profile=_make_profile(),
        destinations=dests,
        dest_features={feat_id: feat},
        travel_month=7,
        filters={"citizenship_code": "RU", "exclude_destination_ids": [], "region": None},
    )
    assert len(results) == 1
    assert results[0].destination_id == dest_id
    assert 0.0 <= results[0].score <= 1.0


def test_scorer_excludes_filtered_dest():
    scorer = ContentScorer()
    dest_id = uuid.uuid4()
    dests = [_make_dest(dest_id)]
    feat_id, feat = _make_features(dest_id)
    results = scorer.score(
        user_profile=_make_profile(),
        destinations=dests,
        dest_features={feat_id: feat},
        travel_month=7,
        filters={"citizenship_code": "RU", "exclude_destination_ids": [dest_id], "region": None},
    )
    assert results == []


def test_scorer_hard_filters_visa():
    scorer = ContentScorer()
    dest_id = uuid.uuid4()
    dests = [_make_dest(dest_id)]
    feat_id, feat = _make_features(dest_id, visa_score=0.2)
    results = scorer.score(
        user_profile=_make_profile(visa_tolerance="visa_free_only"),
        destinations=dests,
        dest_features={feat_id: feat},
        travel_month=7,
        filters={"citizenship_code": "US", "exclude_destination_ids": [], "region": None},
    )
    assert results == []


def test_scorer_region_filter():
    scorer = ContentScorer()
    dest_id = uuid.uuid4()
    dest = {"id": str(dest_id), "name": "City", "country_code": "XX", "region": "Asia", "subregion": "SE"}
    feat_id, feat = _make_features(dest_id)
    results = scorer.score(
        user_profile=_make_profile(),
        destinations=[dest],
        dest_features={feat_id: feat},
        travel_month=7,
        filters={"citizenship_code": "RU", "exclude_destination_ids": [], "region": "Europe"},
    )
    assert results == []


def test_scorer_sorted_by_score_desc():
    scorer = ContentScorer()
    id1, id2 = uuid.uuid4(), uuid.uuid4()
    dests = [_make_dest(id1, "CityA"), _make_dest(id2, "CityB")]
    # CityB has much better season and safety
    feat = {
        id1: _make_features(id1, safety_score=0.3, seasonality={7: 0.2})[1],
        id2: _make_features(id2, safety_score=0.95, seasonality={7: 0.95})[1],
    }
    results = scorer.score(
        user_profile=_make_profile(),
        destinations=dests,
        dest_features=feat,
        travel_month=7,
        filters={"citizenship_code": "RU", "exclude_destination_ids": [], "region": None},
    )
    assert len(results) == 2
    assert results[0].score >= results[1].score


def test_scorer_breakdown_keys_present():
    scorer = ContentScorer()
    dest_id = uuid.uuid4()
    feat_id, feat = _make_features(dest_id)
    results = scorer.score(
        user_profile=_make_profile(),
        destinations=[_make_dest(dest_id)],
        dest_features={feat_id: feat},
        travel_month=7,
        filters={"citizenship_code": "RU", "exclude_destination_ids": [], "region": None},
    )
    bd = results[0].score_breakdown
    for key in ["activity_match", "budget_fit", "season", "visa", "safety", "language", "crowd", "climate"]:
        assert key in bd


def test_scorer_empty_destinations():
    scorer = ContentScorer()
    results = scorer.score(
        user_profile=_make_profile(),
        destinations=[],
        dest_features={},
        travel_month=7,
        filters={"citizenship_code": "RU", "exclude_destination_ids": [], "region": None},
    )
    assert results == []
