from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import jwt
from httpx import AsyncClient

from app.core.config import settings


class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "newuser@example.com", "password": "strongpass1"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newuser@example.com"
        assert "id" in data
        assert "password" not in data
        assert "password_hash" not in data

    async def test_register_duplicate_email(self, client: AsyncClient, registered_user):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "anotherpass1"},
        )
        assert resp.status_code == 409

    async def test_register_weak_password(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "weak@example.com", "password": "short"},
        )
        assert resp.status_code == 422

    async def test_register_invalid_email(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "strongpass1"},
        )
        assert resp.status_code == 422


class TestLogin:
    async def test_login_success(self, client: AsyncClient, registered_user):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "securepass123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "password" not in data
        assert "password_hash" not in data

    async def test_login_wrong_password(self, client: AsyncClient, registered_user):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid credentials"

    async def test_login_unknown_email(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "doesntmatter"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid credentials"

    async def test_login_wrong_password_same_message_as_unknown(
        self, client: AsyncClient, registered_user
    ):
        wrong_pw = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )
        unknown = await client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@example.com", "password": "doesntmatter"},
        )
        assert wrong_pw.json()["detail"] == unknown.json()["detail"]

    async def test_login_timing_equalized(self, client: AsyncClient, registered_user):
        from app.core.security import verify_password as real_verify

        with patch("app.services.auth.verify_password", wraps=real_verify) as mock_verify:
            await client.post(
                "/api/v1/auth/login",
                json={"email": "nobody@example.com", "password": "doesntmatter"},
            )
            assert mock_verify.call_count == 1, "verify_password must run for unknown emails"

            mock_verify.reset_mock()
            await client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "wrongpassword"},
            )
            assert mock_verify.call_count == 1, "verify_password must run for wrong passwords"


class TestMe:
    async def test_me_with_valid_token(self, client: AsyncClient, auth_tokens):
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert "id" in data
        assert "password" not in data
        assert "password_hash" not in data

    async def test_me_no_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_me_expired_token(self, client: AsyncClient, registered_user):
        expired_payload = {
            "sub": registered_user["id"],
            "exp": datetime.now(UTC) - timedelta(minutes=1),
            "iat": datetime.now(UTC) - timedelta(minutes=16),
            "type": "access",
        }
        expired_token = jwt.encode(
            expired_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401

    async def test_me_invalid_token(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer garbage.token.here"},
        )
        assert resp.status_code == 401


class TestRefresh:
    async def test_refresh_success(self, client: AsyncClient, auth_tokens):
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": auth_tokens["refresh_token"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["refresh_token"] != auth_tokens["refresh_token"]

    async def test_old_refresh_rejected_after_rotation(self, client: AsyncClient, auth_tokens):
        old_refresh = auth_tokens["refresh_token"]
        resp1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
        assert resp1.status_code == 200

        resp2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
        assert resp2.status_code == 401

    async def test_refresh_invalid_token(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "bogus.token.value"}
        )
        assert resp.status_code == 401


class TestLogout:
    async def test_logout_revokes_refresh(self, client: AsyncClient, auth_tokens):
        resp = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": auth_tokens["refresh_token"]},
        )
        assert resp.status_code == 204

        resp2 = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": auth_tokens["refresh_token"]},
        )
        assert resp2.status_code == 401

    async def test_logout_invalid_token(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/logout", json={"refresh_token": "bogus.token.value"})
        assert resp.status_code == 401
