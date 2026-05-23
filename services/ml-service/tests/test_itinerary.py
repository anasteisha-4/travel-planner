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
from app.schemas.itinerary import ItineraryGenerateRequest
from app.schemas.llm_quality import (
    LLMCandidatePOI,
    LLMQualityReview,
    LLMReviewAction,
    LLMReviewAdjustment,
    LLMReviewIssue,
    LLMReviewSeverity,
    LLMReviewStatus,
)
from app.services.llm.external_route import _normalize_external_variants, _should_reject_unrepaired_coordinate
from app.services.llm.prompts import compact_json
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
                item_id=POI_ID,
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
    monkeypatch.setattr(settings, "LLM_ITINERARY_REVIEW_VARIANTS", 3)
    monkeypatch.setattr("app.routers.itinerary.httpx.post", Mock(return_value=response))
    monkeypatch.setattr(
        "app.routers.itinerary._destination_info", lambda _destination_id: {"display_name": "Test City"}
    )
    monkeypatch.setattr("app.routers.itinerary.LLMQualityGate", lambda: FakeGate())

    resp = client.post("/api/v1/itinerary", json=_payload(trip_notes="Need slow mornings."))

    assert resp.status_code == 200
    data = resp.json()
    assert data["quality_review"]["status"] == "ok"
    assert data["days"][0]["places"] == []
    assert data["score_summary"]["llm_quality_review"]["status"] == "ok"
    assert data["score_summary"]["llm_quality_applied_adjustments"] == [
        {"action": "remove", "target_id": str(POI_ID), "reason": "warning_issue"}
    ]


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
    rejected_review = LLMQualityReview(
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
    ok_review = LLMQualityReview(
        status=LLMReviewStatus.ok,
        confidence=0.9,
        provider="yandex",
        model="qwen3.6-35b-a3b/latest",
        prompt_version="itinerary_quality_v1",
        issues=[],
        suggested_adjustments=[],
    )

    class FakeGate:
        def review_itinerary(self, **kwargs):
            return rejected_review if kwargs["itinerary_id"] == "rejected" else ok_review

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
    assert [variant["quality_review"]["status"] for variant in data["variants"]] == ["ok", "reject"]


def test_itinerary_quality_reviews_all_default_variants(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    reviewed_ids: list[str] = []

    class FakeGate:
        def review_itinerary(self, **kwargs):
            reviewed_ids.append(kwargs["itinerary_id"])
            return LLMQualityReview(
                status=LLMReviewStatus.ok,
                confidence=0.9,
                provider="yandex",
                model="qwen3.6-35b-a3b/latest",
                prompt_version="itinerary_quality_v1",
                issues=[],
                suggested_adjustments=[],
            )

    variants = []
    for index in range(3):
        variant = _itinerary_payload()
        variant["variant_index"] = index
        variant["variant_seed"] = 101 + index
        variant["route_signature"] = f"variant-{index}"
        variants.append(variant)
    response = Mock()
    response.json.return_value = {**variants[0], "variants": variants}
    response.raise_for_status.return_value = None
    monkeypatch.setattr(settings, "LLM_QUALITY_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_ITINERARY_REVIEW_VARIANTS", 3)
    monkeypatch.setattr("app.routers.itinerary.httpx.post", Mock(return_value=response))
    monkeypatch.setattr("app.routers.itinerary._destination_info", lambda _destination_id: None)
    monkeypatch.setattr("app.routers.itinerary.LLMQualityGate", lambda: FakeGate())

    resp = client.post("/api/v1/itinerary", json=_payload(variant_count=3))

    assert resp.status_code == 200
    data = resp.json()
    assert reviewed_ids == ["variant-0", "variant-1", "variant-2"]
    assert [variant["quality_review"]["status"] for variant in data["variants"]] == ["ok", "ok", "ok"]


def test_rejected_catalog_variants_keep_catalog_variants_without_external_replacement(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    reject_review = LLMQualityReview(
        status=LLMReviewStatus.reject,
        confidence=0.9,
        provider="yandex",
        model="qwen3.6-35b-a3b/latest",
        prompt_version="itinerary_quality_v1",
        issues=[
            LLMReviewIssue(
                code="wrong_city_route",
                severity=LLMReviewSeverity.critical,
                message="Route should be regenerated externally.",
            )
        ],
        suggested_adjustments=[
            LLMReviewAdjustment(action=LLMReviewAction.generate_external_route, reason="Use external route.")
        ],
    )

    class FakeGate:
        def review_itinerary(self, **_kwargs):
            return reject_review

    variants = []
    for index in range(3):
        variant = _itinerary_payload()
        variant["variant_index"] = index
        variant["variant_seed"] = 101 + index
        variant["route_signature"] = f"variant-{index}"
        variants.append(variant)
    response = Mock()
    response.json.return_value = {**variants[0], "variants": variants}
    response.raise_for_status.return_value = None
    external = _itinerary_payload()
    external["source"] = "llm-external-draft"
    external["model_version"] = "llm-external-route:qwen3.6-35b-a3b/latest"
    external["route_signature"] = "external-single"
    calls = 0

    def fake_external_route(**_kwargs):
        nonlocal calls
        calls += 1
        from app.schemas.itinerary import ItineraryGenerateResponse

        return ItineraryGenerateResponse.model_validate(external)

    monkeypatch.setattr(settings, "LLM_QUALITY_ENABLED", True)
    monkeypatch.setattr("app.routers.itinerary.httpx.post", Mock(return_value=response))
    monkeypatch.setattr(
        "app.routers.itinerary._destination_info", lambda _destination_id: {"display_name": "Test City"}
    )
    monkeypatch.setattr("app.routers.itinerary.LLMQualityGate", lambda: FakeGate())
    monkeypatch.setattr("app.routers.itinerary.generate_external_route", fake_external_route)

    resp = client.post("/api/v1/itinerary", json=_payload(variant_count=3))

    assert resp.status_code == 200
    data = resp.json()
    assert calls == 0
    assert data["source"] == "optimized-heuristic"
    assert [variant["route_signature"] for variant in data["variants"]] == ["variant-0", "variant-1", "variant-2"]


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
    assert places[1]["arrival_time"] == "11:50"
    assert places[1]["departure_time"] == "12:50"
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

    def fake_external_route(**kwargs):
        from app.schemas.itinerary import ItineraryGenerateResponse

        assert kwargs["request"].allow_external_route is True
        assert kwargs["trigger"] == "data_service_no_feasible"
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
                            {
                                "name": "Catedral de Tarragona",
                                "category": "culture",
                                "lat": 41.1182,
                                "lng": 1.2582,
                                "address": "Pla de la Seu",
                                "arrival_time": "13:10",
                                "departure_time": "14:20",
                                "visit_duration_minutes": 70,
                                "travel_from_previous_minutes": 20,
                                "reason": "Historic landmark within the old town route.",
                                "confidence": 0.88,
                            },
                            {
                                "name": "Balco del Mediterrani",
                                "category": "viewpoint",
                                "lat": 41.1134,
                                "lng": 1.2566,
                                "address": "Rambla Nova",
                                "arrival_time": "14:45",
                                "departure_time": "15:30",
                                "visit_duration_minutes": 45,
                                "travel_from_previous_minutes": 15,
                                "reason": "Scenic finish near the historic center.",
                                "confidence": 0.86,
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
                            {
                                "name": "Mercat Central de Tarragona",
                                "category": "food",
                                "lat": 41.1167,
                                "lng": 1.2476,
                                "address": "Placa Corsini",
                                "arrival_time": "12:35",
                                "departure_time": "13:35",
                                "visit_duration_minutes": 60,
                                "travel_from_previous_minutes": 20,
                                "reason": "Local food stop.",
                                "confidence": 0.84,
                            },
                            {
                                "name": "Passeig Arqueologic",
                                "category": "history",
                                "lat": 41.119,
                                "lng": 1.255,
                                "address": "Muralles Romanes",
                                "arrival_time": "14:00",
                                "departure_time": "15:10",
                                "visit_duration_minutes": 70,
                                "travel_from_previous_minutes": 15,
                                "reason": "Roman walls complete the cultural route.",
                                "confidence": 0.86,
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
    monkeypatch.setattr(settings, "LLM_EXTERNAL_ROUTE_COORDINATE_REPAIR_ENABLED", False)
    monkeypatch.setattr(settings, "LLM_QUALITY_ENABLED", False)
    monkeypatch.setattr(
        "app.services.llm.external_route.get_provider",
        lambda: FakeProvider(
            responses=[json.dumps({**external_payload, "variants": external_payload["variants"][:1]})]
        ),
    )

    resp = client.post(
        "/api/v1/itinerary",
        json={
            "destination_text": "Таррагона",
            "duration_days": 1,
            "start_date": "2026-06-10",
            "variant_count": 3,
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "llm-external-draft"
    assert len(data["variants"]) == 1
    assert data["variants"][0]["days"][0]["places"][0]["name"] == "Amfiteatre de Tarragona"
    assert len(data["variants"][0]["days"][0]["places"]) == 4
    assert all(place["lat"] and place["lng"] for place in data["variants"][0]["days"][0]["places"])
    assert "центральный район" not in json.dumps(data, ensure_ascii=False)


def test_manual_destination_external_route_requests_single_variant_schema(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    captured_requests = []
    payload = {
        "variants": [
            {
                "variant_index": 0,
                "title": "Single Tarragona route",
                "days": [
                    {
                        "day_number": 1,
                        "theme": "culture",
                        "places": [
                            {
                                "name": f"Tarragona POI {index}",
                                "category": "culture",
                                "lat": 41.11 + index / 1000,
                                "lng": 1.25 + index / 1000,
                                "address": f"Address {index}",
                                "arrival_time": f"{9 + index:02d}:30",
                                "departure_time": f"{10 + index:02d}:20",
                                "visit_duration_minutes": 50,
                                "travel_from_previous_minutes": 10 if index else 0,
                                "reason": "Specific Tarragona stop.",
                                "confidence": 0.86,
                            }
                            for index in range(4)
                        ],
                    }
                ],
            }
        ]
    }

    class CapturingProvider(FakeProvider):
        def complete(self, request):
            captured_requests.append(request)
            return super().complete(request)

    monkeypatch.setattr(settings, "LLM_EXTERNAL_ROUTE_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_EXTERNAL_ROUTE_COORDINATE_REPAIR_ENABLED", False)
    monkeypatch.setattr(settings, "LLM_QUALITY_ENABLED", False)
    monkeypatch.setattr(
        "app.services.llm.external_route.get_provider",
        lambda: CapturingProvider(responses=[json.dumps(payload)]),
    )

    resp = client.post(
        "/api/v1/itinerary",
        json={
            "destination_text": "Таррагона",
            "duration_days": 1,
            "start_date": "2026-06-10",
            "variant_count": 3,
        },
    )

    assert resp.status_code == 200
    request = captured_requests[0]
    assert request.json_schema["schema"]["properties"]["variants"]["maxItems"] == 1
    assert request.max_tokens <= 4500
    assert request.timeout_seconds <= 24.0
    assert json.loads(request.messages[1].content)["context"]["trip"]["variant_count"] == 1


def test_external_route_repairs_coordinates_and_travel_minutes(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    captured_geocode_queries = []
    payload = {
        "variants": [
            {
                "variant_index": 0,
                "title": "Salou route",
                "days": [
                    {
                        "day_number": 1,
                        "theme": "coast",
                        "places": [
                            {
                                "name": "Font Lluminosa",
                                "category": "viewpoint",
                                "lat": 41.0701,
                                "lng": 1.1600,
                                "address": "Passeig de Jaume I",
                                "arrival_time": "09:30",
                                "departure_time": "10:20",
                                "visit_duration_minutes": 50,
                                "travel_from_previous_minutes": 0,
                                "reason": "Specific Salou landmark.",
                                "confidence": 0.9,
                            },
                            {
                                "name": "Torre Vella de Salou",
                                "category": "culture",
                                "lat": 41.0695,
                                "lng": 1.1610,
                                "address": "Carrer de l'Arquebisbe Pere de Cardona",
                                "arrival_time": "10:40",
                                "departure_time": "11:40",
                                "visit_duration_minutes": 60,
                                "travel_from_previous_minutes": 0,
                                "reason": "Historic Salou site.",
                                "confidence": 0.88,
                            },
                            {
                                "name": "Parc Municipal de Salou",
                                "category": "nature",
                                "lat": 41.0700,
                                "lng": 1.1620,
                                "address": "Carrer de Barbastre",
                                "arrival_time": "12:05",
                                "departure_time": "13:05",
                                "visit_duration_minutes": 60,
                                "travel_from_previous_minutes": 0,
                                "reason": "Central green stop.",
                                "confidence": 0.84,
                            },
                            {
                                "name": "Platja de Llevant",
                                "category": "beach",
                                "lat": 41.0690,
                                "lng": 1.1630,
                                "address": "Passeig de Jaume I",
                                "arrival_time": "13:30",
                                "departure_time": "14:30",
                                "visit_duration_minutes": 60,
                                "travel_from_previous_minutes": 0,
                                "reason": "Main beach promenade on land.",
                                "confidence": 0.84,
                            },
                        ],
                    }
                ],
            }
        ]
    }

    class GeocodeResponse:
        status_code = 200

        def __init__(self, lat: float, lon: float, name: str):
            self.lat = lat
            self.lon = lon
            self.name = name

        def json(self):
            return [{"lat": self.lat, "lon": self.lon, "name": self.name}]

    corrected = {
        "Font Lluminosa": (41.0764, 1.1419),
        "Torre Vella de Salou": (41.0783, 1.1308),
        "Parc Municipal de Salou": (41.0738, 1.1486),
        "Platja de Llevant": (41.0760, 1.1438),
    }

    def fake_geocode(_url, params, timeout):
        captured_geocode_queries.append((params, timeout))
        for name, coords in corrected.items():
            if name in params["q"]:
                return GeocodeResponse(*coords, name=name)
        return GeocodeResponse(41.0760, 1.1410, name="Salou")

    monkeypatch.setattr(settings, "LLM_EXTERNAL_ROUTE_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_EXTERNAL_ROUTE_COORDINATE_REPAIR_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_QUALITY_ENABLED", False)
    monkeypatch.setattr("app.services.llm.external_route.httpx.get", fake_geocode)
    monkeypatch.setattr(
        "app.services.llm.external_route.get_provider", lambda: FakeProvider(responses=[json.dumps(payload)])
    )

    resp = client.post(
        "/api/v1/itinerary",
        json={
            "destination_text": "Salou",
            "duration_days": 1,
            "start_date": "2026-06-10",
            "variant_count": 1,
            "allow_external_route": True,
        },
    )

    assert resp.status_code == 200
    places = resp.json()["days"][0]["places"]
    assert places[0]["lat"] == 41.0764
    assert places[0]["lng"] == 1.1419
    assert places[1]["travel_from_previous_minutes"] > 0
    assert len(captured_geocode_queries) == 5


def test_external_route_rejects_risky_unconfirmed_coordinates(monkeypatch: pytest.MonkeyPatch):
    payload = {
        "variants": [
            {
                "variant_index": 0,
                "title": "Unconfirmed coast",
                "days": [
                    {
                        "day_number": 1,
                        "theme": "coast",
                        "places": [
                            {
                                "name": f"Risky Place {index}",
                                "category": "viewpoint",
                                "lat": 41.07 + index / 1000,
                                "lng": 1.16 + index / 1000,
                                "address": "Coast",
                                "arrival_time": f"{9 + index}:30",
                                "departure_time": f"{10 + index}:20",
                                "visit_duration_minutes": 50,
                                "travel_from_previous_minutes": 0,
                                "reason": "Specific but unverified.",
                                "confidence": 0.6,
                            }
                            for index in range(4)
                        ],
                    }
                ],
            }
        ]
    }

    class DestinationOnlyResponse:
        status_code = 200

        def json(self):
            return [{"lat": 41.076, "lon": 1.141, "name": "Salou"}]

    monkeypatch.setattr(settings, "LLM_EXTERNAL_ROUTE_COORDINATE_REPAIR_ENABLED", True)
    monkeypatch.setattr(
        "app.services.llm.external_route.httpx.get", lambda *_args, **_kwargs: DestinationOnlyResponse()
    )

    variants = _normalize_external_variants(
        payload=payload,
        destination_id=DEST_ID,
        destination_name="Salou",
        destination_center=(41.076, 1.141),
        trip_id=None,
        request=ItineraryGenerateRequest(
            destination_text="Salou",
            duration_days=1,
            start_date=date(2026, 6, 10),
            allow_external_route=True,
        ),
        trigger="manual_destination",
    )

    assert variants == []


def test_external_route_keeps_ordinary_unrepaired_city_poi_inside_radius(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "LLM_EXTERNAL_ROUTE_COORDINATE_REPAIR_ENABLED", True)

    assert not _should_reject_unrepaired_coordinate(
        raw_place={"category": "museum", "confidence": 0.72},
        name="Museu de Cambrils",
        lat=41.075,
        lng=1.055,
        destination_center=(41.074871, 1.054892),
        radius_km=35,
    )
    assert _should_reject_unrepaired_coordinate(
        raw_place={"category": "viewpoint", "confidence": 0.6},
        name="Mirador de la Punta",
        lat=41.075,
        lng=1.055,
        destination_center=(41.074871, 1.054892),
        radius_km=35,
    )


def test_manual_destination_regenerate_rejects_same_external_signature(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    def place(name: str, index: int) -> dict:
        return {
            "name": name,
            "category": "culture",
            "lat": 41.11 + index / 1000,
            "lng": 1.25 + index / 1000,
            "address": f"Address {index}",
            "arrival_time": f"{9 + index:02d}:30",
            "departure_time": f"{10 + index:02d}:20",
            "visit_duration_minutes": 50,
            "travel_from_previous_minutes": 10 if index else 0,
            "reason": "Specific Tarragona POI.",
            "confidence": 0.86,
        }

    same_names = [
        "Amfiteatre de Tarragona",
        "Circ Roma de Tarragona",
        "Catedral de Tarragona",
        "Balco del Mediterrani",
    ]
    other_names = [
        "Passeig Arqueologic",
        "Mercat Central de Tarragona",
        "Museu Nacional Arqueologic de Tarragona",
        "Forum Provincial de Tarragona",
    ]
    excluded_signature = (
        f"llm-external-"
        f"{uuid.uuid5(uuid.NAMESPACE_URL, compact_json({'trip_id': None, 'destination': 'Таррагона', 'days': [same_names]}))}"
    )
    responses = [
        json.dumps(
            {
                "variants": [
                    {
                        "variant_index": 0,
                        "title": "Same route",
                        "days": [
                            {
                                "day_number": 1,
                                "theme": "history",
                                "places": [place(name, i) for i, name in enumerate(same_names)],
                            }
                        ],
                    }
                ]
            }
        ),
        json.dumps(
            {
                "variants": [
                    {
                        "variant_index": 0,
                        "title": "Different route",
                        "days": [
                            {
                                "day_number": 1,
                                "theme": "history",
                                "places": [place(name, i) for i, name in enumerate(other_names)],
                            }
                        ],
                    }
                ]
            }
        ),
    ]
    monkeypatch.setattr(settings, "LLM_EXTERNAL_ROUTE_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_EXTERNAL_ROUTE_COORDINATE_REPAIR_ENABLED", False)
    monkeypatch.setattr(settings, "LLM_QUALITY_ENABLED", False)
    monkeypatch.setattr("app.services.llm.external_route.get_provider", lambda: FakeProvider(responses=responses))

    resp = client.post(
        "/api/v1/itinerary",
        json={
            "destination_text": "Таррагона",
            "duration_days": 1,
            "start_date": "2026-06-10",
            "variant_count": 3,
            "exclude_signature": excluded_signature,
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["route_signature"] != excluded_signature
    assert [place["name"] for place in data["days"][0]["places"]] == other_names


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
