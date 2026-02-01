"""
Users router - profile and preferences management
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from app import schemas, models, utils
from app.database import get_db

router = APIRouter()


class ProfileUpdateRequest(BaseModel):
    email: Optional[EmailStr] = None
    login: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> models.User:
    """Extract and validate user from Authorization header"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.replace("Bearer ", "")
    payload = utils.decode_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = payload.get("sub")
    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def user_to_profile(user: models.User) -> schemas.UserProfile:
    """Convert User model to UserProfile schema"""
    preferences = None
    if user.interests or user.budget_preference or user.travel_styles:
        preferences = schemas.UserPreferences(
            interests=user.interests or [],
            budget_preference=user.budget_preference or "medium",
            travel_styles=user.travel_styles or [],
        )
    return schemas.UserProfile(
        id=user.id,
        email=user.email,
        login=user.login,
        first_name=user.first_name,
        last_name=user.last_name,
        preferences=preferences
    )


@router.get("/me", response_model=schemas.UserProfile)
def get_profile(current_user: models.User = Depends(get_current_user)):
    """Get current user profile"""
    return user_to_profile(current_user)


@router.put("/me", response_model=schemas.UserProfile)
def update_profile(
    request: ProfileUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile (email, login, first_name, last_name)"""
    user = db.query(models.User).filter(models.User.id == current_user.id).first()

    if request.email and request.email != user.email:
        existing = db.query(models.User).filter(models.User.email == request.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already taken")
        user.email = request.email

    if request.login and request.login != user.login:
        existing = db.query(models.User).filter(models.User.login == request.login).first()
        if existing:
            raise HTTPException(status_code=400, detail="Login already taken")
        user.login = request.login

    if request.first_name is not None:
        user.first_name = request.first_name

    if request.last_name is not None:
        user.last_name = request.last_name

    db.commit()
    db.refresh(user)

    return user_to_profile(user)


@router.get("/me/preferences", response_model=schemas.UserPreferences)
def get_preferences(current_user: models.User = Depends(get_current_user)):
    """Get user preferences"""
    return schemas.UserPreferences(
        interests=current_user.interests or [],
        budget_preference=current_user.budget_preference or "medium",
        travel_styles=current_user.travel_styles or [],
    )


@router.put("/me/preferences", response_model=schemas.UserPreferences)
def update_preferences(
    preferences: schemas.UserPreferences,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user preferences"""
    user = db.query(models.User).filter(models.User.id == current_user.id).first()

    user.interests = preferences.interests
    user.budget_preference = preferences.budget_preference
    user.travel_styles = preferences.travel_styles
    user.preferences = preferences.model_dump()

    db.commit()

    return preferences
