import json
import uuid
from datetime import date
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.schemas.llm_quality import (
    LLMCandidatePOI,
    LLMQualityReview,
    LLMReviewAction,
    LLMReviewAdjustment,
    LLMReviewIssue,
    LLMReviewSeverity,
    LLMReviewStatus,
)
from app.services.llm.providers import FakeProvider
from app.services.llm.quality_gate import LLMQualityGate
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
        "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS free_text_notes TEXT",
    ]:
        db.execute(text(statement))
    db.execute(
        text("""
            CREATE TABLE IF NOT EXISTS poi (
                id UUID PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                lat DOUBLE PRECISION,
                lng DOUBLE PRECISION,
                destination_id UUID NOT NULL
            )
        """)
    )
    db.execute(text("DELETE FROM poi WHERE destination_id = :destination_id"), {"destination_id": str(DEST_ID)})
    db.execute(text("DELETE FROM user_profiles WHERE user_id = :uid"), {"uid": str(TEST_USER_ID)})
    db.execute(
        text("""
            INSERT INTO user_profiles (
                user_id, onboarding_completed, vacation_preferences_ranked, typical_duration_days, free_text_notes
            ) VALUES (
                :uid, TRUE, '["culture", "food"]', 7, 'Prefer quiet places. Email user@example.com'
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


def _itinerary_payload(items: list[dict] | None = None) -> dict:
    return {
        "destination_id": str(DEST_ID),
        "duration_days": 3,
        "days": [
            {
                "day": 1,
                "day_number": 1,
                "theme": "culture",
                "places": items
                or [
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
                        "score": 1.0,
                    }
                ],
            }
        ],
        "activity_tags": ["culture"],
        "score_summary": {"total_pois": len(items or [1])},
    }


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
    data_service_call = next(call for call in post_mock.call_args_list if "params" in call.kwargs)
    params = data_service_call.kwargs["params"]
    assert ("preferred_activities", "culture") in params
    assert ("variant_count", 1) in params


def test_itinerary_quality_review_caution_and_notes_context(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    review = LLMQualityReview(
        status=LLMReviewStatus.caution,
        confidence=0.82,
        provider="yandex",
        model="qwen3.6-35b-a3b/latest",
        prompt_version="itinerary_quality_v1",
        issues=[
            LLMReviewIssue(
                code="closed_poi",
                severity=LLMReviewSeverity.warning,
                message="A POI may be closed at the planned visit time.",
            )
        ],
        suggested_adjustments=[
            LLMReviewAdjustment(action=LLMReviewAction.note, target_day=1, reason="Warn user about opening hours.")
        ],
        user_summary_ru="Проверьте часы работы музея.",
    )

    class FakeGate:
        def review_itinerary(self, **kwargs):
            context = kwargs["context"]
            assert "user@example.com" not in str(context)
            assert context["trip"]["trip_notes"]["text"] == "Need slow mornings."
            assert "email_masked" in context["user_profile"]["free_text_notes"]["flags"]
            assert context["variant"]["derived_metrics"]["total_visit_minutes"] == 120
            return review

    response = Mock()
    response.json.return_value = _itinerary_payload(
        [
            {
                "id": str(POI_ID),
                "name": "Closed museum",
                "category": "museum",
                "opening_status": "closed",
                "arrival_time": "09:30",
                "departure_time": "11:30",
                "travel_from_previous_minutes": 0,
                "visit_duration_minutes": 120,
                "score": 1.0,
            }
        ]
    )
    response.raise_for_status.return_value = None
    monkeypatch.setattr(settings, "LLM_QUALITY_ENABLED", True)
    monkeypatch.setattr("app.routers.itinerary.httpx.post", Mock(return_value=response))
    monkeypatch.setattr(
        "app.routers.itinerary._destination_info", lambda _destination_id: {"display_name": "Test City"}
    )
    monkeypatch.setattr("app.routers.itinerary.LLMQualityGate", lambda: FakeGate())

    resp = client.post("/api/v1/itinerary", json=_payload(trip_notes="Need slow mornings."))

    assert resp.status_code == 200
    data = resp.json()
    assert data["quality_review"]["status"] == "caution"
    assert data["days"][0]["quality_review"]["issues"][0]["code"] == "closed_poi"
    assert data["score_summary"]["llm_quality_review"]["status"] == "caution"


def test_itinerary_quality_unknown_remove_is_ignored(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    unknown_id = uuid.UUID("99999999-9999-9999-9999-999999999999")
    review = LLMQualityReview(
        status=LLMReviewStatus.caution,
        confidence=0.72,
        provider="yandex",
        model="qwen3.6-35b-a3b/latest",
        prompt_version="itinerary_quality_v1",
        issues=[
            LLMReviewIssue(
                code="overloaded_day",
                severity=LLMReviewSeverity.warning,
                message="Day is overloaded.",
            )
        ],
        suggested_adjustments=[
            LLMReviewAdjustment(action=LLMReviewAction.remove, target_id=unknown_id, reason="Unknown item.")
        ],
    )

    class FakeGate:
        def review_itinerary(self, **_kwargs):
            return review

    response = Mock()
    response.json.return_value = _itinerary_payload()
    response.raise_for_status.return_value = None
    monkeypatch.setattr(settings, "LLM_QUALITY_ENABLED", True)
    monkeypatch.setattr("app.routers.itinerary.httpx.post", Mock(return_value=response))
    monkeypatch.setattr("app.routers.itinerary._destination_info", lambda _destination_id: None)
    monkeypatch.setattr("app.routers.itinerary.LLMQualityGate", lambda: FakeGate())

    resp = client.post("/api/v1/itinerary", json=_payload())

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["days"][0]["places"]) == 1
    assert data["score_summary"]["llm_quality_ignored_adjustments"] == [
        {"action": "remove", "target_id": str(unknown_id), "reason": "unknown_item_id"}
    ]


def test_itinerary_quality_resolved_remove_hides_stale_warning(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    review = LLMQualityReview(
        status=LLMReviewStatus.caution,
        confidence=0.86,
        provider="yandex",
        model="qwen3.6-35b-a3b/latest",
        prompt_version="itinerary_quality_v1",
        issues=[
            LLMReviewIssue(
                code="wrong_city_poi",
                severity=LLMReviewSeverity.warning,
                message="This POI appears to belong to a different city.",
                item_id=POI_ID,
            )
        ],
        suggested_adjustments=[
            LLMReviewAdjustment(action=LLMReviewAction.remove, target_id=POI_ID, reason="Remove wrong-city POI."),
            LLMReviewAdjustment(action=LLMReviewAction.note, reason="Explain the correction to the user."),
        ],
    )

    class FakeGate:
        def review_itinerary(self, **_kwargs):
            return review

    response = Mock()
    response.json.return_value = _itinerary_payload(
        [
            {
                "id": str(POI_ID),
                "name": "Statue de David",
                "category": "culture",
                "arrival_time": "09:30",
                "departure_time": "11:30",
                "travel_from_previous_minutes": 0,
                "visit_duration_minutes": 120,
                "score": 1.0,
            },
            {
                "id": str(uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")),
                "name": "Museum",
                "category": "culture",
                "arrival_time": "12:00",
                "departure_time": "13:00",
                "travel_from_previous_minutes": 20,
                "visit_duration_minutes": 60,
                "score": 0.9,
            },
        ]
    )
    response.raise_for_status.return_value = None
    monkeypatch.setattr(settings, "LLM_QUALITY_ENABLED", True)
    monkeypatch.setattr("app.routers.itinerary.httpx.post", Mock(return_value=response))
    monkeypatch.setattr("app.routers.itinerary._destination_info", lambda _destination_id: None)
    monkeypatch.setattr("app.routers.itinerary.LLMQualityGate", lambda: FakeGate())

    resp = client.post("/api/v1/itinerary", json=_payload())

    assert resp.status_code == 200
    data = resp.json()
    assert [place["name"] for place in data["days"][0]["places"]] == ["Museum"]
    assert data["quality_review"]["status"] == "ok"
    assert data["quality_review"]["issues"] == []
    assert data["days"][0]["quality_review"] is None


def test_itinerary_quality_fail_open_returns_itinerary_without_500(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    response = Mock()
    response.json.return_value = _itinerary_payload()
    response.raise_for_status.return_value = None
    monkeypatch.setattr(settings, "LLM_QUALITY_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_FAIL_OPEN", True)
    monkeypatch.setattr("app.routers.itinerary.httpx.post", Mock(return_value=response))
    monkeypatch.setattr("app.routers.itinerary._destination_info", lambda _destination_id: None)
    monkeypatch.setattr(
        "app.routers.itinerary.LLMQualityGate", lambda: LLMQualityGate(provider=FakeProvider(responses=["not json"]))
    )

    resp = client.post("/api/v1/itinerary", json=_payload())

    assert resp.status_code == 200
    data = resp.json()
    assert data["days"][0]["places"][0]["name"] == "Museum"
    assert data["quality_review"]["status"] == "skipped"


def test_rejected_first_variant_is_ordered_after_alternatives(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    review = LLMQualityReview(
        status=LLMReviewStatus.reject,
        confidence=0.9,
        provider="yandex",
        model="qwen3.6-35b-a3b/latest",
        prompt_version="itinerary_quality_v1",
        issues=[
            LLMReviewIssue(
                code="missing_user_preference",
                severity=LLMReviewSeverity.critical,
                message="First variant misses user preferences.",
                evidence=["No preferred categories."],
            )
        ],
        suggested_adjustments=[],
    )

    class FakeGate:
        def review_itinerary(self, **_kwargs):
            return review

    first = _itinerary_payload()
    first["variant_index"] = 0
    first["variant_seed"] = 101
    first["route_signature"] = "rejected"
    second = _itinerary_payload()
    second["variant_index"] = 1
    second["variant_seed"] = 102
    second["route_signature"] = "alternative"
    response = Mock()
    response.json.return_value = {**first, "variants": [first, second]}
    response.raise_for_status.return_value = None
    monkeypatch.setattr(settings, "LLM_QUALITY_ENABLED", True)
    monkeypatch.setattr("app.routers.itinerary.httpx.post", Mock(return_value=response))
    monkeypatch.setattr("app.routers.itinerary._destination_info", lambda _destination_id: None)
    monkeypatch.setattr("app.routers.itinerary.LLMQualityGate", lambda: FakeGate())

    resp = client.post("/api/v1/itinerary", json=_payload(variant_count=2))

    assert resp.status_code == 200
    data = resp.json()
    assert data["route_signature"] == "alternative"
    assert [variant["route_signature"] for variant in data["variants"]] == ["alternative", "rejected"]


def test_itinerary_candidate_poi_is_added_as_external_candidate(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
):
    candidate = LLMCandidatePOI(
        name="Quiet tea house",
        category="food",
        lat=55.751,
        lng=37.621,
        source_url="https://example.com/tea-house",
        suggested_visit_duration_minutes=60,
        confidence=0.82,
        reason="User asked for quiet food places.",
    )
    review = LLMQualityReview(
        status=LLMReviewStatus.caution,
        confidence=0.8,
        provider="yandex",
        model="qwen3.6-35b-a3b/latest",
        prompt_version="itinerary_quality_v1",
        issues=[
            LLMReviewIssue(
                code="missing_user_interest",
                severity=LLMReviewSeverity.warning,
                message="The itinerary misses quiet food places from notes.",
            )
        ],
        suggested_adjustments=[
            LLMReviewAdjustment(
                action=LLMReviewAction.add_candidate_poi,
                target_day=1,
                target_order=1,
                reason="Add a quiet food stop.",
                candidate_poi=candidate,
            )
        ],
    )

    class FakeGate:
        def review_itinerary(self, **_kwargs):
            return review

    response = Mock()
    response.json.return_value = _itinerary_payload()
    response.raise_for_status.return_value = None
    monkeypatch.setattr(settings, "LLM_QUALITY_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_CANDIDATE_POI_ENABLED", True)
    monkeypatch.setattr("app.routers.itinerary.httpx.post", Mock(return_value=response))
    monkeypatch.setattr("app.routers.itinerary._destination_info", lambda _destination_id: None)
    monkeypatch.setattr("app.routers.itinerary.LLMQualityGate", lambda: FakeGate())

    resp = client.post("/api/v1/itinerary", json=_payload())

    assert resp.status_code == 200
    data = resp.json()
    places = data["days"][0]["places"]
    assert [place["name"] for place in places] == ["Museum", "Quiet tea house"]
    assert places[1]["external_candidate_source"] == "llm_candidate_poi"
    assert data["candidate_poi"][0]["name"] == "Quiet tea house"
    assert data["score_summary"]["llm_candidate_poi"][0]["status"] == "external_candidate"

    row = db.execute(text("SELECT status, name FROM llm_candidate_poi WHERE name = 'Quiet tea house'")).fetchone()
    assert row is not None
    assert row._mapping["status"] == "pending"


def test_itinerary_duplicate_candidate_poi_is_ignored(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch):
    db.execute(
        text("""
            INSERT INTO poi (id, name, category, lat, lng, destination_id)
            VALUES (:id, 'Quiet tea house', 'food', 55.751, 37.621, :destination_id)
        """),
        {"id": str(uuid.uuid4()), "destination_id": str(DEST_ID)},
    )
    db.commit()
    review = LLMQualityReview(
        status=LLMReviewStatus.caution,
        confidence=0.8,
        provider="yandex",
        model="qwen3.6-35b-a3b/latest",
        prompt_version="itinerary_quality_v1",
        issues=[
            LLMReviewIssue(
                code="repetitive_route",
                severity=LLMReviewSeverity.warning,
                message="Route is repetitive.",
            )
        ],
        suggested_adjustments=[
            LLMReviewAdjustment(
                action=LLMReviewAction.add_candidate_poi,
                reason="Duplicate candidate.",
                candidate_poi=LLMCandidatePOI(
                    name="Quiet tea house",
                    category="food",
                    lat=55.751,
                    lng=37.621,
                    source_url="https://example.com/tea-house",
                    confidence=0.82,
                    reason="Looks relevant.",
                ),
            )
        ],
    )

    class FakeGate:
        def review_itinerary(self, **_kwargs):
            return review

    response = Mock()
    response.json.return_value = _itinerary_payload()
    response.raise_for_status.return_value = None
    monkeypatch.setattr(settings, "LLM_QUALITY_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_CANDIDATE_POI_ENABLED", True)
    monkeypatch.setattr("app.routers.itinerary.httpx.post", Mock(return_value=response))
    monkeypatch.setattr("app.routers.itinerary._destination_info", lambda _destination_id: None)
    monkeypatch.setattr("app.routers.itinerary.LLMQualityGate", lambda: FakeGate())

    resp = client.post("/api/v1/itinerary", json=_payload())

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["days"][0]["places"]) == 1
    ignored = data["score_summary"]["llm_quality_ignored_adjustments"][0]
    assert ignored["reason"] == "duplicate_candidate"
    row = db.execute(text("SELECT status FROM llm_candidate_poi WHERE name = 'Quiet tea house'")).fetchone()
    assert row is not None
    assert row._mapping["status"] == "rejected"


def test_generate_itinerary_validates_request(client: TestClient):
    resp = client.post("/api/v1/itinerary", json={"duration_days": 0, "start_date": "2026-06-10"})
    assert resp.status_code == 422


def test_generate_itinerary_no_template_response(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "LLM_EXTERNAL_ROUTE_ENABLED", False)
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


def test_no_feasible_internal_route_can_return_external_draft(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    response = Mock()
    response.json.return_value = {
        "destination_id": str(DEST_ID),
        "duration_days": 3,
        "error": "No feasible itinerary for the selected trip parameters.",
        "variants": [],
    }
    response.raise_for_status.return_value = None
    external = _itinerary_payload()
    external["source"] = "llm-external-draft"
    external["score_summary"] = {"external_route_used": True, "catalog_mutation_allowed": False}
    monkeypatch.setattr("app.routers.itinerary.httpx.post", Mock(return_value=response))
    monkeypatch.setattr(
        "app.routers.itinerary._destination_info", lambda _destination_id: {"display_name": "Test City"}
    )

    def fake_external_route(**_kwargs):
        from app.schemas.itinerary import ItineraryGenerateResponse

        return ItineraryGenerateResponse.model_validate(external)

    monkeypatch.setattr("app.routers.itinerary.generate_external_route", fake_external_route)

    resp = client.post("/api/v1/itinerary", json=_payload())

    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "llm-external-draft"
    assert data["score_summary"]["external_route_used"] is True


def test_manual_destination_external_route_uses_llm_specific_pois(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    external_payload = {
        "variants": [
            {
                "variant_index": 0,
                "title": "Roman Tarragona",
                "days": [
                    {
                        "day_number": 1,
                        "theme": "history",
                        "places": [
                            {
                                "name": "Amfiteatre de Tarragona",
                                "category": "history",
                                "lat": 41.1143,
                                "lng": 1.2595,
                                "address": "Parc de l'Amfiteatre",
                                "arrival_time": "09:30",
                                "departure_time": "11:00",
                                "visit_duration_minutes": 90,
                                "travel_from_previous_minutes": 0,
                                "reason": "Major Roman landmark in Tarragona.",
                                "confidence": 0.92,
                            },
                            {
                                "name": "Circ Roma de Tarragona",
                                "category": "history",
                                "lat": 41.1152,
                                "lng": 1.2564,
                                "address": "Rambla Vella",
                                "arrival_time": "11:20",
                                "departure_time": "12:40",
                                "visit_duration_minutes": 80,
                                "travel_from_previous_minutes": 15,
                                "reason": "Nearby Roman circus keeps the route compact.",
                                "confidence": 0.9,
                            },
                        ],
                    }
                ],
            },
            {
                "variant_index": 1,
                "title": "Old city and sea",
                "days": [
                    {
                        "day_number": 1,
                        "theme": "culture",
                        "places": [
                            {
                                "name": "Catedral de Tarragona",
                                "category": "culture",
                                "lat": 41.1182,
                                "lng": 1.2582,
                                "address": "Pla de la Seu",
                                "arrival_time": "09:30",
                                "departure_time": "11:00",
                                "visit_duration_minutes": 90,
                                "travel_from_previous_minutes": 0,
                                "reason": "Core old-town landmark.",
                                "confidence": 0.91,
                            },
                            {
                                "name": "Balco del Mediterrani",
                                "category": "viewpoint",
                                "lat": 41.1134,
                                "lng": 1.2566,
                                "address": "Rambla Nova",
                                "arrival_time": "11:25",
                                "departure_time": "12:10",
                                "visit_duration_minutes": 45,
                                "travel_from_previous_minutes": 15,
                                "reason": "Logical scenic stop after the old town.",
                                "confidence": 0.88,
                            },
                        ],
                    }
                ],
            },
            {
                "variant_index": 2,
                "title": "Generic route must be rejected",
                "days": [
                    {
                        "day_number": 1,
                        "theme": "generic",
                        "places": [
                            {
                                "name": "Таррагона: центральный район",
                                "category": "walk",
                                "lat": 41.1189,
                                "lng": 1.2445,
                                "address": None,
                                "arrival_time": "09:30",
                                "departure_time": "11:00",
                                "visit_duration_minutes": 90,
                                "travel_from_previous_minutes": 0,
                                "reason": "Placeholder.",
                                "confidence": 0.3,
                            }
                        ],
                    }
                ],
            },
        ]
    }
    monkeypatch.setattr(settings, "LLM_EXTERNAL_ROUTE_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_QUALITY_ENABLED", False)
    monkeypatch.setattr(
        "app.services.llm.external_route.get_provider",
        lambda: FakeProvider(responses=[json.dumps(external_payload)]),
    )

    resp = client.post(
        "/api/v1/itinerary",
        json={
            "destination_text": "Таррагона",
            "duration_days": 1,
            "start_date": "2026-06-10",
            "variant_count": 3,
            "allow_external_route": True,
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "llm-external-draft"
    assert len(data["variants"]) == 2
    assert data["variants"][0]["days"][0]["places"][0]["name"] == "Amfiteatre de Tarragona"
    assert all(place["lat"] and place["lng"] for place in data["variants"][0]["days"][0]["places"])
    assert "центральный район" not in json.dumps(data, ensure_ascii=False)


def test_generate_itinerary_data_service_failure(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "LLM_EXTERNAL_ROUTE_ENABLED", False)
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
