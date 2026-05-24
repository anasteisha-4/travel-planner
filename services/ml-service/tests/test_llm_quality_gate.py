import uuid

from app.schemas.llm_quality import LLMReviewStatus
from app.services.llm.providers import FakeProvider
from app.services.llm.quality_gate import LLMQualityGate, _normalize_review_payload


class _FakeDb:
    def add(self, _value):
        return None

    def commit(self):
        return None

    def rollback(self):
        return None

    def refresh(self, _value):
        return None


def test_llm_quality_gate_fail_open_on_invalid_json(monkeypatch):
    monkeypatch.setattr("app.services.llm.quality_gate.settings.LLM_FAIL_OPEN", True)
    gate = LLMQualityGate(provider=FakeProvider(responses=["not json", "still not json"]))

    review = gate.review_recommendations(
        db=_FakeDb(),
        user_id=uuid.uuid4(),
        recommendation_id=uuid.uuid4(),
        context={"recommendations": []},
    )

    assert review.status == LLMReviewStatus.skipped
    assert "invalid_json_or_schema" in (review.defense_trace or "")


def test_llm_quality_gate_fail_open_on_unexpected_provider_error(monkeypatch):
    monkeypatch.setattr("app.services.llm.quality_gate.settings.LLM_FAIL_OPEN", True)
    gate = LLMQualityGate(provider=FakeProvider(error=TypeError("provider returned malformed response")))

    review = gate.review_recommendations(
        db=_FakeDb(),
        user_id=uuid.uuid4(),
        recommendation_id=uuid.uuid4(),
        context={"recommendations": []},
    )

    assert review.status == LLMReviewStatus.skipped
    assert "TypeError" in (review.defense_trace or "")


def test_normalize_review_payload_drops_invalid_optional_uuid_ids():
    payload = _normalize_review_payload(
        {
            "status": "caution",
            "confidence": 0.8,
            "suggested_adjustments": [
                {
                    "action": "replace_item",
                    "reason": "Use a real candidate instead of a placeholder.",
                    "target_id": "not-a-uuid",
                    "replacement_id": "cambrils_old_town_placeholder",
                }
            ],
        }
    )

    adjustment = payload["suggested_adjustments"][0]
    assert adjustment["target_id"] is None
    assert adjustment["replacement_id"] is None
