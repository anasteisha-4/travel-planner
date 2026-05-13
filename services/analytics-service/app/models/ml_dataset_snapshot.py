from datetime import datetime

from sqlalchemy import TIMESTAMP, BigInteger, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.base_model import BaseModel


class MLDatasetSnapshot(BaseModel):
    __tablename__ = "ml_dataset_snapshots"

    dataset_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    date_from: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    date_to: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    contract_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1", server_default="1")
    builder_version: Mapped[str] = mapped_column(String(80), nullable=False)
    row_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    positive_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sanity_report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    __table_args__ = (
        Index("ix_ml_dataset_snapshots_type_created", "dataset_type", "created_at"),
        Index("ix_ml_dataset_snapshots_range", "date_from", "date_to"),
    )
