from unittest.mock import Mock

import httpx

DEST_ID = "11111111-1111-1111-1111-111111111111"
POI_ID = "22222222-2222-2222-2222-222222222222"


def _create_trip(client, auth_headers, trip_data):
    resp = client.post("/api/trips/", json={**trip_data, "destination_id": DEST_ID}, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()["id"]


def _ml_response():
    days = [
        {
            "day": day_number,
            "day_number": day_number,
            "theme": "culture",
            "start_time": "09:30",
            "end_time": "19:00",
            "items": [
                {
                    "id": POI_ID,
                    "poi_id": POI_ID,
                    "name": f"Museum {day_number}",
                    "category": "culture",
                    "lat": 55.75,
                    "lng": 37.62,
                    "arrival_time": "09:30",
                    "departure_time": "11:30",
                    "visit_duration_minutes": 120,
                    "travel_from_previous_minutes": 0,
                    "opening_status": "open",
                    "score": 1.4,
                }
            ],
        }
        for day_number in range(1, 15)
    ]
    return {
        "variants": [
            {
                "destination_id": DEST_ID,
                "duration_days": 3,
                "variant_index": 0,
                "variant_seed": 101,
                "route_signature": "sig-a",
                "model_version": "itinerary-poi-ranker-v1",
                "score_summary": {
                    "total_pois": 1,
                    "travel_overhead_minutes": 0,
                    "avg_relevance": 1.4,
                    "llm_quality_model_version": "qwen3.6-35b-a3b/latest",
                    "llm_quality_review": {
                        "status": "caution",
                        "confidence": 0.8,
                        "provider": "yandex",
                        "model": "qwen3.6-35b-a3b/latest",
                        "prompt_version": "itinerary_quality_v1",
                        "issues": [
                            {
                                "code": "overloaded_day",
                                "severity": "warning",
                                "message": "Day is dense.",
                                "evidence": [],
                            }
                        ],
                        "suggested_adjustments": [],
                        "user_summary_ru": "Маршрут плотный.",
                        "defense_trace": None,
                    },
                    "llm_quality_day_reviews": {
                        "1": {
                            "status": "caution",
                            "confidence": 0.8,
                            "provider": "yandex",
                            "model": "qwen3.6-35b-a3b/latest",
                            "prompt_version": "itinerary_quality_v1",
                            "issues": [],
                            "suggested_adjustments": [],
                            "user_summary_ru": None,
                            "defense_trace": None,
                        }
                    },
                    "llm_quality_item_reviews": {
                        POI_ID: {
                            "status": "caution",
                            "confidence": 0.8,
                            "provider": "yandex",
                            "model": "qwen3.6-35b-a3b/latest",
                            "prompt_version": "itinerary_quality_v1",
                            "issues": [],
                            "suggested_adjustments": [],
                            "user_summary_ru": None,
                            "defense_trace": None,
                        }
                    },
                },
                "days": days,
            }
        ]
    }


def _ml_response_with_day_timeline():
    body = _ml_response()
    first_day_items = [
        {
            "id": "22222222-2222-2222-2222-222222222220",
            "poi_id": "22222222-2222-2222-2222-222222222220",
            "name": "Morning museum",
            "category": "culture",
            "lat": 55.75,
            "lng": 37.62,
            "arrival_time": "09:30",
            "departure_time": "11:30",
            "visit_duration_minutes": 120,
            "travel_from_previous_minutes": 0,
            "opening_status": "open",
            "score": 1.4,
        },
        {
            "id": "22222222-2222-2222-2222-222222222221",
            "poi_id": "22222222-2222-2222-2222-222222222221",
            "name": "Lunch market",
            "category": "food",
            "lat": 55.76,
            "lng": 37.63,
            "arrival_time": "12:00",
            "departure_time": "13:00",
            "visit_duration_minutes": 60,
            "travel_from_previous_minutes": 30,
            "opening_status": "open",
            "score": 1.2,
        },
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "poi_id": "22222222-2222-2222-2222-222222222222",
            "name": "Evening gallery",
            "category": "culture",
            "lat": 55.77,
            "lng": 37.64,
            "arrival_time": "13:20",
            "departure_time": "14:20",
            "visit_duration_minutes": 60,
            "travel_from_previous_minutes": 20,
            "opening_status": "open",
            "score": 1.3,
        },
    ]
    body["variants"][0]["days"][0]["items"] = first_day_items
    return body


