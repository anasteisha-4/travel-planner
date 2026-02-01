from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserPreferences(BaseModel):
    # TODO: редактировать в зависимости от анкеты
    interests: list[str] = []
    budget_preference: str | None = "medium"
    travel_styles: list[str] = []
    currency: str = "RUB"

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    login: str
    first_name: str | None = None
    last_name: str | None = None
    preferences: UserPreferences | None = None

class UserProfile(BaseModel):
    id: UUID
    email: str
    login: str
    first_name: str | None
    last_name: str | None
    preferences: UserPreferences | None

    class Config:
        from_attributes = True
