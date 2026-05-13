from sqlalchemy import Boolean, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.base_model import BaseModel


class FeatureFlag(BaseModel):
    __tablename__ = "feature_flags"

    key: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    rollout_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    environment: Mapped[str] = mapped_column(String(40), nullable=False, default="all", server_default="all")
    targeting_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class AdminAuditLog(BaseModel):
    __tablename__ = "admin_audit_logs"

    actor_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class Experiment(BaseModel):
    __tablename__ = "experiments"

    key: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active", server_default="active")
    variants_json: Mapped[list] = mapped_column(JSONB, nullable=False)
    metrics_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    guardrails_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class ExperimentAssignment(BaseModel):
    __tablename__ = "analytics_experiment_assignments"

    experiment_key: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    variant: Mapped[str] = mapped_column(String(80), nullable=False)
    subject_key: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    anonymous_id: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