def _ml_response_with_external_candidate():
    body = _ml_response()
    body["variants"][0]["days"][0]["items"].append(
        {
            "id": "33333333-3333-3333-3333-333333333333",
            "name": "Quiet tea house",
            "category": "food",
            "lat": 55.751,
            "lng": 37.621,
            "arrival_time": "12:00",
            "departure_time": "13:00",
            "visit_duration_minutes": 60,
            "travel_from_previous_minutes": 20,
            "opening_status": "unknown",
            "score": 0.82,
            "external_candidate_source": "llm_candidate_poi",
        }
    )
    body["variants"][0]["score_summary"]["llm_candidate_poi"] = [
        {
            "candidate_id": "33333333-3333-3333-3333-333333333333",
            "name": "Quiet tea house",
            "category": "food",
            "lat": 55.751,
            "lng": 37.621,
            "source_url": "https://example.com/tea-house",
            "confidence": 0.82,
            "requires_admin_review": True,
            "missing_fields": [],
            "reason": "User asked for quiet food places.",
            "status": "external_candidate",
        }
    ]
    return body


def _ml_itinerary_call(post_mock):
    return next(call for call in post_mock.call_args_list if "/api/v1/itinerary" in call.args[0])


def _start_generation(client, auth_headers, trip_id, payload):
    response = client.post(
        f"/api/trips/{trip_id}/itinerary/generate",
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 202
    assert response.json()["status"] in {"queued", "completed"}
    return response.json()


def _draft_itineraries(client, auth_headers, trip_id):
    state = client.get(f"/api/trips/{trip_id}/itinerary", headers=auth_headers)
    assert state.status_code == 200
    return state.json()["drafts"]


def test_generate_and_approve_itinerary(client, auth_headers, trip_data, monkeypatch):
    trip_id = _create_trip(client, auth_headers, trip_data)
    response = Mock()
    response.json.return_value = _ml_response()
    response.raise_for_status.return_value = None
    post_mock = Mock(return_value=response)
    monkeypatch.setattr("app.services.itinerary_service.httpx.post", post_mock)

    _start_generation(client, auth_headers, trip_id, {"variant_count": 1, "pace": "standard"})
    itinerary = _draft_itineraries(client, auth_headers, trip_id)[0]
    assert itinerary["status"] == "draft"
    assert _ml_itinerary_call(post_mock).kwargs["json"]["duration_days"] == 14
    assert _ml_itinerary_call(post_mock).kwargs["json"]["trip_notes"] == trip_data["notes"]
    assert _ml_itinerary_call(post_mock).kwargs["timeout"] == 180.0
    assert len(itinerary["days"]) == 14
    assert itinerary["days"][0]["items"][0]["arrival_time"] == "09:30:00"
    assert itinerary["quality_review"] is None
    assert itinerary["days"][0]["quality_review"] is None
    assert itinerary["days"][0]["items"][0]["quality_review"] is None
    assert "llm_quality_review" not in itinerary["score_summary"]

    approved = client.post(f"/api/trips/{trip_id}/itinerary/{itinerary['id']}/approve", headers=auth_headers)
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    state = client.get(f"/api/trips/{trip_id}/itinerary", headers=auth_headers)
    assert state.status_code == 200
    assert state.json()["approved"]["id"] == itinerary["id"]


def test_regenerate_approved_catalog_trip_requests_one_variant_and_replaces_approved_route(
    client, auth_headers, trip_data, monkeypatch
):
    trip_id = _create_trip(client, auth_headers, trip_data)
    first_response = Mock()
    first_response.json.return_value = _ml_response()
    first_response.raise_for_status.return_value = None
    second_response = Mock()
    second_body = _ml_response()
    second_body["variants"][0]["route_signature"] = "sig-b"
    second_body["variants"][0]["variant_seed"] = 202
    second_response.json.return_value = second_body
    second_response.raise_for_status.return_value = None

    def post_side_effect(*_args, **kwargs):
        return second_response if kwargs["json"].get("exclude_signature") == "sig-a" else first_response

    post_mock = Mock(side_effect=post_side_effect)
    monkeypatch.setattr("app.services.itinerary_service.httpx.post", post_mock)

    _start_generation(client, auth_headers, trip_id, {"variant_count": 1})
    approved_id = _draft_itineraries(client, auth_headers, trip_id)[0]["id"]
    approved = client.post(f"/api/trips/{trip_id}/itinerary/{approved_id}/approve", headers=auth_headers)
    assert approved.status_code == 200

    regenerated = client.post(
        f"/api/trips/{trip_id}/itinerary/regenerate",
        json={"variant_count": 3, "exclude_signature": "sig-a", "allow_external_route": True},
        headers=auth_headers,
    )

    assert regenerated.status_code == 202
    regenerate_payload = next(
        call.kwargs["json"] for call in post_mock.call_args_list if call.kwargs["json"].get("exclude_signature")
    )
    assert regenerate_payload["variant_count"] == 1
    assert regenerate_payload["exclude_signature"] == "sig-a"
    state = client.get(f"/api/trips/{trip_id}/itinerary", headers=auth_headers)
    assert state.status_code == 200
    assert state.json()["approved"]["id"] != approved_id
    assert state.json()["approved"]["route_signature"] == "sig-b"
    assert state.json()["drafts"] == []


def test_generate_rejects_variants_with_empty_active_days(client, auth_headers, trip_data, monkeypatch):
    trip_id = _create_trip(client, auth_headers, trip_data)
    response = Mock()
    response.json.return_value = {
        "variants": [
            {
                "destination_id": DEST_ID,
                "duration_days": 14,
                "variant_index": 0,
                "route_signature": "empty",
                "days": [{"day": day, "day_number": day, "theme": "culture", "items": []} for day in range(1, 15)],
            }
        ]
    }
    response.raise_for_status.return_value = None
    monkeypatch.setattr("app.services.itinerary_service.httpx.post", Mock(return_value=response))

    generated = client.post(
        f"/api/trips/{trip_id}/itinerary/generate",
        json={"variant_count": 1},
        headers=auth_headers,
    )

    assert generated.status_code == 202
    state = client.get(f"/api/trips/{trip_id}/itinerary", headers=auth_headers)
    assert state.json()["generation_job"]["status"] == "failed"
    assert state.json()["generation_job"]["error_code"] == "ITINERARY_NO_FEASIBLE_ROUTE"


def test_generate_manual_destination_can_persist_external_route(client, auth_headers, trip_data, monkeypatch):
    trip_payload = {**trip_data, "destination": "Manual Coast", "destination_id": None}
    trip = client.post("/api/trips/", json=trip_payload, headers=auth_headers)
    assert trip.status_code == 201
    trip_id = trip.json()["id"]
    external_item_id = "33333333-3333-3333-3333-333333333333"
    response = Mock()
    response.json.return_value = {
        "destination_id": "44444444-4444-4444-4444-444444444444",
        "duration_days": 14,
        "variant_index": 0,
        "variant_seed": 101,
        "route_signature": "llm-external:manual",
        "model_version": "llm-external-route:qwen3.6-35b-a3b/latest",
        "source": "llm-external-draft",
        "score_summary": {
            "external_route_used": True,
            "catalog_mutation_allowed": False,
            "candidate_destination": {"name": "Manual Coast", "source_urls": ["https://example.com/manual"]},
        },
        "days": [
            {
                "day": day,
                "day_number": day,
                "theme": "culture",
                "items": [
                    {
                        "id": external_item_id,
                        "name": "External Museum",
                        "category": "museum",
                        "lat": 55.75,
                        "lng": 37.62,
                        "arrival_time": "10:00",
                        "departure_time": "11:30",
                        "visit_duration_minutes": 90,
                        "travel_from_previous_minutes": 0,
                        "external_candidate_source": "llm_external_route",
                        "score": 0.8,
                    }
                ],
            }
            for day in range(1, 15)
        ],
    }
    response.raise_for_status.return_value = None
    post_mock = Mock(return_value=response)
    monkeypatch.setattr("app.services.itinerary_service.httpx.post", post_mock)

    generated = client.post(
        f"/api/trips/{trip_id}/itinerary/generate",
        json={"variant_count": 1},
        headers=auth_headers,
    )

    assert generated.status_code == 202
    itinerary = _draft_itineraries(client, auth_headers, trip_id)[0]
    assert itinerary["score_summary"]["external_route_used"] is True
    item = itinerary["days"][0]["items"][0]
    assert item["poi_id"] is None
    assert item["source"] == "external_candidate"
    payload = _ml_itinerary_call(post_mock).kwargs["json"]
    assert payload["destination_id"] is None
    assert payload["destination_text"] == "Manual Coast"
    assert payload["variant_count"] == 1
    assert payload["allow_external_route"] is True


def test_external_llm_route_response_is_persisted_as_one_variant_for_catalog_trip(
    client, auth_headers, trip_data, monkeypatch
):
    trip_id = _create_trip(client, auth_headers, trip_data)
    external_body = _ml_response()
    external_body["source"] = "llm-external-draft"
    external_body["model_version"] = "llm-external-route:qwen3.6-35b-a3b/latest"
    external_body["score_summary"] = {"external_route_used": True}
    external_body["variants"] = []
    for index in range(3):
        variant = _ml_response()["variants"][0]
        variant["source"] = "llm-external-draft"
        variant["model_version"] = "llm-external-route:qwen3.6-35b-a3b/latest"
        variant["route_signature"] = f"llm-external-{index}"
        variant["score_summary"] = {"external_route_used": True}
        external_body["variants"].append(variant)
    response = Mock()
    response.json.return_value = external_body
    response.raise_for_status.return_value = None
    monkeypatch.setattr("app.services.itinerary_service.httpx.post", Mock(return_value=response))

    generated = client.post(
        f"/api/trips/{trip_id}/itinerary/generate",
        json={"variant_count": 3, "allow_external_route": True},
        headers=auth_headers,
    )

    assert generated.status_code == 202
    drafts = _draft_itineraries(client, auth_headers, trip_id)
    assert len(drafts) == 1
    assert drafts[0]["route_signature"] == "llm-external-0"


def test_external_route_persists_travel_overhead_from_items(client, auth_headers, trip_data, monkeypatch):
    trip_id = _create_trip(client, auth_headers, trip_data)
    body = _ml_response_with_day_timeline()
    body["variants"][0]["source"] = "llm-external-draft"
    body["variants"][0]["model_version"] = "llm-external-route:qwen3.6-35b-a3b/latest"
    body["variants"][0]["score_summary"] = {"external_route_used": True}
    response = Mock()
    response.json.return_value = body
    response.raise_for_status.return_value = None
    monkeypatch.setattr("app.services.itinerary_service.httpx.post", Mock(return_value=response))

    generated = client.post(
        f"/api/trips/{trip_id}/itinerary/generate",
        json={"variant_count": 1, "allow_external_route": True},
        headers=auth_headers,
    )

    assert generated.status_code == 202
    summary = _draft_itineraries(client, auth_headers, trip_id)[0]["score_summary"]
    assert summary["external_route_used"] is True
    assert summary["travel_overhead_minutes"] == 50


def test_generate_preserves_ml_no_feasible_error(client, auth_headers, trip_data, monkeypatch):
    trip_id = _create_trip(client, auth_headers, trip_data)
    response = Mock()
    response.status_code = 422
    response.json.return_value = {
        "error": "ITINERARY_NO_FEASIBLE_ROUTE",
        "message": "Could not build a route for the selected trip parameters.",
    }
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "unprocessable entity",
        request=httpx.Request("POST", "http://ml-service/api/v1/itinerary"),
        response=response,
    )
    monkeypatch.setattr("app.services.itinerary_service.httpx.post", Mock(return_value=response))

    generated = client.post(
        f"/api/trips/{trip_id}/itinerary/generate",
        json={"variant_count": 1},
        headers=auth_headers,
    )

    assert generated.status_code == 202
    state = client.get(f"/api/trips/{trip_id}/itinerary", headers=auth_headers)
    assert state.json()["generation_job"]["status"] == "failed"
    assert state.json()["generation_job"]["error_code"] == "ITINERARY_NO_FEASIBLE_ROUTE"


