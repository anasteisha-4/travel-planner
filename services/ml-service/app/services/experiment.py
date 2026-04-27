import hashlib
import uuid

from sqlalchemy.orm import Session

from app.models.experiment import ExperimentAssignment

_EXPERIMENTS: dict[str, list[str]] = {
    "scorer_ab": ["content-v1", "ltr-v1"],
}


def get_variant(db: Session, user_id: uuid.UUID, experiment_name: str) -> str:
    """Return deterministic variant for user; persist assignment on first call."""
    variants = _EXPERIMENTS.get(experiment_name)
    if not variants:
        raise ValueError(f"Unknown experiment: {experiment_name}")

    existing = (
        db.query(ExperimentAssignment)
        .filter(
            ExperimentAssignment.user_id == user_id,
            ExperimentAssignment.experiment_name == experiment_name,
        )
        .first()
    )
    if existing:
        return existing.variant

    bucket = _hash_bucket(user_id, experiment_name, len(variants))
    variant = variants[bucket]

    assignment = ExperimentAssignment(
        user_id=user_id,
        experiment_name=experiment_name,
        variant=variant,
    )
    try:
        db.add(assignment)
        db.commit()
    except Exception:
        db.rollback()

    return variant


def _hash_bucket(user_id: uuid.UUID, experiment_name: str, num_variants: int) -> int:
    key = f"{user_id}:{experiment_name}".encode()
    digest = hashlib.sha256(key).digest()
    return int.from_bytes(digest[:4], "big") % num_variants
