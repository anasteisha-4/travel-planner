import uuid

from app.schemas.recommendation import RecommendRequest, ScoredDestination
from app.services.llm.recommendation_context import build_recommendation_context


def test_recommendation_context_exposes_daily_budget_for_llm():
    destination_id = uuid.uuid4()

    context = build_recommendation_context(
        profile={
            "budget_max_usd": 4114.6,
            "typical_duration_days": 10,
        },
        request=RecommendRequest(travel_month=5, region="Asia", limit=20, citizenship_code="RU"),
        citizenship_code="RU",
        results=[
            ScoredDestination(
                destination_id=destination_id,
                name="Singapore",
                country_code="SG",
                region="Asia",
                score=0.97,
                score_breakdown={},
                explanation_tags=[],
                avg_daily_cost_usd=221.0,
                season_score=0.9,
                safety_score=0.9,
            )
        ],
    )

    assert context["user_profile"]["budget_max_per_day_usd"] == 411.46
    assert context["recommendations"][0]["estimated_trip_cost_usd"] == 2210.0
