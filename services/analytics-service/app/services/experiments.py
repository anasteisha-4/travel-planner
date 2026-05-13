import hashlib
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.feature_flag import Experiment, ExperimentAssignment
from app.models.user_event import UserEvent

TRACKED_METRIC_EVENTS = [
    "recommendation_shown",
    "recommendation_clicked",
    "destination_detail_opened",
    "validation_viewed",
    "budget_prediction_viewed",
    "trip_created",
    "itinerary_generated",
    "itinerary_approved",
    "post_trip_feedback_submitted",
    "failed_api_request",
    "slow_api_request",
    "recommendation_empty_state_shown",
]


def _subject_key(user_id: UUID | None, anonymous_id: str | None) -> str:
    return f"user:{user_id}" if user_id is not None else f"anonymous:{anonymous_id or 'unknown'}"


def _variant_for(experiment_key: str, subject_key: str, variants: list[str]) -> str:
    digest = hashlib.sha256(f"{experiment_key}:{subject_key}".encode()).hexdigest()
    return variants[int(digest[:8], 16) % len(variants)]


def get_assignments(db: Session, *, user_id: UUID | None, anonymous_id: str | None) -> dict[str, str]:
    subject = _subject_key(user_id, anonymous_id)
    experiments = db.query(Experiment).filter(Experiment.status == "active").all()
    assignments: dict[str, str] = {}
    for experiment in experiments:
        existing = (
            db.query(ExperimentAssignment)
            .filter(
                ExperimentAssignment.experiment_key == experiment.key,
                ExperimentAssignment.subject_key == subject,
            )
            .one_or_none()
        )
        if existing is None:
            variant = _variant_for(experiment.key, subject, list(experiment.variants_json))
            existing = ExperimentAssignment(
                experiment_key=experiment.key,
                variant=variant,
                subject_key=subject,
                user_id=str(user_id) if user_id else None,
                anonymous_id=anonymous_id,
            )
            db.add(existing)
            db.flush()
        assignments[experiment.key] = existing.variant
        _record_exposure(
            db, user_id=user_id, anonymous_id=anonymous_id, experiment_key=experiment.key, variant=existing.variant
        )
    db.commit()
    return assignments


def _record_exposure(
    db: Session,
    *,
    user_id: UUID | None,
    anonymous_id: str | None,
    experiment_key: str,
    variant: str,
) -> None:
    db.add(
        UserEvent(
            event_id=uuid4(),
            user_id=user_id,
            session_id=user_id or uuid5(NAMESPACE_URL, anonymous_id or "anonymous"),
            event_type="experiment_exposed",
            entity_type="experiment",
            entity_id=experiment_key,
            context={"experiment_id": experiment_key, "variant": variant},
            client_meta={"platform": "server", "service": "analytics-service"},
            created_at=datetime.now(UTC),
        )
    )


def build_experiment_report(db: Session, experiment_key: str) -> dict[str, dict[str, int]]:
    rows = (
        db.query(UserEvent.event_type, UserEvent.context["variant"].astext.label("variant"), func.count(UserEvent.id))
        .filter(UserEvent.context["experiment_id"].astext == experiment_key)
        .filter(UserEvent.event_type.in_(TRACKED_METRIC_EVENTS + ["experiment_exposed"]))
        .group_by(UserEvent.event_type, "variant")
        .all()
    )
    report: dict[str, dict[str, int]] = {}
    for event_type, variant, count in rows:
        if variant is None:
            continue
        report.setdefault(str(variant), {})[str(event_type)] = int(count)
    return report