def test_itinerary_item_edit_remove_and_visit(client, auth_headers, trip_data, monkeypatch):
    trip_id = _create_trip(client, auth_headers, trip_data)
    response = Mock()
    response.json.return_value = _ml_response()
    response.raise_for_status.return_value = None
    monkeypatch.setattr("app.services.itinerary_service.httpx.post", Mock(return_value=response))
    _start_generation(client, auth_headers, trip_id, {"variant_count": 1})
    itinerary = _draft_itineraries(client, auth_headers, trip_id)[0]
    client.post(f"/api/trips/{trip_id}/itinerary/{itinerary['id']}/approve", headers=auth_headers)
    item_id = itinerary["days"][0]["items"][0]["id"]

    patched = client.patch(
        f"/api/trips/{trip_id}/itinerary/items/{item_id}",
        json={"is_pinned": True, "duration_minutes": 135},
        headers=auth_headers,
    )
    assert patched.status_code == 200
    assert patched.json()["is_pinned"] is True
    assert patched.json()["duration_minutes"] == 135

    visited = client.post(f"/api/trips/{trip_id}/itinerary/items/{item_id}/visit", headers=auth_headers)
    assert visited.status_code == 200
    assert visited.json()["visited_place_id"] is not None

    places = client.get(f"/api/trips/{trip_id}/places", headers=auth_headers)
    assert places.status_code == 200
    assert places.json()[0]["name"] == "Museum 1"

    unvisited = client.delete(f"/api/trips/{trip_id}/itinerary/items/{item_id}/visit", headers=auth_headers)
    assert unvisited.status_code == 200
    assert unvisited.json()["visited_place_id"] is None

    places_after_unvisit = client.get(f"/api/trips/{trip_id}/places", headers=auth_headers)
    assert places_after_unvisit.status_code == 200
    assert places_after_unvisit.json() == []

    removed = client.delete(f"/api/trips/{trip_id}/itinerary/items/{item_id}", headers=auth_headers)
    assert removed.status_code == 204


