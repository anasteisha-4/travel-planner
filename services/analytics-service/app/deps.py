from typing import cast
from uuid import UUID

import redis
from fastapi import Header
from jose import JWTError, jwt

from app.config import settings
from app.exceptions import AppException


def get_redis():
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def is_token_blacklisted(jti: str) -> bool:
    try:
        r = get_redis()
        return cast(int, r.exists(f"blacklist:{jti}")) > 0
    except redis.ConnectionError:
        return False


def get_current_user_id(authorization: str | None = Header(None)) -> UUID:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppException(status_code=401, code="UNAUTHORIZED", message="Missing or invalid authorization header")

    token = authorization.replace("Bearer ", "")

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        raise AppException(status_code=401, code="UNAUTHORIZED", message="Invalid or expired token") from e

    if payload.get("type") != "access":
        raise AppException(status_code=401, code="UNAUTHORIZED", message="Invalid token type")

    jti = payload.get("jti")
    if jti and is_token_blacklisted(jti):
        raise AppException(status_code=401, code="UNAUTHORIZED", message="Token has been revoked")

    user_id = payload.get("sub")
    if not user_id:
        raise AppException(status_code=401, code="UNAUTHORIZED", message="Invalid token payload")

    return UUID(user_id)


def get_optional_user_id(authorization: str | None = Header(None)) -> UUID | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return get_current_user_id(authorization)
    except AppException:
        return None


def get_admin_user_id(authorization: str | None = Header(None)) -> UUID:
    current_user_id = get_current_user_id(authorization)
    admin_ids = {item.strip() for item in settings.ADMIN_USER_IDS.split(",") if item.strip()}
    if str(current_user_id) not in admin_ids:
        raise AppException(status_code=403, code="ADMIN_REQUIRED", message="Admin access required")
    return current_user_id
