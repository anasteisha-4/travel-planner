import uuid

from app.schemas.llm_quality import LLMReviewStatus
from app.services.llm.providers import FakeProvider
from app.services.llm.quality_gate import LLMQualityGate


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
