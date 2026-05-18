from app.services.llm.cache import get_cached_review, make_cache_key, set_cached_review


class _FakeRedis:
    def __init__(self):
        self.values = {}
        self.ttls = {}

    def get(self, key):
        return self.values.get(key)

    def setex(self, key, ttl, value):
        self.values[key] = value
        self.ttls[key] = ttl


def test_llm_cache_key_is_context_based_not_request_id():
    context = {"recommendations": [{"destination_id": "1", "score": 0.9}]}

    first = make_cache_key(
        entity_type="recommendation_set",
        entity_id="recommendation-a",
        model="qwen",
        prompt_version="recommendation_quality_v1",
        context=context,
    )
    second = make_cache_key(
        entity_type="recommendation_set",
        entity_id="recommendation-b",
        model="qwen",
        prompt_version="recommendation_quality_v1",
        context=context,
    )

    assert first == second


def test_llm_review_cache_round_trips_json(monkeypatch):
    fake_redis = _FakeRedis()
    monkeypatch.setattr("app.services.llm.cache.get_redis", lambda: fake_redis)
    monkeypatch.setattr("app.services.llm.cache.settings.LLM_CACHE_TTL_SECONDS", 123)

    review = {
        "status": "ok",
        "confidence": 0.9,
        "provider": "yandex",
        "model": "qwen",
        "prompt_version": "recommendation_quality_v1",
        "issues": [],
        "suggested_adjustments": [],
        "user_summary_ru": None,
        "defense_trace": "cached",
    }

    set_cached_review("llm:test", review)

    assert get_cached_review("llm:test") == review
    assert fake_redis.ttls["llm:test"] == 123
