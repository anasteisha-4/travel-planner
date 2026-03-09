"""
Users router - profile and preferences management
"""

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
    """Convert User model to UserProfile schema"""
    preferences = None
    if user.preferences:
        preferences = schemas.UserPreferences(**user.preferences)
    return schemas.UserProfile(
        id=user.id,
        email=user.email,
        login=user.login,
        onboarding_completed=user.onboarding_completed,
        preferences=preferences,
    )


@router.get("/me", response_model=schemas.UserProfile)
def get_profile(current_user: models.User = Depends(get_current_user)):
    """Get current user profile"""
    return user_to_profile(current_user)


@router.put("/me", response_model=schemas.UserProfile)
def update_profile(
    request: ProfileUpdateRequest, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Update user profile (email, login)"""
    user = db.query(models.User).filter(models.User.id == current_user.id).first()

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


@router.get("/me/preferences", response_model=schemas.UserPreferences)
def get_preferences(current_user: models.User = Depends(get_current_user)):
    """Get user preferences"""
    if current_user.preferences:
        return schemas.UserPreferences(**current_user.preferences)
    return schemas.UserPreferences()


@router.put("/me/preferences", response_model=schemas.UserPreferences)
def update_preferences(
    preferences: schemas.UserPreferences,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user preferences and mark onboarding as completed"""
    user = db.query(models.User).filter(models.User.id == current_user.id).first()

    user.preferences = preferences.model_dump()
    user.onboarding_completed = True

    db.commit()

    return preferences
