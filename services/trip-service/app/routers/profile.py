import asyncio
import logging
import uuid
from datetime import UTC, datetime
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.database import get_db
from app.deps import get_current_user_id
from app.services.currency_service import convert_amount, get_exchange_rates

logger = logging.getLogger(__name__)

router = APIRouter()


async def _trigger_features_rebuild(user_id: UUID) -> None:
    url = f"{settings.ANALYTICS_SERVICE_URL}/api/v1/internal/users/{user_id}/features/rebuild"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(url)
    except Exception as exc:
        logger.warning("features rebuild trigger failed for %s: %s", user_id, exc)


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


async def _sync_budget_usd(profile: models.UserProfile) -> None:
    if profile.budget_min is None and profile.budget_max is None:
        profile.budget_min_usd = None
        profile.budget_max_usd = None
        return

    currency = (profile.preferred_currency or "USD").upper()
    if currency == "USD":
        profile.budget_min_usd = profile.budget_min
        profile.budget_max_usd = profile.budget_max
        return

    rates = await get_exchange_rates("USD")
    if not rates:
        return
    if profile.budget_min is not None:
        profile.budget_min_usd = convert_amount(profile.budget_min, currency, "USD", rates)
    else:
        profile.budget_min_usd = None
    if profile.budget_max is not None:
        profile.budget_max_usd = convert_amount(profile.budget_max, currency, "USD", rates)
    else:
        profile.budget_max_usd = None


@router.get("/", response_model=schemas.UserProfileResponse)
def get_profile(
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return _get_or_create_profile(db, user_id)


@router.put("/", response_model=schemas.UserProfileResponse)
async def update_profile(
    data: schemas.UserProfileCreate,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    profile = _get_or_create_profile(db, user_id)
    for field, value in data.model_dump(exclude_unset=False).items():
        setattr(profile, field, value)
    await _sync_budget_usd(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.patch("/", response_model=schemas.UserProfileResponse)
async def patch_profile(
    data: schemas.UserProfileUpdate,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    profile = _get_or_create_profile(db, user_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    if {"budget_min", "budget_max", "preferred_currency"} & data.model_fields_set:
        await _sync_budget_usd(profile)
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

    await _sync_budget_usd(profile)

    profile.onboarding_completed = True
    profile.onboarding_completed_at = datetime.now(UTC)
    profile.onboarding_step = 6
    db.commit()
    db.refresh(profile)

    asyncio.ensure_future(_trigger_features_rebuild(user_id))

    return profile
