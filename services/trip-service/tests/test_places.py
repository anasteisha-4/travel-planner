import pytest

PLACE_DATA = {
    "name": "Токийская башня",
    "visited_at": "2026-04-03",
    "latitude": "35.6586",
    "longitude": "139.7454",
    "notes": "Вид на Фудзи",
}


@pytest.fixture
def trip_id(client, auth_headers, trip_data):
    resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
    return resp.json()["id"]


@pytest.fixture
def place_id(client, auth_headers, trip_id):
    resp = client.post(f"/api/trips/{trip_id}/places", json=PLACE_DATA, headers=auth_headers)
    return resp.json()["id"]


class TestCreatePlace:
    def test_create_success(self, client, auth_headers, trip_id):
        resp = client.post(f"/api/trips/{trip_id}/places", json=PLACE_DATA, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == PLACE_DATA["name"]
        assert data["visited_at"] == PLACE_DATA["visited_at"]
        assert data["latitude"] == "35.6586000"
        assert data["longitude"] == "139.7454000"
        assert data["notes"] == PLACE_DATA["notes"]
        assert data["trip_id"] == trip_id
        assert "id" in data
        assert "user_id" in data

    def test_create_minimal_without_notes(self, client, auth_headers, trip_id):
        data = {"name": "Храм Сэнсо-дзи", "visited_at": "2026-04-04", "latitude": "35.7148", "longitude": "139.7967"}
        resp = client.post(f"/api/trips/{trip_id}/places", json=data, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["notes"] is None

    def test_create_no_auth(self, client, trip_id):
        resp = client.post(f"/api/trips/{trip_id}/places", json=PLACE_DATA)
        assert resp.status_code == 401

    def test_create_trip_not_found(self, client, auth_headers):
        resp = client.post(
            "/api/trips/00000000-0000-0000-0000-000000000000/places",
            json=PLACE_DATA,
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert resp.json()["error"] == "NOT_FOUND"

    def test_create_other_users_trip(self, client, auth_headers, other_user_headers, trip_id):
        resp = client.post(f"/api/trips/{trip_id}/places", json=PLACE_DATA, headers=other_user_headers)
        assert resp.status_code == 404

    def test_create_invalid_latitude_above_90(self, client, auth_headers, trip_id):
        data = {**PLACE_DATA, "latitude": "91.0"}
        resp = client.post(f"/api/trips/{trip_id}/places", json=data, headers=auth_headers)
        assert resp.status_code == 400
        assert resp.json()["error"] == "INVALID_COORDINATES"

    def test_create_invalid_latitude_below_minus_90(self, client, auth_headers, trip_id):
        data = {**PLACE_DATA, "latitude": "-90.1"}
        resp = client.post(f"/api/trips/{trip_id}/places", json=data, headers=auth_headers)
        assert resp.status_code == 400
        assert resp.json()["error"] == "INVALID_COORDINATES"

    def test_create_invalid_longitude_above_180(self, client, auth_headers, trip_id):
        data = {**PLACE_DATA, "longitude": "180.1"}
        resp = client.post(f"/api/trips/{trip_id}/places", json=data, headers=auth_headers)
        assert resp.status_code == 400
        assert resp.json()["error"] == "INVALID_COORDINATES"

    def test_create_invalid_longitude_below_minus_180(self, client, auth_headers, trip_id):
        data = {**PLACE_DATA, "longitude": "-181.0"}
        resp = client.post(f"/api/trips/{trip_id}/places", json=data, headers=auth_headers)
        assert resp.status_code == 400
        assert resp.json()["error"] == "INVALID_COORDINATES"

    def test_create_boundary_coordinates(self, client, auth_headers, trip_id):
        data = {**PLACE_DATA, "latitude": "90.0", "longitude": "-180.0"}
        resp = client.post(f"/api/trips/{trip_id}/places", json=data, headers=auth_headers)
        assert resp.status_code == 201

    def test_create_zero_coordinates(self, client, auth_headers, trip_id):
        data = {**PLACE_DATA, "latitude": "0.0", "longitude": "0.0"}
        resp = client.post(f"/api/trips/{trip_id}/places", json=data, headers=auth_headers)
        assert resp.status_code == 201


class TestGetPlaces:
    def test_get_empty(self, client, auth_headers, trip_id):
        resp = client.get(f"/api/trips/{trip_id}/places", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_places(self, client, auth_headers, trip_id):
        client.post(f"/api/trips/{trip_id}/places", json=PLACE_DATA, headers=auth_headers)
        client.post(
            f"/api/trips/{trip_id}/places",
            json={"name": "Сибуя", "visited_at": "2026-04-05", "latitude": "35.6595", "longitude": "139.7004"},
            headers=auth_headers,
        )
        resp = client.get(f"/api/trips/{trip_id}/places", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_sorted_by_visited_at(self, client, auth_headers, trip_id):
        client.post(
            f"/api/trips/{trip_id}/places",
            json={"name": "Место B", "visited_at": "2026-04-05", "latitude": "35.0", "longitude": "139.0"},
            headers=auth_headers,
        )
        client.post(
            f"/api/trips/{trip_id}/places",
            json={"name": "Место A", "visited_at": "2026-04-03", "latitude": "35.0", "longitude": "139.0"},
            headers=auth_headers,
        )
        client.post(
            f"/api/trips/{trip_id}/places",
            json={"name": "Место C", "visited_at": "2026-04-07", "latitude": "35.0", "longitude": "139.0"},
            headers=auth_headers,
        )
        resp = client.get(f"/api/trips/{trip_id}/places", headers=auth_headers)
        dates = [p["visited_at"] for p in resp.json()]
        assert dates == sorted(dates)

    def test_get_no_auth(self, client, trip_id):
        resp = client.get(f"/api/trips/{trip_id}/places")
        assert resp.status_code == 401

    def test_get_trip_not_found(self, client, auth_headers):
        resp = client.get("/api/trips/00000000-0000-0000-0000-000000000000/places", headers=auth_headers)
        assert resp.status_code == 404

    def test_get_other_users_trip(self, client, auth_headers, other_user_headers, trip_id):
        client.post(f"/api/trips/{trip_id}/places", json=PLACE_DATA, headers=auth_headers)
        resp = client.get(f"/api/trips/{trip_id}/places", headers=other_user_headers)
        assert resp.status_code == 404

    def test_get_only_own_places(self, client, auth_headers, other_user_headers, trip_data):
        trip_a = client.post("/api/trips/", json=trip_data, headers=auth_headers).json()["id"]
        trip_b = client.post("/api/trips/", json=trip_data, headers=other_user_headers).json()["id"]

        client.post(f"/api/trips/{trip_a}/places", json=PLACE_DATA, headers=auth_headers)
        client.post(f"/api/trips/{trip_b}/places", json=PLACE_DATA, headers=other_user_headers)

        resp = client.get(f"/api/trips/{trip_a}/places", headers=auth_headers)
        assert len(resp.json()) == 1
        assert resp.json()[0]["trip_id"] == trip_a


class TestUpdatePlace:
    def test_update_name(self, client, auth_headers, place_id):
        resp = client.patch(f"/api/places/{place_id}", json={"name": "Башня Скайтри"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Башня Скайтри"

    def test_update_visited_at(self, client, auth_headers, place_id):
        resp = client.patch(f"/api/places/{place_id}", json={"visited_at": "2026-05-01"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["visited_at"] == "2026-05-01"

    def test_update_notes(self, client, auth_headers, place_id):
        resp = client.patch(f"/api/places/{place_id}", json={"notes": "Обновлённые заметки"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["notes"] == "Обновлённые заметки"

    def test_update_notes_to_null(self, client, auth_headers, place_id):
        resp = client.patch(f"/api/places/{place_id}", json={"notes": None}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["notes"] is None

    def test_update_both_coordinates(self, client, auth_headers, place_id):
        resp = client.patch(
            f"/api/places/{place_id}",
            json={"latitude": "35.7148", "longitude": "139.7967"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["latitude"] == "35.7148000"
        assert resp.json()["longitude"] == "139.7967000"

    def test_update_only_latitude(self, client, auth_headers, place_id):
        resp = client.patch(f"/api/places/{place_id}", json={"latitude": "34.0"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["latitude"] == "34.0000000"
        assert resp.json()["longitude"] == "139.7454000"

    def test_update_only_longitude(self, client, auth_headers, place_id):
        resp = client.patch(f"/api/places/{place_id}", json={"longitude": "140.0"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["longitude"] == "140.0000000"
        assert resp.json()["latitude"] == "35.6586000"

    def test_update_all_fields(self, client, auth_headers, place_id):
        payload = {
            "name": "Синдзюку",
            "visited_at": "2026-04-10",
            "latitude": "35.6938",
            "longitude": "139.7036",
            "notes": "Ночная жизнь",
        }
        resp = client.patch(f"/api/places/{place_id}", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == payload["name"]
        assert data["visited_at"] == payload["visited_at"]
        assert data["latitude"] == "35.6938000"
        assert data["longitude"] == "139.7036000"
        assert data["notes"] == payload["notes"]

    def test_update_empty_body_returns_unchanged(self, client, auth_headers, place_id):
        resp = client.patch(f"/api/places/{place_id}", json={}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == PLACE_DATA["name"]
        assert data["visited_at"] == PLACE_DATA["visited_at"]
        assert data["notes"] == PLACE_DATA["notes"]

    def test_update_returns_full_response_shape(self, client, auth_headers, trip_id, place_id):
        resp = client.patch(f"/api/places/{place_id}", json={"name": "Акихабара"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        for field in ("id", "trip_id", "user_id", "name", "visited_at", "latitude", "longitude", "notes", "created_at"):
            assert field in data
        assert data["trip_id"] == trip_id

    def test_update_persists(self, client, auth_headers, trip_id, place_id):
        client.patch(f"/api/places/{place_id}", json={"name": "Гинза"}, headers=auth_headers)
        places = client.get(f"/api/trips/{trip_id}/places", headers=auth_headers).json()
        assert places[0]["name"] == "Гинза"

    def test_update_no_auth(self, client, place_id):
        resp = client.patch(f"/api/places/{place_id}", json={"name": "X"})
        assert resp.status_code == 401

    def test_update_not_found(self, client, auth_headers):
        resp = client.patch(
            "/api/places/00000000-0000-0000-0000-000000000000",
            json={"name": "X"},
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert resp.json()["error"] == "NOT_FOUND"

    def test_update_other_users_place(self, client, auth_headers, other_user_headers, place_id):
        resp = client.patch(f"/api/places/{place_id}", json={"name": "X"}, headers=other_user_headers)
        assert resp.status_code == 404

    def test_update_invalid_latitude_above_90(self, client, auth_headers, place_id):
        resp = client.patch(f"/api/places/{place_id}", json={"latitude": "91.0"}, headers=auth_headers)
        assert resp.status_code == 400
        assert resp.json()["error"] == "INVALID_COORDINATES"

    def test_update_invalid_latitude_below_minus_90(self, client, auth_headers, place_id):
        resp = client.patch(f"/api/places/{place_id}", json={"latitude": "-90.1"}, headers=auth_headers)
        assert resp.status_code == 400
        assert resp.json()["error"] == "INVALID_COORDINATES"

    def test_update_invalid_longitude_above_180(self, client, auth_headers, place_id):
        resp = client.patch(f"/api/places/{place_id}", json={"longitude": "180.1"}, headers=auth_headers)
        assert resp.status_code == 400
        assert resp.json()["error"] == "INVALID_COORDINATES"

    def test_update_invalid_longitude_below_minus_180(self, client, auth_headers, place_id):
        resp = client.patch(f"/api/places/{place_id}", json={"longitude": "-181.0"}, headers=auth_headers)
        assert resp.status_code == 400
        assert resp.json()["error"] == "INVALID_COORDINATES"

    def test_update_boundary_coordinates(self, client, auth_headers, place_id):
        resp = client.patch(
            f"/api/places/{place_id}",
            json={"latitude": "90.0", "longitude": "-180.0"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_update_only_latitude_invalid_uses_existing_longitude(self, client, auth_headers, place_id):
        resp = client.patch(f"/api/places/{place_id}", json={"latitude": "95.0"}, headers=auth_headers)
        assert resp.status_code == 400
        assert resp.json()["error"] == "INVALID_COORDINATES"

    def test_update_only_longitude_invalid_uses_existing_latitude(self, client, auth_headers, place_id):
        resp = client.patch(f"/api/places/{place_id}", json={"longitude": "200.0"}, headers=auth_headers)
        assert resp.status_code == 400
        assert resp.json()["error"] == "INVALID_COORDINATES"

    def test_update_no_coordinates_skips_validation(self, client, auth_headers, place_id):
        resp = client.patch(f"/api/places/{place_id}", json={"name": "Без координат"}, headers=auth_headers)
        assert resp.status_code == 200


class TestDeletePlace:
    def test_delete_success(self, client, auth_headers, trip_id, place_id):
        resp = client.delete(f"/api/places/{place_id}", headers=auth_headers)
        assert resp.status_code == 204

        resp = client.get(f"/api/trips/{trip_id}/places", headers=auth_headers)
        assert resp.json() == []

    def test_delete_not_found(self, client, auth_headers):
        resp = client.delete("/api/places/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert resp.status_code == 404
        assert resp.json()["error"] == "NOT_FOUND"

    def test_delete_no_auth(self, client, place_id):
        resp = client.delete(f"/api/places/{place_id}")
        assert resp.status_code == 401

    def test_delete_other_users_place(self, client, auth_headers, other_user_headers, trip_id, place_id):
        resp = client.delete(f"/api/places/{place_id}", headers=other_user_headers)
        assert resp.status_code == 404

        resp = client.get(f"/api/trips/{trip_id}/places", headers=auth_headers)
        assert len(resp.json()) == 1
