from uuid import UUID

import redis
from fastapi import Header, HTTPException
from jose import JWTError, jwt

from app.config import settings


def get_redis():
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def is_token_blacklisted(jti: str) -> bool:
    try:
        r = get_redis()
        return r.exists(f"blacklisted_token:{jti}") > 0
    except redis.ConnectionError:
        return False


def get_current_user_id(authorization: str | None = Header(None)) -> UUID:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.replace("Bearer ", "")

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    jti = payload.get("jti")
    if jti and is_token_blacklisted(jti):
        raise HTTPException(status_code=401, detail="Token has been revoked")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    return UUID(user_id)