def test_external_candidate_poi_is_persisted_but_cannot_be_visited(client, auth_headers, trip_data, monkeypatch):
    trip_id = _create_trip(client, auth_headers, trip_data)
    response = Mock()
    response.json.return_value = _ml_response_with_external_candidate()
    response.raise_for_status.return_value = None
    monkeypatch.setattr("app.services.itinerary_service.httpx.post", Mock(return_value=response))

    _start_generation(client, auth_headers, trip_id, {"variant_count": 1})
    items = _draft_itineraries(client, auth_headers, trip_id)[0]["days"][0]["items"]
    external = next(item for item in items if item["name"] == "Quiet tea house")
    assert external["poi_id"] is None
    assert external["source"] == "external_candidate"
    assert external["external_candidate_source"] is None

    visited = client.post(f"/api/trips/{trip_id}/itinerary/items/{external['id']}/visit", headers=auth_headers)
    assert visited.status_code == 400
    assert visited.json()["error"] == "CANDIDATE_POI_NOT_APPROVED"

    removed = client.delete(f"/api/trips/{trip_id}/itinerary/items/{external['id']}", headers=auth_headers)
    assert removed.status_code == 204


def test_itinerary_item_time_edit_shifts_following_items(client, auth_headers, trip_data, monkeypatch):
    trip_id = _create_trip(client, auth_headers, trip_data)
    response = Mock()
    response.json.return_value = _ml_response_with_day_timeline()
    response.raise_for_status.return_value = None
    monkeypatch.setattr("app.services.itinerary_service.httpx.post", Mock(return_value=response))
    _start_generation(client, auth_headers, trip_id, {"variant_count": 1})
    itinerary = _draft_itineraries(client, auth_headers, trip_id)[0]
    item_id = itinerary["days"][0]["items"][0]["id"]

    patched = client.patch(
        f"/api/trips/{trip_id}/itinerary/items/{item_id}",
        json={"duration_minutes": 135},
        headers=auth_headers,
    )

    assert patched.status_code == 200
    assert patched.json()["departure_time"] == "11:45:00"
    state = client.get(f"/api/trips/{trip_id}/itinerary", headers=auth_headers).json()
    items = state["drafts"][0]["days"][0]["items"]
    assert items[1]["arrival_time"] == "12:15:00"
    assert items[1]["departure_time"] == "13:15:00"
    assert items[2]["arrival_time"] == "13:35:00"
    assert items[2]["departure_time"] == "14:35:00"

    repatched = client.patch(
        f"/api/trips/{trip_id}/itinerary/items/{item_id}",
        json={"arrival_time": "10:00"},
        headers=auth_headers,
    )

    assert repatched.status_code == 200
    assert repatched.json()["arrival_time"] == "10:00:00"
    assert repatched.json()["departure_time"] == "12:15:00"
    state = client.get(f"/api/trips/{trip_id}/itinerary", headers=auth_headers).json()
    items = state["drafts"][0]["days"][0]["items"]
    assert items[1]["arrival_time"] == "12:45:00"


