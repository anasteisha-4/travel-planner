from unittest.mock import Mock

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
                "score_summary": {"total_pois": 1, "travel_overhead_minutes": 0, "avg_relevance": 1.4},
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


def test_generate_and_approve_itinerary(client, auth_headers, trip_data, monkeypatch):
    trip_id = _create_trip(client, auth_headers, trip_data)
    response = Mock()
    response.json.return_value = _ml_response()
    response.raise_for_status.return_value = None
    post_mock = Mock(return_value=response)
    monkeypatch.setattr("app.services.itinerary_service.httpx.post", post_mock)

    generated = client.post(
        f"/api/trips/{trip_id}/itinerary/generate",
        json={"variant_count": 1, "pace": "standard"},
        headers=auth_headers,
    )
    assert generated.status_code == 201
    itinerary = generated.json()[0]
    assert itinerary["status"] == "draft"
    assert post_mock.call_args.kwargs["json"]["duration_days"] == 14
    assert len(itinerary["days"]) == 14
    assert itinerary["days"][0]["items"][0]["arrival_time"] == "09:30:00"

    approved = client.post(f"/api/trips/{trip_id}/itinerary/{itinerary['id']}/approve", headers=auth_headers)
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    state = client.get(f"/api/trips/{trip_id}/itinerary", headers=auth_headers)
    assert state.status_code == 200
    assert state.json()["approved"]["id"] == itinerary["id"]


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

    assert generated.status_code == 422
    assert generated.json()["error"] == "ITINERARY_NO_FEASIBLE_ROUTE"


def test_itinerary_item_edit_remove_and_visit(client, auth_headers, trip_data, monkeypatch):
    trip_id = _create_trip(client, auth_headers, trip_data)
    response = Mock()
    response.json.return_value = _ml_response()
    response.raise_for_status.return_value = None
    monkeypatch.setattr("app.services.itinerary_service.httpx.post", Mock(return_value=response))
    itinerary = client.post(
        f"/api/trips/{trip_id}/itinerary/generate",
        json={"variant_count": 1},
        headers=auth_headers,
    ).json()[0]
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


def test_itinerary_item_time_edit_shifts_following_items(client, auth_headers, trip_data, monkeypatch):
    trip_id = _create_trip(client, auth_headers, trip_data)
    response = Mock()
    response.json.return_value = _ml_response_with_day_timeline()
    response.raise_for_status.return_value = None
    monkeypatch.setattr("app.services.itinerary_service.httpx.post", Mock(return_value=response))
    itinerary = client.post(
        f"/api/trips/{trip_id}/itinerary/generate",
        json={"variant_count": 1},
        headers=auth_headers,
    ).json()[0]
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
    itinerary = client.post(
        f"/api/trips/{trip_id}/itinerary/generate",
        json={"variant_count": 1},
        headers=auth_headers,
    ).json()[0]
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
    itinerary = client.post(
        f"/api/trips/{trip_id}/itinerary/generate",
        json={"variant_count": 1},
        headers=auth_headers,
    ).json()[0]
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
    itinerary = client.post(
        f"/api/trips/{trip_id}/itinerary/generate",
        json={"variant_count": 1},
        headers=auth_headers,
    ).json()[0]
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
    itinerary = client.post(
        f"/api/trips/{trip_id}/itinerary/generate",
        json={"variant_count": 1},
        headers=auth_headers,
    ).json()[0]
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
