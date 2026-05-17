from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, text
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
    "llm_quality_review_completed",
    "llm_quality_adjustment_applied",
    "llm_quality_skipped",
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
        "charts": {
            "daily_events": _daily_event_series(db),
            "top_events": _top_events(db),
            "recommendation_funnel": _funnel(
                event_counts,
                [
                    "recommendation_shown",
                    "recommendation_impression",
                    "recommendation_clicked",
                    "destination_detail_opened",
                    "trip_created",
                ],
            ),
            "itinerary_funnel": _funnel(
                event_counts,
                [
                    "itinerary_viewed",
                    "itinerary_generated",
                    "itinerary_approved",
                    "itinerary_poi_moved",
                    "place_visit_marked_visited",
                ],
            ),
            "operational_daily": _operational_series(db),
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


def _daily_event_series(db: Session) -> list[dict]:
    rows = db.execute(
        text(
            "SELECT date_trunc('day', created_at)::date AS day, "
            "COUNT(*) AS total, "
            "COUNT(DISTINCT user_id) FILTER (WHERE user_id IS NOT NULL) AS users, "
            "COUNT(DISTINCT session_id) AS sessions "
            "FROM user_events "
            "WHERE created_at >= now() - interval '13 days' "
            "GROUP BY day "
            "ORDER BY day"
        )
    ).mappings()
    return [
        {
            "date": str(row["day"]),
            "events": int(row["total"] or 0),
            "users": int(row["users"] or 0),
            "sessions": int(row["sessions"] or 0),
        }
        for row in rows
    ]


def _operational_series(db: Session) -> list[dict]:
    rows = (
        db.query(
            func.date_trunc("day", UserEvent.created_at).label("day"),
            func.count(UserEvent.id).label("total"),
            func.sum(case((UserEvent.event_type == "failed_api_request", 1), else_=0)).label("failed"),
            func.sum(case((UserEvent.event_type == "slow_api_request", 1), else_=0)).label("slow"),
            func.sum(case((UserEvent.event_type == "frontend_error", 1), else_=0)).label("frontend_errors"),
        )
        .filter(
            UserEvent.event_type.in_(OPERATIONAL_EVENTS),
            UserEvent.created_at >= func.now() - text("interval '13 days'"),
        )
        .group_by("day")
        .order_by("day")
        .all()
    )
    return [
        {
            "date": row.day.date().isoformat() if row.day else None,
            "total": int(row.total or 0),
            "failed": int(row.failed or 0),
            "slow": int(row.slow or 0),
            "frontend_errors": int(row.frontend_errors or 0),
        }
        for row in rows
    ]


def _top_events(db: Session) -> list[dict]:
    rows = (
        db.query(UserEvent.event_type, func.count(UserEvent.id).label("count"))
        .group_by(UserEvent.event_type)
        .order_by(func.count(UserEvent.id).desc())
        .limit(12)
        .all()
    )
    return [{"event_type": row.event_type, "count": int(row.count or 0)} for row in rows]


def _funnel(event_counts: dict, event_names: list[str]) -> list[dict]:
    first_count = int(event_counts.get(event_names[0], 0) or 0) if event_names else 0
    return [
        {
            "event_type": event_name,
            "count": int(event_counts.get(event_name, 0) or 0),
            "conversion": round((int(event_counts.get(event_name, 0) or 0) / first_count), 4) if first_count else None,
        }
        for event_name in event_names
    ]
