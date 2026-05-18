import hashlib
import json

import redis

from app.config import settings
from app.deps import get_redis


def make_cache_key(*, entity_type: str, entity_id: str, model: str, prompt_version: str, context: dict) -> str:
    raw = json.dumps(context, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return f"llm:{entity_type}:{model}:{prompt_version}:{digest}"


def get_cached_review(key: str) -> dict | None:
    try:
        raw = get_redis().get(key)
    except redis.RedisError:
        return None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None


def set_cached_review(key: str, review: dict) -> None:
    try:
        get_redis().setex(
            key,
            settings.LLM_CACHE_TTL_SECONDS,
            json.dumps(review, ensure_ascii=False, sort_keys=True, default=str),
        )
    except redis.RedisError:
        return None
