from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app import models, redis_client, utils
from app.database import get_db
from app.exceptions import AppException


def get_current_user(authorization: str | None = Header(None), db: Session = Depends(get_db)) -> models.User:
    """Extract and validate user from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise AppException(status_code=401, code="UNAUTHORIZED", message="Missing or invalid authorization header")

    token = authorization.replace("Bearer ", "")
    payload = utils.decode_token(token)

    if not payload:
        raise AppException(status_code=401, code="UNAUTHORIZED", message="Invalid or expired token")

    if payload.get("type") != "access":
        raise AppException(status_code=401, code="UNAUTHORIZED", message="Invalid token type")

    jti = payload.get("jti")
    if jti and redis_client.is_blacklisted(jti):
        raise AppException(status_code=401, code="UNAUTHORIZED", message="Token has been revoked")

    user_id = payload.get("sub")
    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise AppException(status_code=401, code="UNAUTHORIZED", message="User not found")

    return user
