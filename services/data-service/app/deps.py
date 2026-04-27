import secrets

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db


def get_internal_db(db: Session = Depends(get_db)) -> Session:
    return db


def verify_internal_secret(x_internal_secret: str = Header(...)) -> None:
    if not settings.INTERNAL_API_SECRET or not secrets.compare_digest(x_internal_secret, settings.INTERNAL_API_SECRET):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid internal secret")
