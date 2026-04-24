import uuid

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user_id
from app.exceptions import AppException
from app.models.user_features import UserFeatures
from app.schemas.features import UserFeaturesResponse
from app.services.feature_builder import build_user_features

router = APIRouter(prefix="/api/v1/users", tags=["features"])


@router.get("/{user_id}/features", response_model=UserFeaturesResponse)
async def get_user_features(
    user_id: uuid.UUID,
    requesting_user_id: uuid.UUID = Depends(get_current_user_id),
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> UserFeatures:
    if requesting_user_id != user_id:
        raise AppException(status_code=403, code="FORBIDDEN", message="Access denied")

    features = await build_user_features(user_id=user_id, db=db, auth_header=authorization)
    return features
