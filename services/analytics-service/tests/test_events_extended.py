import uuid
from typing import get_args

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user_event import UserEvent
from app.schemas.events import EventType


def test_ingest_empty_batch_rejected(client: TestClient):
    # Schema enforces min_length=1 on events list
    resp = client.post("/api/v1/events", json={"events": []})
    assert resp.status_code == 422


def test_ingest_event_without_entity(client: TestClient, db: Session):
    resp = client.post(
        "/api/v1/events",
        json={"events": [{"session_id": str(uuid.uuid4()), "event_type": "trip_created"}]},
    )
    assert resp.status_code == 202
    row = db.query(UserEvent).first()
    assert row is not None
    assert row.entity_type is None
    assert row.entity_id is None


def test_ingest_event_stores_user_id(client: TestClient, db: Session):
    resp = client.post(
        "/api/v1/events",
        json={"events": [{"session_id": str(uuid.uuid4()), "event_type": "onboarding_completed"}]},
    )
    assert resp.status_code == 202
    row = db.query(UserEvent).first()
    assert row is not None
    assert row.user_id is not None


def test_ingest_event_with_context(client: TestClient, db: Session):
    ctx = {"score": 0.92, "rank": 1, "model": "content-v1"}
    resp = client.post(
        "/api/v1/events",
        json={
            "events": [
                {
                    "session_id": str(uuid.uuid4()),
                    "event_type": "recommendation_clicked",
                    "entity_type": "destination",
                    "entity_id": "99",
                    "context": ctx,
                }
            ]
        },
    )
    assert resp.status_code == 202
    row = db.query(UserEvent).first()
    assert row is not None, "UserEvent was not created"
    assert row.context == ctx


def test_ingest_all_event_types(client: TestClient, db: Session):
    valid_types = get_args(EventType)
    events = [{"session_id": str(uuid.uuid4()), "event_type": t} for t in valid_types]
    resp = client.post("/api/v1/events", json={"events": events})
    assert resp.status_code == 202
    assert resp.json()["accepted"] == len(valid_types)


def test_multiple_sessions_stored_separately(client: TestClient, db: Session):
    session_a = str(uuid.uuid4())
    session_b = str(uuid.uuid4())
    resp = client.post(
        "/api/v1/events",
        json={
            "events": [
                {"session_id": session_a, "event_type": "recommendation_shown", "entity_id": "1"},
                {"session_id": session_b, "event_type": "recommendation_shown", "entity_id": "2"},
            ]
        },
    )
    assert resp.status_code == 202
    rows = db.query(UserEvent).all()
    sessions = {str(r.session_id) for r in rows}
    assert sessions == {session_a, session_b}
