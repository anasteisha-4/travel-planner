from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import UUID

class UserPreferences(BaseModel):
    # TODO: редактировать в зависимости от анкеты
    interests: List[str] = []
    budget_preference: Optional[str] = "medium"
    travel_styles: List[str] = []
    currency: str = "RUB"

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    login: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    preferences: Optional[UserPreferences] = None

class UserProfile(BaseModel):
    id: UUID
    email: str
    login: str
    first_name: Optional[str]
    last_name: Optional[str]
    preferences: Optional[UserPreferences]

    class Config:
        from_attributes = True
