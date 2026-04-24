import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.post_trip_feedback import PostTripFeedback
from app.models.user_event import UserEvent
from app.models.user_features import UserFeatures

TEST_USER_ID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

PROFILE_RESPONSE = {
    "user_id": str(TEST_USER_ID),
    "vacation_preferences_ranked": ["beach", "culture", "nature"],
    "preferred_currency": "USD",
    "budget_min_usd": 500.0,
    "budget_max_usd": 2000.0,
    "typical_duration_days": 10,
    "origin_lat": 55.75,
    "origin_lng": 37.62,
    "onboarding_completed": True,
}


def _add_events(db: Session, user_id: uuid.UUID):
    session_id = uuid.uuid4()
    events = [
        UserEvent(
            user_id=user_id,
            session_id=session_id,
            event_type="recommendation_shown",
            entity_type="destination",
            entity_id="10",
        ),
        UserEvent(
            user_id=user_id,
            session_id=session_id,
            event_type="recommendation_clicked",
            entity_type="destination",
            entity_id="10",
        ),
        UserEvent(
            user_id=user_id,
            session_id=uuid.uuid4(),
            event_type="destination_detail_opened",
            entity_type="destination",
            entity_id="20",
        ),
    ]
    db.add_all(events)
    db.commit()


def _add_feedback(db: Session, user_id: uuid.UUID):
    feedback = PostTripFeedback(
        id=uuid.uuid4(),
        user_id=user_id,
        trip_id=str(uuid.uuid4()),
        destination="Istanbul",
        overall_rating=5,
        destination_rating=4,
        would_revisit=True,
    )
    db.add(feedback)
    db.commit()


def test_get_features_no_data(client: TestClient):
    with patch(
        "app.services.feature_builder._fetch_profile",
        new=AsyncMock(return_value=PROFILE_RESPONSE),
    ):
        resp = client.get(f"/api/v1/users/{TEST_USER_ID}/features")

    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == str(TEST_USER_ID)
    assert data["onboarding_completed"] is True
    assert data["budget_min_usd"] == 500.0
    assert data["budget_max_usd"] == 2000.0
    assert data["preferred_duration_days"] == 10
    assert data["activity_prefs_vector"] is not None
    assert len(data["activity_prefs_vector"]) == 10


def test_get_features_with_events_and_feedback(client: TestClient, db: Session):
    _add_events(db, TEST_USER_ID)
    _add_feedback(db, TEST_USER_ID)

    with patch(
        "app.services.feature_builder._fetch_profile",
        new=AsyncMock(return_value=PROFILE_RESPONSE),
    ):
        resp = client.get(f"/api/v1/users/{TEST_USER_ID}/features")

    assert resp.status_code == 200
    data = resp.json()
    assert data["session_count"] == 2
    assert "10" in (data["viewed_destination_ids"] or [])
    assert "10" in (data["clicked_destination_ids"] or [])
    assert data["completed_trips_count"] == 1
    assert data["avg_destination_rating"] == 4.0
    assert data["would_revisit_ratio"] == 1.0


def test_get_features_upserts_on_repeat_call(client: TestClient, db: Session):
    with patch(
        "app.services.feature_builder._fetch_profile",
        new=AsyncMock(return_value=PROFILE_RESPONSE),
    ):
        client.get(f"/api/v1/users/{TEST_USER_ID}/features")
        client.get(f"/api/v1/users/{TEST_USER_ID}/features")

    rows = db.query(UserFeatures).filter(UserFeatures.user_id == TEST_USER_ID).all()
    assert len(rows) == 1
    assert rows[0].feature_version == 2


def test_get_features_forbidden_for_other_user(client: TestClient):
    other_user_id = uuid.uuid4()
    resp = client.get(f"/api/v1/users/{other_user_id}/features")
    assert resp.status_code == 403


def test_activity_prefs_vector_weighting(client: TestClient):
    profile = {**PROFILE_RESPONSE, "vacation_preferences_ranked": ["beach", "culture"]}
    with patch(
        "app.services.feature_builder._fetch_profile",
        new=AsyncMock(return_value=profile),
    ):
        resp = client.get(f"/api/v1/users/{TEST_USER_ID}/features")

    data = resp.json()
    vec = data["activity_prefs_vector"]
    assert vec is not None
    # beach is index 0, weight = (5-0)/5 = 1.0
    assert vec[0] == pytest.approx(1.0)
    # culture is index 1, weight = (5-1)/5 = 0.8
    assert vec[1] == pytest.approx(0.8)
    # rest should be 0
    assert all(v == 0.0 for v in vec[2:])
