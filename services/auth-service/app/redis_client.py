"""
Redis client for token management
"""

import redis

from app.config import settings

redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Get Redis client instance (singleton)."""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client


def store_refresh_token(user_id: str, jti: str, ttl_seconds: int, metadata: dict = None) -> None:
    """Store refresh token in Redis"""
    import json
    from datetime import datetime

    r = get_redis()
    key = f"refresh_token:{user_id}:{jti}"
    value = json.dumps({"created_at": datetime.utcnow().isoformat(), **(metadata or {})})
    r.setex(key, ttl_seconds, value)


def validate_refresh_token(user_id: str, jti: str) -> bool:
    """Check if refresh token exists in Redis"""
    r = get_redis()
    key = f"refresh_token:{user_id}:{jti}"
    return r.exists(key) == 1


def revoke_refresh_token(user_id: str, jti: str) -> bool:
    """Revoke (delete) a specific refresh token"""
    r = get_redis()
    key = f"refresh_token:{user_id}:{jti}"
    return r.delete(key) > 0


def revoke_all_user_tokens(user_id: str) -> int:
    """Revoke all refresh tokens for a user"""
    r = get_redis()
    pattern = f"refresh_token:{user_id}:*"
    keys = list(r.scan_iter(match=pattern))
    if keys:
        return r.delete(*keys)
    return 0


def add_to_blacklist(jti: str, ttl_seconds: int) -> None:
    """Add access token to blacklist"""
    r = get_redis()
    key = f"blacklist:{jti}"
    r.setex(key, ttl_seconds, "1")


def is_blacklisted(jti: str) -> bool:
    """Check if access token is blacklisted"""
    r = get_redis()
    key = f"blacklist:{jti}"
    return r.exists(key) == 1


def check_redis_connection() -> bool:
    """Health check for Redis connection"""
    try:
        r = get_redis()
        r.ping()
        return True
    except redis.ConnectionError:
        return False
