import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.post_trip_feedback import PostTripFeedback


def _feedback_payload(trip_id: str | None = None) -> dict:
    return {
        "trip_id": trip_id or str(uuid.uuid4()),
        "destination": "Istanbul",
        "overall_rating": 5,
        "destination_rating": 4,
        "value_rating": 5,
        "actual_total_cost": 1200.0,
        "actual_currency": "USD",
        "would_revisit": True,
        "free_text": "Great trip!",
    }


def test_submit_feedback(client: TestClient, db: Session):
    payload = _feedback_payload()
    resp = client.post("/api/v1/feedback/post-trip", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["destination"] == "Istanbul"
    assert data["overall_rating"] == 5
    assert data["would_revisit"] is True

    row = db.query(PostTripFeedback).first()
    assert row is not None
    assert row.trip_id == payload["trip_id"]


def test_submit_feedback_duplicate_rejected(client: TestClient):
    payload = _feedback_payload()
    client.post("/api/v1/feedback/post-trip", json=payload)
    resp = client.post("/api/v1/feedback/post-trip", json=payload)
    assert resp.status_code == 409


def test_get_feedback(client: TestClient):
    payload = _feedback_payload()
    client.post("/api/v1/feedback/post-trip", json=payload)

    resp = client.get(f"/api/v1/feedback/post-trip/{payload['trip_id']}")
    assert resp.status_code == 200
    assert resp.json()["trip_id"] == payload["trip_id"]


def test_get_feedback_not_found(client: TestClient):
    resp = client.get(f"/api/v1/feedback/post-trip/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_update_feedback(client: TestClient):
    payload = _feedback_payload()
    client.post("/api/v1/feedback/post-trip", json=payload)

    resp = client.put(
        f"/api/v1/feedback/post-trip/{payload['trip_id']}",
        json={"overall_rating": 3, "free_text": "Changed my mind"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_rating"] == 3
    assert data["free_text"] == "Changed my mind"


def test_delete_feedback(client: TestClient, db: Session):
    payload = _feedback_payload()
    client.post("/api/v1/feedback/post-trip", json=payload)
    assert db.query(PostTripFeedback).count() == 1

    resp = client.delete(f"/api/v1/feedback/post-trip/{payload['trip_id']}")
    assert resp.status_code == 204
    assert db.query(PostTripFeedback).count() == 0


def test_pending_feedback(client: TestClient):
    trip_id_1 = str(uuid.uuid4())
    trip_id_2 = str(uuid.uuid4())

    client.post("/api/v1/feedback/post-trip", json=_feedback_payload(trip_id_1))

    resp = client.get(
        "/api/v1/feedback/pending",
        params=[
            ("trip_id", trip_id_1),
            ("trip_id", trip_id_2),
            ("destination", "Istanbul"),
            ("destination", "Paris"),
        ],
    )
    assert resp.status_code == 200
    pending = resp.json()
    assert len(pending) == 1
    assert pending[0]["trip_id"] == trip_id_2
