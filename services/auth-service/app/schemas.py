import re
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator


class UserPreferences(BaseModel):
    travel_types: list[str] = []
    favorite_destinations: str | None = None
    currency: str = "RUB"
    budget_min: int | None = None
    budget_max: int | None = None
    trip_duration: str | None = None
    additional_info: str | None = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    login: str
    preferences: UserPreferences | None = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[a-zа-яё]", v.lower()):
            raise ValueError("Password must contain lowercase letters")
        if not re.search(r"[A-ZА-ЯЁ]", v):
            raise ValueError("Password must contain uppercase letters")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain digits")
        if not re.search(r"[^a-zA-Zа-яА-ЯёЁ0-9\s]", v):
            raise ValueError("Password must contain special characters")
        return v


class UserProfile(BaseModel):
    id: UUID
    email: str
    login: str
    onboarding_completed: bool
    preferences: UserPreferences | None

    class Config:
        from_attributes = True
