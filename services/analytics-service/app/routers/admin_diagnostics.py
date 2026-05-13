from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_admin_user_id
from app.models.user_event import UserEvent
from app.routers.admin_dashboards import _event_to_dict, _mask_context

router = APIRouter(prefix="/api/v1/admin/diagnostics", tags=["admin-diagnostics"])


@router.get("/models")
def model_registry(
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
):
    del user_id
    if not _table_exists(db, "model_registry"):
        return {"models": []}
    rows = db.execute(
        text(
            "SELECT id::text, name, version, model_type, is_active, metrics, trained_at, created_at "
            "FROM model_registry "
            "ORDER BY is_active DESC, trained_at DESC NULLS LAST, created_at DESC"
        )
    ).mappings()
    return {
        "models": [
            {
                "id": row["id"],
                "name": row["name"],
                "version": row["version"],
                "model_type": row["model_type"],
                "is_active": bool(row["is_active"]),
                "metrics": row["metrics"] or {},
                "trained_at": row["trained_at"].isoformat() if row["trained_at"] else None,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ]
    }


@router.get("/recommendations/{recommendation_id}")
def recommendation_debug(
    recommendation_id: str,
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
):
    del user_id
    log = None
    if _table_exists(db, "recommendation_logs"):
        log = (
            db.execute(
                text(
                    "SELECT id::text, user_id::text, request, model_version, scorer_weights, results, latency_ms, created_at "
                    "FROM recommendation_logs "
                    "WHERE id::text = :recommendation_id"
                ),
                {"recommendation_id": recommendation_id},
            )
            .mappings()
            .one_or_none()
        )
    events = (
        db.query(UserEvent)
        .filter(
            (UserEvent.entity_id == recommendation_id)
            | (UserEvent.context["recommendation_id"].astext == recommendation_id)
        )
        .order_by(UserEvent.created_at.asc())
        .limit(200)
        .all()
    )
    return {
        "recommendation_log": _recommendation_log_to_dict(log) if log else None,
        "events": [_event_to_dict(event) for event in events],
    }


@router.get("/budget")
def budget_debug(
    trip_id: str | None = None,
    destination_id: str | None = None,
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
):
    del user_id
    query = db.query(UserEvent).filter(UserEvent.event_type.in_(["budget_prediction_served", "budget_monitor_served"]))
    if trip_id:
        query = query.filter((UserEvent.entity_id == trip_id) | (UserEvent.context["trip_id"].astext == trip_id))
    if destination_id:
        query = query.filter(
            (UserEvent.entity_id == destination_id) | (UserEvent.context["destination_id"].astext == destination_id)
        )
    events = query.order_by(UserEvent.created_at.desc()).limit(100).all()
    feedback = []
    if trip_id and _table_exists(db, "post_trip_feedback"):
        feedback = [
            dict(row)
            for row in db.execute(
                text(
                    "SELECT trip_id, destination, overall_rating, value_rating, actual_total_cost, actual_currency, "
                    "would_revisit, created_at "
                    "FROM post_trip_feedback "
                    "WHERE trip_id = :trip_id"
                ),
                {"trip_id": trip_id},
            ).mappings()
        ]
    return {"events": [_event_to_dict(event) for event in events], "feedback": feedback}


@router.get("/itinerary")
def itinerary_debug(
    trip_id: str | None = None,
    itinerary_id: str | None = None,
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
):
    del user_id
    event_types = [
        "itinerary_candidate_generated",
        "itinerary_viewed",
        "itinerary_generated",
        "itinerary_approved",
        "itinerary_regenerated",
        "itinerary_poi_moved",
        "itinerary_poi_removed",
        "itinerary_poi_added",
        "place_visit_marked_visited",
    ]
    query = db.query(UserEvent).filter(UserEvent.event_type.in_(event_types))
    if trip_id:
        query = query.filter((UserEvent.entity_id == trip_id) | (UserEvent.context["trip_id"].astext == trip_id))
    if itinerary_id:
        query = query.filter(UserEvent.context["itinerary_id"].astext == itinerary_id)
    events = query.order_by(UserEvent.created_at.desc()).limit(150).all()
    return {"events": [_event_to_dict(event) for event in events]}


@router.get("/timeline")
def timeline(
    user_id_filter: str | None = Query(default=None, alias="user_id"),
    session_id: str | None = None,
    limit: int = Query(default=200, ge=1, le=500),
    user_id=Depends(get_admin_user_id),
    db: Session = Depends(get_db),
):
    del user_id
    query = db.query(UserEvent)
    if user_id_filter:
        query = query.filter(UserEvent.user_id == user_id_filter)
    if session_id:
        query = query.filter(UserEvent.session_id == session_id)
    events = query.order_by(UserEvent.created_at.asc()).limit(limit).all()
    grouped: dict[str, list[dict]] = {}
    for event in events:
        grouped.setdefault(str(event.session_id), []).append(_event_to_dict(event))
    return {"sessions": [{"session_id": key, "events": value} for key, value in grouped.items()]}


def _recommendation_log_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "request": _mask_context(row["request"] or {}),
        "model_version": row["model_version"],
        "scorer_weights": row["scorer_weights"] or {},
        "results": row["results"] or [],
        "latency_ms": row["latency_ms"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


def _table_exists(db: Session, table_name: str) -> bool:
    return bool(db.execute(text("SELECT to_regclass(:table_name)"), {"table_name": table_name}).scalar())
