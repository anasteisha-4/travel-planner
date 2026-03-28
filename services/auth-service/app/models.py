from typing import Any

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.base_model import BaseModel


class User(BaseModel):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    login: Mapped[str | None] = mapped_column(String, unique=True, index=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    yandex_id: Mapped[str | None] = mapped_column(String, unique=True, index=True, nullable=True)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    preferences: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
