from sqlalchemy import JSON, Boolean, Column, String

from app.base_model import BaseModel


class User(BaseModel):
    __tablename__ = "users"
    email = Column(String, unique=True, index=True, nullable=False)
    login = Column(String, unique=True, index=True, nullable=True)
    password_hash = Column(String, nullable=True)
    yandex_id = Column(String, unique=True, index=True, nullable=True)

    onboarding_completed = Column(Boolean, default=False, nullable=False, server_default="false")
    preferences = Column(JSON, nullable=True)
