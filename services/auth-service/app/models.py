import uuid

from sqlalchemy import JSON, TIMESTAMP, Boolean, Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    login = Column(String, unique=True, index=True, nullable=True)
    password_hash = Column(String, nullable=True)
    yandex_id = Column(String, unique=True, index=True, nullable=True)

    onboarding_completed = Column(Boolean, default=False, nullable=False, server_default="false")
    preferences = Column(JSON, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
