import uuid
from datetime import date
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from tests.conftest import TEST_USER_ID

DEST_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
POI_ID = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")


@pytest.fixture(autouse=True)
def seed_profile(db: Session, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "DATA_SERVICE_SECRET", "test-secret")
    monkeypatch.setattr(settings, "INTERNAL_API_SECRET", "test-secret")
    monkeypatch.setattr(settings, "DATA_SERVICE_URL", "http://data-service:8000")
    db.execute(
        text("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id UUID PRIMARY KEY,
                onboarding_completed BOOLEAN DEFAULT TRUE,
                vacation_preferences_ranked JSONB,
                budget_min_usd NUMERIC,
                budget_max_usd NUMERIC,
                typical_duration_days INTEGER,
                typical_duration TEXT,
                risk_tolerance TEXT,
                visa_tolerance TEXT,
                language_comfort JSONB,
                crowd_preference TEXT,
                climate_preferences JSONB,
                liked_destination_ids JSONB,
                origin_city_name TEXT,
                origin_lat NUMERIC,
                origin_lng NUMERIC
            )
        """)
    )
    for statement in [
        "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS vacation_preferences_ranked JSONB",
        "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS typical_duration_days INTEGER",
    ]:
        db.execute(text(statement))
    db.execute(text("DELETE FROM user_profiles WHERE user_id = :uid"), {"uid": str(TEST_USER_ID)})
    db.execute(
        text("""
            INSERT INTO user_profiles (
                user_id, onboarding_completed, vacation_preferences_ranked, typical_duration_days
            ) VALUES (
                :uid, TRUE, '["culture", "food"]', 7
            )
        """),
        {"uid": str(TEST_USER_ID)},
    )
    db.commit()
    yield
    db.execute(text("DELETE FROM user_profiles WHERE user_id = :uid"), {"uid": str(TEST_USER_ID)})
    db.commit()


def _payload(**overrides) -> dict:
    base = {
        "destination_id": str(DEST_ID),
        "duration_days": 3,
        "start_date": date(2026, 6, 10).isoformat(),
    }
    base.update(overrides)
    return base


def test_generate_itinerary_success(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    response = Mock()
    response.json.return_value = {
        "destination_id": str(DEST_ID),
        "duration_days": 3,
        "days": [
            {
                "day": 1,
                "theme": "culture",
                "places": [
                    {
                        "id": str(POI_ID),
                        "name": "Museum",
                        "category": "culture",
                        "lat": 55.75,
                        "lng": 37.62,
                        "address": "Main street",
                        "opening_hours": "Mo-Su 10:00-18:00",
                        "is_open_at_midday": True,
                        "opening_status": "open",
                        "arrival_time": "09:30",
                        "departure_time": "11:30",
                        "travel_from_previous_minutes": 0,
                        "visit_duration_minutes": 120,
                    }
                ],
            }
        ],
        "activity_tags": ["culture"],
    }
    response.raise_for_status.return_value = None
    post_mock = Mock(return_value=response)
    monkeypatch.setattr("app.routers.itinerary.httpx.post", post_mock)

    resp = client.post("/api/v1/itinerary", json=_payload())

    assert resp.status_code == 200
    data = resp.json()
    assert data["destination_id"] == str(DEST_ID)
    assert data["source"] == "optimized-heuristic"
    assert data["has_template"] is True
    assert data["days"][0]["places"][0]["name"] == "Museum"
    assert data["days"][0]["places"][0]["arrival_time"] == "09:30"
    params = post_mock.call_args.kwargs["params"]
    assert ("preferred_activities", "culture") in params
    assert ("variant_count", 1) in params


def test_generate_itinerary_validates_request(client: TestClient):
    resp = client.post("/api/v1/itinerary", json={"duration_days": 0, "start_date": "2026-06-10"})
    assert resp.status_code == 422


def test_generate_itinerary_no_template_response(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    response = Mock()
    response.json.return_value = {
        "destination_id": str(DEST_ID),
        "error": "No itinerary template available for this destination.",
    }
    response.raise_for_status.return_value = None
    monkeypatch.setattr("app.routers.itinerary.httpx.post", Mock(return_value=response))

    resp = client.post("/api/v1/itinerary", json=_payload())

    assert resp.status_code == 200
    data = resp.json()
    assert data["has_template"] is False
    assert data["days"] == []
    assert data["message"] == "No itinerary template available for this destination."


def test_generate_itinerary_data_service_failure(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "app.routers.itinerary.httpx.post",
        Mock(side_effect=httpx.ConnectError("connection failed")),
    )

    resp = client.post("/api/v1/itinerary", json=_payload())

    assert resp.status_code == 503
    assert resp.json()["error"] == "ITINERARY_UNAVAILABLE"


def test_generate_itinerary_requires_internal_secret(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "DATA_SERVICE_SECRET", "")
    monkeypatch.setattr(settings, "INTERNAL_API_SECRET", "")

    resp = client.post("/api/v1/itinerary", json=_payload())

    assert resp.status_code == 503
    assert resp.json()["error"] == "ITINERARY_UNAVAILABLE"
