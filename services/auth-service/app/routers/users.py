from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.exceptions import AppException

router = APIRouter()


class ProfileUpdateRequest(BaseModel):
    email: EmailStr | None = None
    login: str | None = None


def user_to_profile(user: models.User) -> schemas.UserProfile:
    return schemas.UserProfile(
        id=user.id,
        email=user.email,
        login=user.login,
        onboarding_completed=user.onboarding_completed,
    )


@router.get("/me", response_model=schemas.UserProfile)
def get_profile(current_user: models.User = Depends(get_current_user)):
    return user_to_profile(current_user)


@router.put("/me", response_model=schemas.UserProfile)
def update_profile(
    request: ProfileUpdateRequest, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    if not user:
        raise AppException(status_code=404, code="NOT_FOUND", message="User not found")

    if request.email and request.email != user.email:
        existing = db.query(models.User).filter(models.User.email == request.email).first()
        if existing:
            raise AppException(status_code=400, code="BAD_REQUEST", message="Email already taken")
        user.email = request.email

    if request.login and request.login != user.login:
        existing = db.query(models.User).filter(models.User.login == request.login).first()
        if existing:
            raise AppException(status_code=400, code="BAD_REQUEST", message="Login already taken")
        user.login = request.login

    db.commit()
    db.refresh(user)

    return user_to_profile(user)


@router.delete("/me", status_code=204)
def delete_account(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    if not user:
        raise AppException(status_code=404, code="NOT_FOUND", message="User not found")
    db.delete(user)
    db.commit()


@router.get("/me/preferences", response_model=schemas.UserPreferencesResponse)
def get_preferences(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    prefs = db.query(models.UserPreferences).filter(models.UserPreferences.user_id == current_user.id).first()
    if not prefs:
        return schemas.UserPreferencesResponse()
    return prefs


@router.put("/me/preferences", response_model=schemas.UserPreferencesResponse)
def update_preferences(
    request: schemas.UserPreferencesUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prefs = db.query(models.UserPreferences).filter(models.UserPreferences.user_id == current_user.id).first()
    if not prefs:
        prefs = models.UserPreferences(user_id=current_user.id)
        db.add(prefs)

    if request.travel_types is not None:
        prefs.travel_types = request.travel_types
    if request.favorite_destinations is not None:
        prefs.favorite_destinations = request.favorite_destinations
    if request.currency is not None:
        prefs.currency = request.currency
    if request.budget_min is not None:
        prefs.budget_min = request.budget_min
    if request.budget_max is not None:
        prefs.budget_max = request.budget_max
    if request.trip_duration is not None:
        prefs.trip_duration = request.trip_duration
    if request.additional_info is not None:
        prefs.additional_info = request.additional_info

    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    if user:
        user.onboarding_completed = True

    db.commit()
    db.refresh(prefs)
    return prefs
