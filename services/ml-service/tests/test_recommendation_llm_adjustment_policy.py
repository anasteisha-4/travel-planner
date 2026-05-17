import uuid

from app.schemas.llm_quality import LLMQualityReview, LLMReviewIssue, LLMReviewSeverity, LLMReviewStatus
from app.schemas.recommendation import ScoredDestination
from app.services.llm.quality_gate import _normalize_review_payload
from app.services.llm.recommendation_adjustment_policy import apply_recommendation_quality_review


def _destination(destination_id: uuid.UUID, name: str, score: float) -> ScoredDestination:
    return ScoredDestination(
        destination_id=destination_id,
        name=name,
        country_code="RU",
        region="Europe",
        score=score,
        score_breakdown={"ltr_score": score},
        explanation_tags=[],
        avg_daily_cost_usd=100,
        season_score=0.8,
        safety_score=0.8,
    )


def test_llm_warning_issue_demotes_destination_before_response():
    risky_id = uuid.uuid4()
    safe_id = uuid.uuid4()
    fallback_id = uuid.uuid4()
    results = [
        _destination(risky_id, "Risky destination", 0.91),
        _destination(safe_id, "Safer destination", 0.84),
    ]
    review = LLMQualityReview(
        status=LLMReviewStatus.caution,
        confidence=0.8,
        provider="fake",
        model="fake",
        prompt_version="recommendation_quality_v1",
        issues=[
            LLMReviewIssue(
                code="safety_score_low",
                severity=LLMReviewSeverity.warning,
                message="Safety score is materially lower than comparable options.",
                destination_id=risky_id,
            )
        ],
        suggested_adjustments=[],
    )

    adjusted = apply_recommendation_quality_review(
        results,
        review,
        replacement_pool=[_destination(fallback_id, "Fallback", 0.78)],
    )

    assert [item.destination_id for item in adjusted.results] == [safe_id, fallback_id]
    assert all(item.destination_id != risky_id for item in adjusted.results)
    assert adjusted.applied_adjustments == [
        {
            "action": "issue_penalty",
            "issue_code": "safety_score_low",
            "target_id": str(risky_id),
            "reason": "warning_score_penalty",
        }
    ]


def test_llm_critical_issue_replaces_destination_before_response():
    blocked_id = uuid.uuid4()
    safe_id = uuid.uuid4()
    fallback_id = uuid.uuid4()
    review = LLMQualityReview(
        status=LLMReviewStatus.reject,
        confidence=0.9,
        provider="fake",
        model="fake",
        prompt_version="recommendation_quality_v1",
        issues=[
            LLMReviewIssue(
                code="safety_critical",
                severity=LLMReviewSeverity.critical,
                message="Critical safety issue.",
                destination_id=blocked_id,
            )
        ],
    )

    adjusted = apply_recommendation_quality_review(
        [_destination(blocked_id, "Blocked", 0.92), _destination(safe_id, "Safe", 0.85)],
        review,
        replacement_pool=[_destination(fallback_id, "Fallback", 0.8)],
    )

    assert [item.destination_id for item in adjusted.results] == [safe_id, fallback_id]
    assert adjusted.applied_adjustments == [
        {
            "action": "issue_penalty",
            "issue_code": "safety_critical",
            "target_id": str(blocked_id),
            "reason": "critical_remove_or_replace",
        }
    ]


def test_llm_payload_normalization_accepts_nested_qwen_issue_shape():
    destination_id = uuid.uuid4()
    payload = {
        "status": "caution",
        "confidence": 0.82,
        "prompt_version": "recommendation_quality_v1",
        "issues": [
            {
                "destination_id": str(destination_id),
                "issue": {
                    "type": "weak_beach_fit",
                    "severity": "moderate",
                    "reason": "Cold city break is a poor fit for a beach-focused May trip.",
                },
            }
        ],
        "suggested_adjustments": [
            {
                "destination_id": str(destination_id),
                "adjustment": {
                    "type": "penalize",
                    "reason": "Demote below warmer coastal alternatives.",
                },
            }
        ],
    }

    normalized = LLMQualityReview.model_validate(_normalize_review_payload(payload))

    assert normalized.issues[0].code == "weak_beach_fit"
    assert normalized.issues[0].severity == LLMReviewSeverity.warning
    assert normalized.issues[0].message == "Cold city break is a poor fit for a beach-focused May trip."
    assert normalized.issues[0].destination_id == destination_id
    assert normalized.suggested_adjustments[0].action.value == "demote"
    assert normalized.suggested_adjustments[0].target_destination_id == destination_id
