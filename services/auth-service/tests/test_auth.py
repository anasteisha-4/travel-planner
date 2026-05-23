import unittest.mock
from urllib.parse import parse_qs, urlparse


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
        assert "already registered" in response.json()["message"]

    def test_register_duplicate_login(self, client, test_user, test_user_data):
        """Duplicate login returns 400"""
        new_data = {**test_user_data, "email": "different@example.com"}
        response = client.post("/api/auth/register", json=new_data)
        assert response.status_code == 400
        assert "already registered" in response.json()["message"]

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
        response = client.post(
            "/api/auth/login", json={"identifier": test_user_data["email"], "password": test_user_data["password"]}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "refresh_token" in response.json()

    def test_login_by_login(self, client, test_user, test_user_data):
        """Login by login returns tokens"""
        response = client.post(
            "/api/auth/login", json={"identifier": test_user_data["login"], "password": test_user_data["password"]}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_wrong_password(self, client, test_user, test_user_data):
        """Wrong password returns 400"""
        response = client.post(
            "/api/auth/login", json={"identifier": test_user_data["email"], "password": "WrongPassword123"}
        )
        assert response.status_code == 400
        assert "Incorrect credentials" in response.json()["message"]

    def test_login_nonexistent_user(self, test_user, client):
        """Non-existent user returns 400"""
        response = client.post(
            "/api/auth/login", json={"identifier": "nobody@example.com", "password": "SomePassword123"}
        )
        assert response.status_code == 400
        assert "Incorrect credentials" in response.json()["message"]


class TestYandexAuthorize:
    """GET /api/auth/yandex/authorize"""

    def test_yandex_authorize_uses_canonical_www_redirect_for_apex_origin(self, client, monkeypatch):
        from app.config import settings

        monkeypatch.setattr(settings, "YANDEX_CLIENT_ID", "test-client-id")
        monkeypatch.setattr(settings, "YANDEX_REDIRECT_URI", "https://www.triply-ai.ru/auth/yandex/callback")
        monkeypatch.setattr(settings, "FRONTEND_URL", "https://www.triply-ai.ru")
        monkeypatch.setattr(settings, "CORS_ORIGINS", "https://triply-ai.ru,https://www.triply-ai.ru")

        response = client.get("/api/auth/yandex/authorize?origin=https%3A%2F%2Ftriply-ai.ru", follow_redirects=False)

        assert response.status_code == 302
        redirect_query = parse_qs(urlparse(response.headers["location"]).query)
        assert redirect_query["redirect_uri"] == ["https://www.triply-ai.ru/auth/yandex/callback"]

    def test_yandex_authorize_keeps_allowed_local_origin(self, client, monkeypatch):
        from app.config import settings

        monkeypatch.setattr(settings, "YANDEX_CLIENT_ID", "test-client-id")
        monkeypatch.setattr(settings, "YANDEX_REDIRECT_URI", "http://localhost/auth/yandex/callback")
        monkeypatch.setattr(settings, "FRONTEND_URL", "http://localhost")
        monkeypatch.setattr(settings, "CORS_ORIGINS", "http://localhost:5173")

        response = client.get("/api/auth/yandex/authorize?origin=http%3A%2F%2Flocalhost%3A5173", follow_redirects=False)

        assert response.status_code == 302
        redirect_query = parse_qs(urlparse(response.headers["location"]).query)
        assert redirect_query["redirect_uri"] == ["http://localhost:5173/auth/yandex/callback"]

    def test_yandex_redirect_uri_candidates_include_paired_www_domain(self):
        from app.routers.auth import _yandex_redirect_uri_candidates

        assert _yandex_redirect_uri_candidates("https://www.triply-ai.ru/auth/yandex/callback") == [
            "https://www.triply-ai.ru/auth/yandex/callback",
            "https://triply-ai.ru/auth/yandex/callback",
        ]


class TestRefresh:
    """POST /api/auth/refresh"""

    def test_refresh_success(self, client, test_user):
        """Valid refresh token returns new tokens"""
        response = client.post("/api/auth/refresh", json={"refresh_token": test_user["refresh_token"]})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["refresh_token"] != test_user["refresh_token"]

    def test_refresh_invalid_token(self, client, test_user):
        """Invalid token returns 401"""
        response = client.post("/api/auth/refresh", json={"refresh_token": "invalid.token.here"})
        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["message"]

    def test_refresh_with_access_token(self, client, test_user):
        """Using access token instead of refresh returns 401"""
        response = client.post("/api/auth/refresh", json={"refresh_token": test_user["access_token"]})
        assert response.status_code == 401
        assert "Invalid token type" in response.json()["message"]

    def test_refresh_revoked_token(self, client, test_user):
        """Using already-used refresh token returns 401"""
        response1 = client.post("/api/auth/refresh", json={"refresh_token": test_user["refresh_token"]})
        assert response1.status_code == 200

        response2 = client.post("/api/auth/refresh", json={"refresh_token": test_user["refresh_token"]})
        assert response2.status_code == 401
        assert "revoked" in response2.json()["message"]


class TestPasswordChange:
    """POST /api/auth/password/change"""

    def test_password_change_success(self, client, test_user, auth_headers, test_user_data):
        """Valid password change succeeds"""
        new_password = "NewSecure456!"
        response = client.post(
            "/api/auth/password/change",
            json={"old_password": test_user_data["password"], "new_password": new_password},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "successfully" in response.json()["message"]

        login_response = client.post(
            "/api/auth/login", json={"identifier": test_user_data["email"], "password": new_password}
        )
        assert login_response.status_code == 200

    def test_password_change_wrong_old(self, client, auth_headers):
        """Wrong old password returns 400"""
        response = client.post(
            "/api/auth/password/change",
            json={"old_password": "WrongOldPassword", "new_password": "NewPass123!"},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "Incorrect old password" in response.json()["message"]

    def test_password_change_no_auth(self, client):
        """No authorization returns 401"""
        response = client.post("/api/auth/password/change", json={"old_password": "old", "new_password": "new"})
        assert response.status_code == 401


class TestLogout:
    """POST /api/auth/logout"""

    def test_logout_success(self, client, test_user, auth_headers):
        """Logout revokes refresh token"""
        response = client.post(
            "/api/auth/logout", json={"refresh_token": test_user["refresh_token"]}, headers=auth_headers
        )
        assert response.status_code == 200
        assert "successfully" in response.json()["message"]

        refresh_response = client.post("/api/auth/refresh", json={"refresh_token": test_user["refresh_token"]})
        assert refresh_response.status_code == 401

    def test_logout_blacklists_access_token(self, client, test_user, auth_headers):
        """Logout with access token blacklists it"""
        response = client.post(
            "/api/auth/logout", json={"refresh_token": test_user["refresh_token"]}, headers=auth_headers
        )
        assert response.status_code == 200

        profile_response = client.get("/api/users/me", headers=auth_headers)
        assert profile_response.status_code == 401
        assert "revoked" in profile_response.json()["message"]

    def test_logout_invalid_refresh(self, test_user, client):
        """Logout with invalid refresh token succeeds"""
        response = client.post("/api/auth/logout", json={"refresh_token": "invalid.token"})
        assert response.status_code == 200


class TestLogoutAll:
    """POST /api/auth/logout-all"""

    def test_logout_all_success(self, client, test_user, auth_headers, test_user_data):
        """Logout-all revokes all sessions"""
        # Login again to create second session
        login_response = client.post(
            "/api/auth/login", json={"identifier": test_user_data["email"], "password": test_user_data["password"]}
        )
        second_refresh = login_response.json()["refresh_token"]

        response = client.post("/api/auth/logout-all", headers=auth_headers)
        assert response.status_code == 200
        assert "sessions revoked" in response.json()["message"]

        for token in [test_user["refresh_token"], second_refresh]:
            refresh_response = client.post("/api/auth/refresh", json={"refresh_token": token})
            assert refresh_response.status_code == 401

    def test_logout_all_no_auth(self, client):
        """Logout-all without auth returns 401"""
        response = client.post("/api/auth/logout-all")
        assert response.status_code == 401


class TestPasswordReset:
    """POST /api/auth/password/forgot and /api/auth/password/reset"""

    def test_forgot_password_existing_email(self, client, test_user, test_user_data):
        """Forgot password for registered email returns 200"""
        with unittest.mock.patch("app.routers.auth.send_password_reset_email", return_value=True) as mock_send:
            response = client.post("/api/auth/password/forgot", json={"email": test_user_data["email"]})
            assert response.status_code == 200
            assert "reset link" in response.json()["message"]
            mock_send.assert_called_once()

    def test_forgot_password_unknown_email(self, client, test_user):
        """Forgot password for unknown email still returns 200 (no leak)"""
        response = client.post("/api/auth/password/forgot", json={"email": "nobody@example.com"})
        assert response.status_code == 200
        assert "reset link" in response.json()["message"]

    def test_forgot_password_yandex_only_user(self, client, fake_redis):
        """Forgot password for Yandex-only user (no password_hash) returns 200 but no email sent"""
        from app import models
        from app.database import get_db

        db = next(client.app.dependency_overrides[get_db]())
        yandex_user = models.User(email="yandex@example.com", login="yandex_user", yandex_id="123", password_hash=None)
        db.add(yandex_user)
        db.commit()

        with unittest.mock.patch("app.routers.auth.send_password_reset_email") as mock_send:
            response = client.post("/api/auth/password/forgot", json={"email": "yandex@example.com"})
            assert response.status_code == 200
            mock_send.assert_not_called()
        db.close()

    def test_reset_password_success(self, client, test_user, test_user_data, fake_redis):
        """Valid reset token allows password change"""
        from app import redis_client

        token = "test-reset-token-123"
        redis_client.store_reset_token(token, str(test_user["access_token"]))

        # Get real user_id from the token
        from app.utils import decode_token

        payload = decode_token(test_user["access_token"])
        user_id = payload["sub"]
        redis_client.store_reset_token(token, user_id)

        new_password = "BrandNew789!"
        response = client.post(
            "/api/auth/password/reset",
            json={"token": token, "new_password": new_password, "confirm_password": new_password},
        )
        assert response.status_code == 200
        assert "successfully" in response.json()["message"]

        # Verify new password works
        login_response = client.post(
            "/api/auth/login", json={"identifier": test_user_data["email"], "password": new_password}
        )
        assert login_response.status_code == 200

    def test_reset_password_mismatch(self, client, test_user, fake_redis):
        """Mismatched passwords return 422"""
        response = client.post(
            "/api/auth/password/reset",
            json={"token": "any-token", "new_password": "NewPass123!", "confirm_password": "Different123!"},
        )
        assert response.status_code == 422

    def test_reset_password_same_as_old(self, client, test_user, test_user_data, fake_redis):
        """Same password as current returns 400"""
        from app import redis_client
        from app.utils import decode_token

        token = "test-same-password-token"
        payload = decode_token(test_user["access_token"])
        user_id = payload["sub"]
        redis_client.store_reset_token(token, user_id)

        response = client.post(
            "/api/auth/password/reset",
            json={
                "token": token,
                "new_password": test_user_data["password"],
                "confirm_password": test_user_data["password"],
            },
        )
        assert response.status_code == 400
        assert "differ" in response.json()["message"]

    def test_reset_password_weak(self, client, test_user, fake_redis):
        """Weak password returns 422"""
        response = client.post(
            "/api/auth/password/reset",
            json={"token": "any-token", "new_password": "weak", "confirm_password": "weak"},
        )
        assert response.status_code == 422

    def test_reset_password_invalid_token(self, client, test_user, fake_redis):
        """Invalid/expired token returns 400"""
        response = client.post(
            "/api/auth/password/reset",
            json={"token": "nonexistent-token", "new_password": "ValidNew123!", "confirm_password": "ValidNew123!"},
        )
        assert response.status_code == 400
        assert "Invalid" in response.json()["message"]

    def test_reset_password_token_reuse(self, client, test_user, test_user_data, fake_redis):
        """Used reset token cannot be reused"""
        from app import redis_client
        from app.utils import decode_token

        token = "test-reuse-token"
        payload = decode_token(test_user["access_token"])
        user_id = payload["sub"]
        redis_client.store_reset_token(token, user_id)

        # First use — success
        new_password = "FirstNew789!"
        response1 = client.post(
            "/api/auth/password/reset",
            json={"token": token, "new_password": new_password, "confirm_password": new_password},
        )
        assert response1.status_code == 200

        # Second use — fail
        response2 = client.post(
            "/api/auth/password/reset",
            json={"token": token, "new_password": "SecondNew789!", "confirm_password": "SecondNew789!"},
        )
        assert response2.status_code == 400
