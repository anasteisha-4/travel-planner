class TestCreateTrip:
    def test_create_success(self, client, auth_headers, trip_data):
        response = client.post("/api/trips/", json=trip_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == trip_data["title"]
        assert data["destination"] == trip_data["destination"]
        assert data["status"] == "planned"
        assert data["people_count"] == 2
        assert "id" in data

    def test_create_minimal(self, client, auth_headers):
        minimal = {
            "title": "Быстрая поездка",
            "destination": "Москва",
            "start_date": "2026-07-01",
            "end_date": "2026-07-03",
        }
        response = client.post("/api/trips/", json=minimal, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["currency"] == "RUB"
        assert data["people_count"] == 1
        assert data["budget"] is None

    def test_create_no_auth(self, client, trip_data):
        response = client.post("/api/trips/", json=trip_data)
        assert response.status_code == 401


class TestListTrips:
    def test_list_empty(self, client, auth_headers):
        response = client.get("/api/trips/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_with_trips(self, client, auth_headers, trip_data):
        client.post("/api/trips/", json=trip_data, headers=auth_headers)
        client.post("/api/trips/", json={**trip_data, "title": "Вторая"}, headers=auth_headers)

        response = client.get("/api/trips/", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_list_filter_by_status(self, client, auth_headers, trip_data):
        resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
        trip_id = resp.json()["id"]

        client.put(f"/api/trips/{trip_id}", json={"status": "completed"}, headers=auth_headers)

        response = client.get("/api/trips/?status=completed", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1

        response = client.get("/api/trips/?status=planned", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 0

    def test_list_only_own_trips(self, client, auth_headers, other_user_headers, trip_data):
        client.post("/api/trips/", json=trip_data, headers=auth_headers)
        client.post("/api/trips/", json={**trip_data, "title": "Чужая"}, headers=other_user_headers)

        response = client.get("/api/trips/", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["title"] == trip_data["title"]


class TestGetTrip:
    def test_get_success(self, client, auth_headers, trip_data):
        resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
        trip_id = resp.json()["id"]

        response = client.get(f"/api/trips/{trip_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["title"] == trip_data["title"]

    def test_get_not_found(self, client, auth_headers):
        response = client.get("/api/trips/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert response.status_code == 404

    def test_get_other_users_trip(self, client, auth_headers, other_user_headers, trip_data):
        resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
        trip_id = resp.json()["id"]

        response = client.get(f"/api/trips/{trip_id}", headers=other_user_headers)
        assert response.status_code == 404


class TestUpdateTrip:
    def test_update_title(self, client, auth_headers, trip_data):
        resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
        trip_id = resp.json()["id"]

        response = client.put(f"/api/trips/{trip_id}", json={"title": "Новое название"}, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["title"] == "Новое название"
        assert response.json()["destination"] == trip_data["destination"]

    def test_update_status(self, client, auth_headers, trip_data):
        resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
        trip_id = resp.json()["id"]

        response = client.put(f"/api/trips/{trip_id}", json={"status": "active"}, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "active"

    def test_update_not_found(self, client, auth_headers):
        response = client.put(
            "/api/trips/00000000-0000-0000-0000-000000000000", json={"title": "Test"}, headers=auth_headers
        )
        assert response.status_code == 404


class TestDeleteTrip:
    def test_delete_success(self, client, auth_headers, trip_data):
        resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
        trip_id = resp.json()["id"]

        response = client.delete(f"/api/trips/{trip_id}", headers=auth_headers)
        assert response.status_code == 204

        response = client.get(f"/api/trips/{trip_id}", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_not_found(self, client, auth_headers):
        response = client.delete("/api/trips/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_other_users_trip(self, client, auth_headers, other_user_headers, trip_data):
        resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
        trip_id = resp.json()["id"]

        response = client.delete(f"/api/trips/{trip_id}", headers=other_user_headers)
        assert response.status_code == 404

        response = client.get(f"/api/trips/{trip_id}", headers=auth_headers)
        assert response.status_code == 200