def test_itinerary_item_swap_recalculates_day_route(client, auth_headers, trip_data, monkeypatch):
    trip_id = _create_trip(client, auth_headers, trip_data)
    response = Mock()
    response.json.return_value = _ml_response_with_day_timeline()
    response.raise_for_status.return_value = None
    monkeypatch.setattr("app.services.itinerary_service.httpx.post", Mock(return_value=response))
    _start_generation(client, auth_headers, trip_id, {"variant_count": 1})
    itinerary = _draft_itineraries(client, auth_headers, trip_id)[0]
    first_item_id = itinerary["days"][0]["items"][0]["id"]
    last_item_id = itinerary["days"][0]["items"][2]["id"]

    swapped = client.post(
        f"/api/trips/{trip_id}/itinerary/items/{first_item_id}/swap",
        json={"target_item_id": last_item_id},
        headers=auth_headers,
    )

    assert swapped.status_code == 200
    items = swapped.json()["days"][0]["items"]
    assert [item["name"] for item in items] == ["Evening gallery", "Lunch market", "Morning museum"]
    assert [item["order"] for item in items] == [0, 1, 2]
    assert items[0]["arrival_time"] == "09:30:00"
    assert items[0]["travel_from_previous_minutes"] == 0
    assert items[1]["travel_from_previous_minutes"] > 0
    assert items[1]["arrival_time"] > items[0]["departure_time"]
    assert items[2]["arrival_time"] > items[1]["departure_time"]


