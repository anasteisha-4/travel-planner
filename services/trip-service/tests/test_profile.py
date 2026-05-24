class TestProfileOnboarding:
    def test_onboarding_step_saves_normalized_citizenship_code(self, client, auth_headers):
        response = client.post(
            "/api/profile/onboarding/step/3",
            json={
                "origin_city_name": "Москва",
                "origin_lat": 55.7558,
                "origin_lng": 37.6173,
                "citizenship_code": "us",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["citizenship_code"] == "US"
        assert data["origin_city_name"] == "Москва"
        assert data["onboarding_step"] == 3

    def test_onboarding_step_rejects_invalid_citizenship_code(self, client, auth_headers):
        response = client.post(
            "/api/profile/onboarding/step/3",
            json={"citizenship_code": "USA"},
            headers=auth_headers,
        )

        assert response.status_code == 422
