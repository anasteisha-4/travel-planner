import hashlib
import json


def make_cache_key(*, entity_type: str, entity_id: str, model: str, prompt_version: str, context: dict) -> str:
    raw = json.dumps(context, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return f"llm:{entity_type}:{entity_id}:{model}:{prompt_version}:{digest}"


def get_cached_review(_key: str) -> dict | None:
    return None


def set_cached_review(_key: str, _review: dict) -> None:
    return None
