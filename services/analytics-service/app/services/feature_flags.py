import hashlib
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.models.feature_flag import AdminAuditLog, FeatureFlag

SUGGESTED_FLAGS = [
    "analytics_collection_enabled",
    "hybrid_ranker_v2_enabled",
    "behavioral_ltr_augmentation_enabled",
    "budget_monitor_ml_enabled",
    "itinerary_ranker_enabled",
    "itinerary_dnd_enabled",
    "travel_fare_enrichment_enabled",
    "destination_validation_block_enabled",
]


def _bucket(flag_key: str, identity: str) -> float:
    digest = hashlib.sha256(f"{flag_key}:{identity}".encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF * 100


def _target_allows(flag: FeatureFlag, user_id: UUID | None, anonymous_id: str | None, platform: str | None) -> bool:
    targeting = flag.targeting_json or {}
    current_environment = getattr(settings, "ENVIRONMENT", "local")
    if flag.environment not in {"all", current_environment}:
        return False

    environments = targeting.get("environments")
    if isinstance(environments, list) and environments and current_environment not in environments:
        return False

    platforms = targeting.get("platforms")
    if isinstance(platforms, list) and platforms and platform not in platforms:
        return False

    identity = str(user_id) if user_id is not None else anonymous_id
    allowlist = targeting.get("allowlist")
    if isinstance(allowlist, list) and identity in {str(value) for value in allowlist}:
        return True

    return True


def evaluate_flag(flag: FeatureFlag, user_id: UUID | None, anonymous_id: str | None, platform: str | None) -> bool:
    if not flag.enabled:
        return False
    if not _target_allows(flag, user_id, anonymous_id, platform):
        return False
    identity = str(user_id) if user_id is not None else anonymous_id or "anonymous"
    return _bucket(flag.key, identity) < max(0.0, min(flag.rollout_percentage, 100.0))


def list_evaluated_flags(
    db: Session,
    *,
    user_id: UUID | None,
    anonymous_id: str | None,
    platform: str | None,
) -> dict[str, dict[str, Any]]:
    flags = {flag.key: flag for flag in db.query(FeatureFlag).all()}
    return {
        key: {
            "key": key,
            "enabled": evaluate_flag(flag, user_id, anonymous_id, platform) if flag else False,
            "payload": flag.payload_json or {} if flag else {},
        }
        for key, flag in flags.items()
    }


def write_audit_log(
    db: Session,
    *,
    actor_user_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: str | None,
    context: dict[str, Any] | None,
) -> None:
    db.add(
        AdminAuditLog(
            actor_user_id=str(actor_user_id) if actor_user_id else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            context=context,
        )
    )
