from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_admin_user_id
from app.models.user_event import UserEvent

router = APIRouter(prefix="/api/v1/admin/dashboards", tags=["admin-dashboards"])

PRODUCT_EVENTS = [
    "app_opened",
    "session_started",
    "onboarding_completed",
    "recommendation_shown",
    "recommendation_clicked",
    "destination_detail_opened",
    "trip_created",
    "itinerary_viewed",
    "itinerary_generated",
    "itinerary_approved",
    "expense_added",
    "post_trip_feedback_submitted",
]

ML_EVENTS = [
    "recommendation_impression",
    "budget_prediction_served",
    "budget_monitor_served",
    "itinerary_candidate_generated",
    "validation_result_served",
]

OPERATIONAL_EVENTS = [
    "failed_api_request",
    "slow_api_request",
    "frontend_error",
    "frontend_unhandled_rejection",
    "service_worker_error",
    "network_status_changed",
    "external_api_call_completed",
]


@router.get("/summary")
def dashboard_summary(
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
):
    del user_id
    event_counts = dict(db.query(UserEvent.event_type, func.count(UserEvent.id)).group_by(UserEvent.event_type).all())
    active_users = (
        db.query(func.count(func.distinct(UserEvent.user_id))).filter(UserEvent.user_id.isnot(None)).scalar() or 0
    )
    active_sessions = db.query(func.count(func.distinct(UserEvent.session_id))).scalar() or 0
    recent_events = db.query(UserEvent).order_by(UserEvent.created_at.desc()).limit(25).all()
    return {
        "product": {
            "active_users": active_users,
            "active_sessions": active_sessions,
            "counts": {key: int(event_counts.get(key, 0)) for key in PRODUCT_EVENTS},
        },
        "ml": {
            "counts": {key: int(event_counts.get(key, 0)) for key in ML_EVENTS},
        },
        "operational": {
            "counts": {key: int(event_counts.get(key, 0)) for key in OPERATIONAL_EVENTS},
        },
        "recent_events": [_event_to_dict(event) for event in recent_events],
    }


@router.get("/events")
def events_explorer(
    event_type: str | None = None,
    user_id_filter: str | None = Query(default=None, alias="user_id"),
    session_id: str | None = None,
    entity_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
):
    del user_id
    query = db.query(UserEvent)
    if event_type:
        query = query.filter(UserEvent.event_type == event_type)
    if user_id_filter:
        query = query.filter(UserEvent.user_id == user_id_filter)
    if session_id:
        query = query.filter(UserEvent.session_id == session_id)
    if entity_id:
        query = query.filter(UserEvent.entity_id == entity_id)
    events = query.order_by(UserEvent.created_at.desc()).limit(limit).all()
    return {"events": [_event_to_dict(event) for event in events]}


def _event_to_dict(event: UserEvent) -> dict:
    return {
        "id": str(event.id),
        "event_id": str(event.event_id) if event.event_id else None,
        "user_id": str(event.user_id) if event.user_id else None,
        "session_id": str(event.session_id),
        "event_type": event.event_type,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "context": _mask_context(event.context or {}),
        "client_meta": _mask_context(event.client_meta or {}),
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def _mask_context(value):
    if isinstance(value, dict):
        masked = {}
        for key, nested in value.items():
            if any(part in key.lower() for part in ["email", "token", "password", "secret", "oauth"]):
                masked[key] = "***"
            else:
                masked[key] = _mask_context(nested)
        return masked
    if isinstance(value, list):
        return [_mask_context(item) for item in value]
    return value
