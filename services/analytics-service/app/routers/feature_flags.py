from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_admin_user_id, get_optional_user_id
from app.exceptions import AppException
from app.models.feature_flag import FeatureFlag
from app.schemas.feature_flags import EvaluatedFlagsResponse, FeatureFlagResponse, FeatureFlagUpdate
from app.services.feature_flags import list_evaluated_flags, write_audit_log

router = APIRouter(prefix="/api/v1/flags", tags=["feature-flags"])
admin_router = APIRouter(prefix="/api/v1/admin/feature-flags", tags=["admin-feature-flags"])


@router.get("", response_model=EvaluatedFlagsResponse)
def get_flags(
    user_id=Depends(get_optional_user_id),
    x_anonymous_id: str | None = Header(default=None, alias="X-Anonymous-ID"),
    x_platform: str | None = Header(default="web", alias="X-Platform"),
    db: Session = Depends(get_db),
) -> EvaluatedFlagsResponse:
    return EvaluatedFlagsResponse(
        flags=list_evaluated_flags(db, user_id=user_id, anonymous_id=x_anonymous_id, platform=x_platform)
    )


@admin_router.get("", response_model=list[FeatureFlagResponse])
def list_flags(
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
) -> list[FeatureFlagResponse]:
    return list(db.query(FeatureFlag).order_by(FeatureFlag.key.asc()).all())


@admin_router.patch("/{flag_key}", response_model=FeatureFlagResponse)
def update_flag(
    flag_key: str,
    data: FeatureFlagUpdate,
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
) -> FeatureFlagResponse:
    flag = db.query(FeatureFlag).filter(FeatureFlag.key == flag_key).one_or_none()
    if flag is None:
        raise AppException(status_code=404, code="FEATURE_FLAG_NOT_FOUND", message="Feature flag not found")

    before = {
        "enabled": flag.enabled,
        "rollout_percentage": flag.rollout_percentage,
        "environment": flag.environment,
        "targeting_json": flag.targeting_json,
        "payload_json": flag.payload_json,
    }
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(flag, field, value)
    write_audit_log(
        db,
        actor_user_id=user_id,
        action="feature_flag_updated",
        entity_type="feature_flag",
        entity_id=flag.key,
        context={"before": before, "after": data.model_dump(exclude_unset=True)},
    )
    db.commit()
    db.refresh(flag)
    return flag
