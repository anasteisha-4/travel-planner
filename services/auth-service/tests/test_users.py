class TestGetProfile:
    """GET /api/users/me"""

    def test_get_profile_success(self, client, auth_headers, test_user_data):
        """Valid token returns user profile"""
        response = client.get("/api/users/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["login"] == test_user_data["login"]
        assert data["first_name"] == test_user_data["first_name"]
        assert data["last_name"] == test_user_data["last_name"]
        assert "id" in data

    def test_get_profile_no_auth(self, client):
        """No authorization returns 401"""
        response = client.get("/api/users/me")
        assert response.status_code == 401

    def test_get_profile_invalid_token(self, client):
        """Invalid token returns 401"""
        response = client.get(
            "/api/users/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert response.status_code == 401


class TestUpdateProfile:
    """PUT /api/users/me"""

    def test_update_first_name(self, client, auth_headers):
        """Update first_name succeeds"""
        first_name = "NewFirstName"
        response = client.put(
            "/api/users/me",
            json={"first_name": first_name},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["first_name"] == first_name

    def test_update_last_name(self, client, auth_headers):
        """Update last_name succeeds"""
        last_name = "NewLastName"
        response = client.put(
            "/api/users/me",
            json={"last_name": last_name},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["last_name"] == last_name

    def test_update_email_success(self, client, auth_headers):
        """Update email with unique value succeeds"""
        email = "newemail@example.com"
        response = client.put(
            "/api/users/me",
            json={"email": email},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["email"] == email

    def test_update_email_duplicate(self, client,  auth_headers, second_user_data):
        """Update email to existing email returns 400"""
        client.post("/api/auth/register", json=second_user_data)

        response = client.put(
            "/api/users/me",
            json={"email": second_user_data["email"]},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "already taken" in response.json()["detail"]

    def test_update_login_success(self, client, auth_headers):
        """Update login with unique value succeeds"""
        login = "newlogin"
        response = client.put(
            "/api/users/me",
            json={"login": login},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["login"] == "newlogin"

    def test_update_login_duplicate(self, client, auth_headers, second_user_data):
        """Update login to existing login returns 400"""
        client.post("/api/auth/register", json=second_user_data)

        response = client.put(
            "/api/users/me",
            json={"login": second_user_data["login"]},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "already taken" in response.json()["detail"]

    def test_update_no_auth(self, client):
        """Update without auth returns 401"""
        response = client.put("/api/users/me", json={"first_name": "Test"})
        assert response.status_code == 401


class TestGetPreferences:
    """GET /api/users/me/preferences"""

    def test_get_preferences_default(self, client, auth_headers):
        """New user gets default preferences if not set"""
        response = client.get("/api/users/me/preferences", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["budget_preference"] == "medium"
        assert data["interests"] == []
        assert data["travel_styles"] == []

    def test_get_preferences_no_auth(self, client):
        """No auth returns 401"""
        response = client.get("/api/users/me/preferences")
        assert response.status_code == 401


class TestUpdatePreferences:
    """PUT /api/users/me/preferences"""

    def test_update_preferences_success(self, client, auth_headers):
        """Update preferences succeeds"""
        preferences = {
            "interests": ["nature", "culture", "food"],
            "budget_preference": "high",
            "travel_styles": ["adventure", "relaxation"],
            "currency": "USD"
        }
        response = client.put(
            "/api/users/me/preferences",
            json=preferences,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["interests"] == preferences["interests"]
        assert data["budget_preference"] == preferences["budget_preference"]
        assert data["travel_styles"] == preferences["travel_styles"]

    def test_update_preferences_persists(self, client, auth_headers):
        """Updated preferences persist on subsequent get"""
        preferences = {
            "interests": ["history"],
            "budget_preference": "low",
            "travel_styles": ["solo"],
            "currency": "EUR"
        }
        client.put("/api/users/me/preferences", json=preferences, headers=auth_headers)

        response = client.get("/api/users/me/preferences", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["interests"] == ["history"]
        assert data["budget_preference"] == "low"
        assert data["travel_styles"] == ["solo"]

    def test_update_preferences_no_auth(self, client):
        """Update preferences without auth returns 401"""
        response = client.put(
            "/api/users/me/preferences",
            json={"interests": ["test"]}
        )
        assert response.status_code == 401
