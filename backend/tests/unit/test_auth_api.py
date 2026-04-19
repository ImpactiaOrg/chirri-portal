"""Auth endpoints: login returns JWT + user payload; /me requires auth."""
import pytest


@pytest.mark.django_db
class TestLogin:
    url = "/api/auth/login/"

    def test_valid_credentials_returns_tokens_and_user(self, api_client, balanz_user):
        response = api_client.post(
            self.url,
            {"email": "belen@balanz.com", "password": "balanz2026"},
            format="json",
        )
        assert response.status_code == 200
        body = response.json()
        assert "access" in body and "refresh" in body
        assert body["user"]["email"] == "belen@balanz.com"
        assert body["user"]["client"]["name"] == "Balanz"
        assert body["user"]["role"] == "ADMIN_CLIENT"

    def test_invalid_credentials_returns_401(self, api_client, balanz_user):
        response = api_client.post(
            self.url,
            {"email": "belen@balanz.com", "password": "wrong"},
            format="json",
        )
        assert response.status_code == 401

    def test_unknown_user_returns_401(self, api_client):
        response = api_client.post(
            self.url,
            {"email": "ghost@nowhere.com", "password": "whatever"},
            format="json",
        )
        assert response.status_code == 401


@pytest.mark.django_db
class TestCurrentUser:
    url = "/api/auth/me/"

    def test_anonymous_is_401(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == 401

    def test_authenticated_returns_client_scoped_payload(self, authed_balanz, balanz_user):
        response = authed_balanz.get(self.url)
        assert response.status_code == 200
        body = response.json()
        assert body["email"] == "belen@balanz.com"
        assert body["client"]["name"] == "Balanz"
