import enum
import uuid

from sqlalchemy import (
    CheckConstraint,
    Enum,
    Float,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VisaType(str, enum.Enum):
    visa_free = "visa_free"
    evisa = "evisa"
    visa_required = "visa_required"
    no_admission = "no_admission"


VISA_SCORES: dict[VisaType, float] = {
    VisaType.visa_free: 1.0,
    VisaType.evisa: 0.6,
    VisaType.visa_required: 0.2,
    VisaType.no_admission: 0.0,
}


class VisaRule(Base):
    __tablename__ = "visa_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    citizenship_code: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    visa_type: Mapped[VisaType] = mapped_column(
        Enum(VisaType, name="visatype"), nullable=False
    )
    visa_score: Mapped[float] = mapped_column(Float, nullable=False)
    max_stay_days: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "citizenship_code", "destination_id", name="uq_visa_citizenship_dest"
        ),
        CheckConstraint("visa_score >= 0 AND visa_score <= 1", name="ck_visa_score"),
    )
