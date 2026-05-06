import uuid
from datetime import UTC, datetime
from typing import cast

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.post_trip_feedback import PostTripFeedback
from app.models.user_event import UserEvent
from app.models.user_features import UserFeatures

ACTIVITY_TYPES = [
    "beach",
    "culture",
    "nature",
    "adventure",
    "food",
    "nightlife",
    "wellness",
    "shopping",
    "family",
    "urban",
]

VACATION_PREF_TO_ACTIVITY = {
    "beach": 0,
    "culture": 1,
    "nature": 2,
    "adventure": 3,
    "active": 3,
    "food": 4,
    "gastronomy": 4,
    "nightlife": 5,
    "wellness": 6,
    "relaxation": 6,
    "shopping": 7,
    "family": 8,
    "urban": 9,
    "city": 9,
}


async def _fetch_profile(user_id: uuid.UUID, auth_header: str | None) -> dict | None:
    if not settings.TRIP_SERVICE_URL:
        return None
    headers = {}
    if auth_header:
        headers["Authorization"] = auth_header
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.TRIP_SERVICE_URL}/api/profile",
                headers=headers,
            )
            if resp.status_code == 200:
                return cast(dict, resp.json())
    except (httpx.RequestError, httpx.TimeoutException):
        pass
    return None


def _build_layer1(profile: dict) -> dict:
    activity_vector = [0.0] * len(ACTIVITY_TYPES)

    prefs = profile.get("vacation_preferences_ranked") or []
    for position, pref_key in enumerate(prefs[:5]):
        weight = (5 - position) / 5.0
        idx = VACATION_PREF_TO_ACTIVITY.get(pref_key)
        if idx is not None:
            activity_vector[idx] = max(activity_vector[idx], weight)

    duration_days = profile.get("typical_duration_days")

    return {
        "activity_prefs_vector": activity_vector if any(v > 0 for v in activity_vector) else None,
        "budget_min_usd": profile.get("budget_min_usd"),
        "budget_max_usd": profile.get("budget_max_usd"),
        "preferred_duration_days": int(duration_days) if duration_days is not None else None,
        "origin_lat": profile.get("origin_lat"),
        "origin_lng": profile.get("origin_lng"),
        "onboarding_completed": bool(profile.get("onboarding_completed", False)),
    }


def _build_layer2(user_id: uuid.UUID, db: Session) -> dict:
    viewed_ids: list[str] = []
    clicked_ids: list[str] = []

    view_rows = (
        db.query(UserEvent.entity_id)
        .filter(
            UserEvent.user_id == user_id,
            UserEvent.event_type.in_(["recommendation_impression", "recommendation_shown"]),
            UserEvent.entity_id.isnot(None),
        )
        .distinct()
        .limit(100)
        .all()
    )
    viewed_ids = [r.entity_id for r in view_rows if r.entity_id]

    click_rows = (
        db.query(UserEvent.entity_id)
        .filter(
            UserEvent.user_id == user_id,
            UserEvent.event_type.in_(["recommendation_clicked", "destination_detail_opened"]),
            UserEvent.entity_id.isnot(None),
        )
        .distinct()
        .limit(50)
        .all()
    )
    clicked_ids = [r.entity_id for r in click_rows if r.entity_id]

    session_stats = (
        db.query(
            func.count(func.distinct(UserEvent.session_id)).label("session_count"),
            func.count(UserEvent.id).label("total_events"),
        )
        .filter(UserEvent.user_id == user_id)
        .one()
    )

    session_count = session_stats.session_count or 0
    avg_session_events = round(session_stats.total_events / session_count, 2) if session_count > 0 else None

    return {
        "viewed_destination_ids": viewed_ids or None,
        "clicked_destination_ids": clicked_ids or None,
        "session_count": session_count or None,
        "avg_session_events": avg_session_events,
    }


def _build_layer3(user_id: uuid.UUID, db: Session) -> dict:
    feedback_rows = db.query(PostTripFeedback).filter(PostTripFeedback.user_id == user_id).all()

    if not feedback_rows:
        return {
            "completed_trips_count": None,
            "avg_spend_ratio": None,
            "visited_destination_ids": None,
            "avg_destination_rating": None,
            "would_revisit_ratio": None,
        }

    visited = [r.destination for r in feedback_rows if r.destination]
    ratings = [r.destination_rating for r in feedback_rows if r.destination_rating is not None]
    revisit_flags = [r.would_revisit for r in feedback_rows if r.would_revisit is not None]

    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
    revisit_ratio = round(sum(1 for v in revisit_flags if v) / len(revisit_flags), 2) if revisit_flags else None

    return {
        "completed_trips_count": len(feedback_rows),
        "avg_spend_ratio": None,
        "visited_destination_ids": visited or None,
        "avg_destination_rating": avg_rating,
        "would_revisit_ratio": revisit_ratio,
    }


async def build_user_features(
    user_id: uuid.UUID,
    db: Session,
    auth_header: str | None = None,
) -> UserFeatures:
    profile = await _fetch_profile(user_id, auth_header)

    layer1 = (
        _build_layer1(profile)
        if profile
        else {
            "activity_prefs_vector": None,
            "budget_min_usd": None,
            "budget_max_usd": None,
            "preferred_duration_days": None,
            "origin_lat": None,
            "origin_lng": None,
            "onboarding_completed": False,
        }
    )

    layer2 = _build_layer2(user_id, db)
    layer3 = _build_layer3(user_id, db)

    l2_events = (layer2.get("session_count") or 0) + len(layer2.get("clicked_destination_ids") or [])
    l3_trips = layer3.get("completed_trips_count") or 0
    confidence = min(1.0, round((l2_events * 0.02 + l3_trips * 0.1), 2)) if (l2_events or l3_trips) else None

    existing = db.query(UserFeatures).filter(UserFeatures.user_id == user_id).first()

    if existing:
        for k, v in {**layer1, **layer2, **layer3}.items():
            setattr(existing, k, v)
        existing.confidence = confidence
        existing.feature_version = (existing.feature_version or 1) + 1
        existing.computed_at = datetime.now(UTC)
        db.commit()
        db.refresh(existing)
        return existing

    features = UserFeatures(
        user_id=user_id,
        feature_version=1,
        computed_at=datetime.now(UTC),
        confidence=confidence,
        **layer1,
        **layer2,
        **layer3,
    )
    db.add(features)
    db.commit()
    db.refresh(features)
    return features