def test_itinerary_item_swap_between_days_recalculates_both_days(client, auth_headers, trip_data, monkeypatch):
    trip_id = _create_trip(client, auth_headers, trip_data)
    response = Mock()
    response.json.return_value = _ml_response_with_day_timeline()
    response.raise_for_status.return_value = None
    monkeypatch.setattr("app.services.itinerary_service.httpx.post", Mock(return_value=response))
    _start_generation(client, auth_headers, trip_id, {"variant_count": 1})
    itinerary = _draft_itineraries(client, auth_headers, trip_id)[0]
    day_one_second_id = itinerary["days"][0]["items"][1]["id"]
    day_two_first_id = itinerary["days"][1]["items"][0]["id"]

    swapped = client.post(
        f"/api/trips/{trip_id}/itinerary/items/{day_one_second_id}/swap",
        json={"target_item_id": day_two_first_id},
        headers=auth_headers,
    )

    assert swapped.status_code == 200
    days = swapped.json()["days"]
    assert [item["name"] for item in days[0]["items"]] == ["Morning museum", "Museum 2", "Evening gallery"]
    assert [item["name"] for item in days[1]["items"]] == ["Lunch market"]
    assert [item["order"] for item in days[0]["items"]] == [0, 1, 2]
    assert days[0]["items"][1]["travel_from_previous_minutes"] >= 0
    assert days[0]["items"][2]["travel_from_previous_minutes"] > 0
    assert days[1]["items"][0]["travel_from_previous_minutes"] == 0
    assert days[1]["items"][0]["arrival_time"] == "09:30:00"


