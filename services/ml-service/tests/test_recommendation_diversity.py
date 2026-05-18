import uuid

from app.routers.recommendations import _apply_country_diversity
from app.schemas.recommendation import ScoredDestination


def _item(country_code: str, score: float) -> ScoredDestination:
    return ScoredDestination(
        destination_id=uuid.uuid4(),
        name=f"{country_code}-{score}",
        country_code=country_code,
        region="Asia",
        score=score,
        score_breakdown={},
        explanation_tags=[],
        avg_daily_cost_usd=None,
        season_score=None,
        safety_score=None,
    )


def test_apply_country_diversity_limits_repeated_countries_for_asia():
    results = [
        _item("IN", 0.99),
        _item("IN", 0.98),
        _item("IN", 0.97),
        _item("SG", 0.96),
        _item("VN", 0.95),
    ]

    diversified = _apply_country_diversity(results, region="Asia", limit=4)

    assert [item.country_code for item in diversified] == ["IN", "IN", "SG", "VN"]


def test_apply_country_diversity_fills_from_deferred_when_needed():
    results = [_item("IN", 0.99), _item("IN", 0.98), _item("IN", 0.97)]

    diversified = _apply_country_diversity(results, region="Asia", limit=3)

    assert [item.country_code for item in diversified] == ["IN", "IN", "IN"]
