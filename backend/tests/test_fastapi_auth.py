"""Tests for /api/v1/auth endpoints."""

import pytest
from app.auth.service import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    validate_password_strength,
)
from tests.conftest import _TEST_SECRET


class TestPasswordHashing:
    def test_hash_and_verify(self):
        plain = "SecurePass123"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("Correct123")
        assert not verify_password("Wrong123", hashed)


class TestJWTTokens:
    def test_create_and_decode_access(self):
        token = create_access_token(42, "user", _TEST_SECRET, 15)
        payload = decode_token(token, _TEST_SECRET)
        assert payload["sub"] == "42"
        assert payload["role"] == "user"
        assert payload["type"] == "access"

    def test_create_and_decode_refresh(self):
        token = create_refresh_token(42, _TEST_SECRET, 7)
        payload = decode_token(token, _TEST_SECRET)
        assert payload["sub"] == "42"
        assert payload["type"] == "refresh"

    def test_decode_invalid_token_raises(self):
        from jose import JWTError

        with pytest.raises(JWTError):
            decode_token("invalid.token.here", _TEST_SECRET)


class TestPasswordValidation:
    def test_valid_password(self):
        ok, err = validate_password_strength("SecurePass123")
        assert ok is True
        assert err is None

    def test_short_password(self):
        ok, err = validate_password_strength("Ab1")
        assert ok is False
        assert "8 characters" in err

    def test_empty_password(self):
        ok, err = validate_password_strength("")
        assert ok is False

    def test_no_number(self):
        ok, err = validate_password_strength("OnlyLettersHere")
        assert ok is False

    def test_no_letter(self):
        ok, err = validate_password_strength("123456789")
        assert ok is False


class TestLoginEndpoint:
    def test_login_success(self, client, test_user):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "TestPass123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "WrongPass123"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client, seed_roles):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "nobody", "password": "NoPass123"},
        )
        assert resp.status_code == 401


class TestLogoutEndpoint:
    def test_logout(self, client):
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Logged out successfully"


class TestMeEndpoint:
    def test_me_authenticated(self, client, auth_headers):
        resp = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"
        assert data["role"] == "user"

    def test_me_unauthenticated(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code in (401, 403)


class TestRefreshEndpoint:
    def test_refresh_without_cookie(self, client):
        resp = client.post("/api/v1/auth/refresh")
        assert resp.status_code == 401

    def test_refresh_with_invalid_cookie(self, client):
        client.cookies.set("refresh_token", "invalid.token")
        resp = client.post("/api/v1/auth/refresh")
        assert resp.status_code == 401

    def test_refresh_with_access_token_type(self, client, test_user):
        # Use an access token as refresh — should fail (wrong type)
        token = create_access_token(
            test_user.id, test_user.role.name, _TEST_SECRET, 60
        )
        client.cookies.set("refresh_token", token)
        resp = client.post("/api/v1/auth/refresh")
        assert resp.status_code == 401

    def test_refresh_success(self, client, test_user):
        token = create_refresh_token(test_user.id, _TEST_SECRET, 7)
        client.cookies.set("refresh_token", token)
        resp = client.post("/api/v1/auth/refresh")
        assert resp.status_code == 200
        assert "access_token" in resp.json()


class TestLoginInactiveUser:
    def test_login_inactive_user(self, client, db_session, test_user):
        # Deactivate the user
        test_user.status = "inactive"
        db_session.commit()

        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "TestPass123"},
        )
        assert resp.status_code == 401
        assert "not active" in resp.json()["detail"]
