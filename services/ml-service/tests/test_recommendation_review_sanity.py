import uuid

from app.routers.recommendations import _enforce_recommendation_review_sanity
from app.schemas.llm_quality import (
    LLMQualityReview,
    LLMReviewAction,
    LLMReviewAdjustment,
    LLMReviewIssue,
    LLMReviewSeverity,
    LLMReviewStatus,
)
from app.schemas.recommendation import RecommendRequest, ScoredDestination


def test_sanity_drops_llm_budget_issue_when_trip_total_fits_budget():
    destination_id = uuid.uuid4()
    review = LLMQualityReview(
        status=LLMReviewStatus.reject,
        provider="yandex",
        model="qwen",
        prompt_version="recommendation_quality_v3",
        issues=[
            LLMReviewIssue(
                code="budget_critical",
                severity=LLMReviewSeverity.critical,
                message="Singapore exceeds budget.",
                destination_id=destination_id,
            )
        ],
        suggested_adjustments=[
            LLMReviewAdjustment(
                action=LLMReviewAction.remove,
                reason="Exceeds budget",
                target_destination_id=destination_id,
            )
        ],
    )
    result = _enforce_recommendation_review_sanity(
        review,
        RecommendRequest(travel_month=5, region="Asia", limit=20, citizenship_code="RU"),
        {"budget_max_usd": 4114.6, "typical_duration_days": 10},
        [
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

    assert result.status == LLMReviewStatus.ok
    assert result.issues == []
    assert result.suggested_adjustments == []
