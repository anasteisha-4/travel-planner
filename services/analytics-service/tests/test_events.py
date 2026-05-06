import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user_event import UserEvent


def test_ingest_single_event(client: TestClient, db: Session):
    session_id = str(uuid.uuid4())
    resp = client.post(
        "/api/v1/events",
        json={
            "events": [
                {
                    "session_id": session_id,
                    "event_type": "recommendation_shown",
                    "entity_type": "destination",
                    "entity_id": "42",
                    "context": {"score": 0.87},
                }
            ]
        },
    )
    assert resp.status_code == 202
    assert resp.json()["accepted"] == 1

    rows = db.query(UserEvent).all()
    assert len(rows) == 1
    assert rows[0].event_type == "recommendation_shown"
    assert rows[0].entity_id == "42"


def test_ingest_batch_events(client: TestClient, db: Session):
    session_id = str(uuid.uuid4())
    event_types = [
        "recommendation_impression",
        "recommendation_clicked",
        "destination_detail_opened",
        "budget_prediction_viewed",
        "trip_created",
    ]
    events = [
        {"session_id": session_id, "event_type": event_types[i], "entity_type": "destination", "entity_id": str(i)}
        for i in range(5)
    ]
    resp = client.post("/api/v1/events", json={"events": events})
    assert resp.status_code == 202
    assert resp.json()["accepted"] == 5
    assert db.query(UserEvent).count() == 5


def test_ingest_event_with_occurred_at(client: TestClient, db: Session):
    session_id = str(uuid.uuid4())
    resp = client.post(
        "/api/v1/events",
        json={
            "events": [
                {
                    "session_id": session_id,
                    "event_type": "trip_created",
                    "occurred_at": "2025-01-15T10:30:00Z",
                }
            ]
        },
    )
    assert resp.status_code == 202
    row = db.query(UserEvent).first()
    assert row is not None
    assert row.event_type == "trip_created"