def test_itinerary_item_move_between_days_inserts_without_swapping(client, auth_headers, trip_data, monkeypatch):
    trip_id = _create_trip(client, auth_headers, trip_data)
    response = Mock()
    response.json.return_value = _ml_response_with_day_timeline()
    response.raise_for_status.return_value = None
    monkeypatch.setattr("app.services.itinerary_service.httpx.post", Mock(return_value=response))
    _start_generation(client, auth_headers, trip_id, {"variant_count": 1})
    itinerary = _draft_itineraries(client, auth_headers, trip_id)[0]
    moved_item_id = itinerary["days"][0]["items"][1]["id"]
    target_day_id = itinerary["days"][1]["id"]

    moved = client.post(
        f"/api/trips/{trip_id}/itinerary/items/{moved_item_id}/move",
        json={"target_day_id": target_day_id, "target_order": 1},
        headers=auth_headers,
    )

    assert moved.status_code == 200
    days = moved.json()["days"]
    assert [item["name"] for item in days[0]["items"]] == ["Morning museum", "Evening gallery"]
    assert [item["name"] for item in days[1]["items"]] == ["Museum 2", "Lunch market"]
    assert [item["order"] for item in days[0]["items"]] == [0, 1]
    assert [item["order"] for item in days[1]["items"]] == [0, 1]
    assert days[0]["items"][1]["travel_from_previous_minutes"] > 0
    assert days[1]["items"][1]["travel_from_previous_minutes"] > 0
    assert days[1]["items"][1]["arrival_time"] > days[1]["items"][0]["departure_time"]


def test_trip_parameter_change_resets_itinerary_state(client, auth_headers, trip_data, monkeypatch):
    trip_id = _create_trip(client, auth_headers, trip_data)
    response = Mock()
    response.json.return_value = _ml_response()
    response.raise_for_status.return_value = None
    monkeypatch.setattr("app.services.itinerary_service.httpx.post", Mock(return_value=response))
    _start_generation(client, auth_headers, trip_id, {"variant_count": 1})
    itinerary = _draft_itineraries(client, auth_headers, trip_id)[0]
    client.post(f"/api/trips/{trip_id}/itinerary/{itinerary['id']}/approve", headers=auth_headers)

    updated = client.put(
        f"/api/trips/{trip_id}",
        json={"end_date": "2026-06-10"},
        headers=auth_headers,
    )
    assert updated.status_code == 200

    state = client.get(f"/api/trips/{trip_id}/itinerary", headers=auth_headers)
    assert state.status_code == 200
    assert state.json()["approved"] is None
    assert state.json()["drafts"] == []
