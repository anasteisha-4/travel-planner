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
