import re
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator, model_validator


def validate_password_strength(v: str) -> str:
    """Shared password strength validation"""
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


class UserPreferences(BaseModel):
    travel_types: list[str] = []
    favorite_destinations: str | None = None
    currency: str = "RUB"
    budget_min: int | None = None
    budget_max: int | None = None
    trip_duration: str | None = None
    departure_city: str | None = None
    additional_info: str | None = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    login: str
    preferences: UserPreferences | None = None

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)

    @model_validator(mode="after")
    def passwords_match(self) -> "ResetPasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class UserProfile(BaseModel):
    id: UUID
    email: str
    login: str
    onboarding_completed: bool
    preferences: UserPreferences | None

    class Config:
        from_attributes = True
