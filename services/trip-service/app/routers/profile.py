import uuid
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user_id
from app.services.currency_service import convert_amount, get_exchange_rates

router = APIRouter()

DURATION_DAYS_MAP = {
    "weekend": 2,
    "short": 5,
    "standard": 10,
    "long": 21,
    "extended": 45,
}


def _get_or_create_profile(db: Session, user_id: UUID) -> models.UserProfile:
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == user_id).first()
    if not profile:
        profile = models.UserProfile(
            id=uuid.uuid4(),
            user_id=user_id,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.get("/", response_model=schemas.UserProfileResponse)
def get_profile(
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return _get_or_create_profile(db, user_id)


@router.put("/", response_model=schemas.UserProfileResponse)
def update_profile(
    data: schemas.UserProfileCreate,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    profile = _get_or_create_profile(db, user_id)
    for field, value in data.model_dump(exclude_unset=False).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile


@router.patch("/", response_model=schemas.UserProfileResponse)
def patch_profile(
    data: schemas.UserProfileUpdate,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    profile = _get_or_create_profile(db, user_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/onboarding/step/{step_num}", response_model=schemas.UserProfileResponse)
def save_onboarding_step(
    *,
    step_num: int = Path(..., ge=1, le=6),
    data: schemas.OnboardingStepPayload,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    profile = _get_or_create_profile(db, user_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    profile.onboarding_step = max(profile.onboarding_step, step_num)
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/onboarding/complete", response_model=schemas.UserProfileResponse)
async def complete_onboarding(
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    profile = _get_or_create_profile(db, user_id)

    if profile.typical_duration and profile.typical_duration in DURATION_DAYS_MAP:
        profile.typical_duration_days = DURATION_DAYS_MAP[profile.typical_duration]

    if profile.budget_min is not None or profile.budget_max is not None:
        currency = (profile.preferred_currency or "USD").upper()
        if currency != "USD":
            rates = await get_exchange_rates("USD")
            if rates:
                if profile.budget_min is not None:
                    converted = convert_amount(profile.budget_min, currency, "USD", rates)
                    profile.budget_min_usd = converted
                if profile.budget_max is not None:
                    converted = convert_amount(profile.budget_max, currency, "USD", rates)
                    profile.budget_max_usd = converted
        else:
            profile.budget_min_usd = profile.budget_min
            profile.budget_max_usd = profile.budget_max

    profile.onboarding_completed = True
    profile.onboarding_completed_at = datetime.now(UTC)
    profile.onboarding_step = 6
    db.commit()
    db.refresh(profile)
    return profile
