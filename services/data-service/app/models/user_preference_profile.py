import uuid

from sqlalchemy import Float, SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.base_model import BaseModel


class UserPreferenceProfile(BaseModel):
    __tablename__ = "user_preference_profiles"

    citizenship_code: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    travel_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    budget_tier: Mapped[str] = mapped_column(String(20), nullable=False)
    preferred_activities: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )
    trip_type: Mapped[str] = mapped_column(String(50), nullable=False)
    min_safety_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    profile_type: Mapped[str] = mapped_column(String(50), nullable=False)
    label_destination_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    label_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="synthetic")
