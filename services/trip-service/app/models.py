from sqlalchemy import Column, Date, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.base_model import BaseModel


class Trip(BaseModel):
    __tablename__ = "trips"
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    budget = Column(Float, nullable=True)
    currency = Column(String, nullable=False, default="RUB")
    people_count = Column(Integer, nullable=False, default=1)
    status = Column(String, nullable=False, default="planned")
    trip_type = Column(String, nullable=True)
    season = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
