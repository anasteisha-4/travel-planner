class TestRegister:
    """POST /api/auth/register"""

    def test_register_success(self, client, test_user_data):
        """Valid registration returns tokens"""
        response = client.post("/api/auth/register", json=test_user_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email(self, client, test_user, test_user_data):
        """Duplicate email returns 400"""
        new_data = {**test_user_data, "login": "different_login"}
        response = client.post("/api/auth/register", json=new_data)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_register_duplicate_login(self, client, test_user, test_user_data):
        """Duplicate login returns 400"""
        new_data = {**test_user_data, "email": "different@example.com"}
        response = client.post("/api/auth/register", json=new_data)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_register_invalid_email(self, client, test_user_data):
        """Invalid email format returns 422"""
        test_user_data["email"] = "not-an-email"
        response = client.post("/api/auth/register", json=test_user_data)
        assert response.status_code == 422

    def test_register_missing_fields(self, client):
        """Missing required fields returns 422"""
        response = client.post("/api/auth/register", json={"email": "test@example.com"})
        assert response.status_code == 422


class TestLogin:
    """POST /api/auth/login"""

    def test_login_by_email(self, client, test_user, test_user_data):
        """Login by email returns tokens"""
        response = client.post("/api/auth/login", json={
            "identifier": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "refresh_token" in response.json()

    def test_login_by_login(self, client, test_user, test_user_data):
        """Login by login returns tokens"""
        response = client.post("/api/auth/login", json={
            "identifier": test_user_data["login"],
            "password": test_user_data["password"]
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_wrong_password(self, client, test_user, test_user_data):
        """Wrong password returns 400"""
        response = client.post("/api/auth/login", json={
            "identifier": test_user_data["email"],
            "password": "WrongPassword123"
        })
        assert response.status_code == 400
        assert "Incorrect credentials" in response.json()["detail"]

    def test_login_nonexistent_user(self, test_user, client):
        """Non-existent user returns 400"""
        response = client.post("/api/auth/login", json={
            "identifier": "nobody@example.com",
            "password": "SomePassword123"
        })
        assert response.status_code == 400
        assert "Incorrect credentials" in response.json()["detail"]


class TestRefresh:
    """POST /api/auth/refresh"""

    def test_refresh_success(self, client, test_user):
        """Valid refresh token returns new tokens"""
        response = client.post("/api/auth/refresh", json={
            "refresh_token": test_user["refresh_token"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["refresh_token"] != test_user["refresh_token"]

    def test_refresh_invalid_token(self, client, test_user):
        """Invalid token returns 401"""
        response = client.post("/api/auth/refresh", json={
            "refresh_token": "invalid.token.here"
        })
        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]

    def test_refresh_with_access_token(self, client, test_user):
        """Using access token instead of refresh returns 401"""
        response = client.post("/api/auth/refresh", json={
            "refresh_token": test_user["access_token"]
        })
        assert response.status_code == 401
        assert "Invalid token type" in response.json()["detail"]

    def test_refresh_revoked_token(self, client, test_user):
        """Using already-used refresh token returns 401"""
        response1 = client.post("/api/auth/refresh", json={
            "refresh_token": test_user["refresh_token"]
        })
        assert response1.status_code == 200

        response2 = client.post("/api/auth/refresh", json={
            "refresh_token": test_user["refresh_token"]
        })
        assert response2.status_code == 401
        assert "revoked" in response2.json()["detail"]


class TestPasswordChange:
    """POST /api/auth/password/change"""

    def test_password_change_success(self, client, test_user, auth_headers, test_user_data):
        """Valid password change succeeds"""
        new_password = "NewSecure456!"
        response = client.post(
            "/api/auth/password/change",
            json={"old_password": test_user_data["password"], "new_password": new_password},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert "successfully" in response.json()["message"]

        login_response = client.post("/api/auth/login", json={
            "identifier": test_user_data["email"],
            "password": new_password
        })
        assert login_response.status_code == 200

    def test_password_change_wrong_old(self, client, auth_headers):
        """Wrong old password returns 400"""
        response = client.post(
            "/api/auth/password/change",
            json={"old_password": "WrongOldPassword", "new_password": "NewPass123!"},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "Incorrect old password" in response.json()["detail"]

    def test_password_change_no_auth(self, client):
        """No authorization returns 401"""
        response = client.post(
            "/api/auth/password/change",
            json={"old_password": "old", "new_password": "new"}
        )
        assert response.status_code == 401


class TestLogout:
    """POST /api/auth/logout"""

    def test_logout_success(self, client, test_user, auth_headers):
        """Logout revokes refresh token"""
        response = client.post(
            "/api/auth/logout",
            json={"refresh_token": test_user["refresh_token"]},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert "successfully" in response.json()["message"]

        refresh_response = client.post("/api/auth/refresh", json={
            "refresh_token": test_user["refresh_token"]
        })
        assert refresh_response.status_code == 401

    def test_logout_blacklists_access_token(self, client, test_user, auth_headers):
        """Logout with access token blacklists it"""
        response = client.post(
            "/api/auth/logout",
            json={"refresh_token": test_user["refresh_token"]},
            headers=auth_headers
        )
        assert response.status_code == 200

        profile_response = client.get("/api/users/me", headers=auth_headers)
        assert profile_response.status_code == 401
        assert "revoked" in profile_response.json()["detail"]

    def test_logout_invalid_refresh(self, test_user, client):
        """Logout with invalid refresh token succeeds"""
        response = client.post(
            "/api/auth/logout",
            json={"refresh_token": "invalid.token"}
        )
        assert response.status_code == 200


class TestLogoutAll:
    """POST /api/auth/logout-all"""

    def test_logout_all_success(self, client, test_user, auth_headers, test_user_data):
        """Logout-all revokes all sessions"""
        # Login again to create second session
        login_response = client.post("/api/auth/login", json={
            "identifier": test_user_data["email"],
            "password": test_user_data["password"]
        })
        second_refresh = login_response.json()["refresh_token"]

        response = client.post("/api/auth/logout-all", headers=auth_headers)
        assert response.status_code == 200
        assert "sessions revoked" in response.json()["message"]

        for token in [test_user["refresh_token"], second_refresh]:
            refresh_response = client.post("/api/auth/refresh", json={
                "refresh_token": token
            })
            assert refresh_response.status_code == 401

    def test_logout_all_no_auth(self, client):
        """Logout-all without auth returns 401"""
        response = client.post("/api/auth/logout-all")
        assert response.status_code == 401
