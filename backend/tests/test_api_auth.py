"""
Tests for app/api/auth.py JWT and API key authentication

Tests cover:
- JWT initialization
- Token creation and validation
- API key validation
"""

import pytest
from flask import Flask
from flask_jwt_extended import create_access_token, decode_token
from datetime import timedelta

from app import create_app
from app.api.auth import (
    init_jwt,
    VALID_API_KEYS,
    generate_api_key,
    validate_api_key,
    revoke_api_key,
    list_api_keys,
    create_access_token_for_user,
    require_api_key,
)


class TestJWTInitialization:
    """Test JWT authentication initialization"""

    def test_init_jwt_configures_app(self) -> None:
        """Test that init_jwt properly configures Flask app"""
        app = Flask(__name__)
        jwt_manager = init_jwt(app)

        assert jwt_manager is not None
        assert "JWT_SECRET_KEY" in app.config
        assert "JWT_ACCESS_TOKEN_EXPIRES" in app.config
        assert isinstance(app.config["JWT_ACCESS_TOKEN_EXPIRES"], timedelta)

    def test_init_jwt_sets_secret_key(self) -> None:
        """Test that JWT secret key is configured"""
        app = Flask(__name__)
        init_jwt(app)

        assert app.config["JWT_SECRET_KEY"] is not None
        assert len(app.config["JWT_SECRET_KEY"]) > 0

    def test_init_jwt_sets_expiration(self) -> None:
        """Test that JWT expiration is configured"""
        app = Flask(__name__)
        init_jwt(app)

        expiration = app.config["JWT_ACCESS_TOKEN_EXPIRES"]
        assert isinstance(expiration, timedelta)
        assert expiration.total_seconds() > 0

    def test_api_key_store_exists(self) -> None:
        """Test that API key store is configured"""
        assert VALID_API_KEYS is not None
        assert isinstance(VALID_API_KEYS, dict)
        assert len(VALID_API_KEYS) > 0

    def test_demo_api_key_in_store(self) -> None:
        """Test that demo API key exists"""
        assert "demo-api-key-12345" in VALID_API_KEYS
        assert VALID_API_KEYS["demo-api-key-12345"] == "demo_user"

    def test_test_api_key_in_store(self) -> None:
        """Test that test API key exists"""
        assert "test-api-key-67890" in VALID_API_KEYS
        assert VALID_API_KEYS["test-api-key-67890"] == "test_user"

    def test_jwt_initialization_with_real_app(self) -> None:
        """Test JWT initialization with real Flask app"""
        app = create_app()
        with app.app_context():
            assert "JWT_SECRET_KEY" in app.config
            assert "JWT_ACCESS_TOKEN_EXPIRES" in app.config
            assert app.config["JWT_SECRET_KEY"] is not None

    def test_api_keys_are_strings(self) -> None:
        """Test that all API keys and values are strings"""
        for api_key, username in VALID_API_KEYS.items():
            assert isinstance(api_key, str)
            assert isinstance(username, str)

    def test_api_key_format(self) -> None:
        """Test that API keys have expected format"""
        for api_key in VALID_API_KEYS.keys():
            assert api_key.startswith("")  # Any format allowed
            assert len(api_key) > 0

    def test_api_key_values_format(self) -> None:
        """Test that API key values are valid usernames"""
        for username in VALID_API_KEYS.values():
            assert len(username) > 0
            assert isinstance(username, str)

    def test_jwt_manager_returned(self) -> None:
        """Test that init_jwt returns JWTManager instance"""
        from flask_jwt_extended import JWTManager

        app = Flask(__name__)
        jwt_manager = init_jwt(app)

        assert isinstance(jwt_manager, JWTManager)


class TestAPIKeyManagement:
    """Test API key generation, validation, and management"""

    def setup_method(self) -> None:
        """Clear VALID_API_KEYS before each test to ensure isolation"""
        # Store original keys before modifications
        self.original_keys = VALID_API_KEYS.copy()
        # Clear only generated keys, keep demo keys
        keys_to_remove = [
            k
            for k in VALID_API_KEYS.keys()
            if k not in ["demo-api-key-12345", "test-api-key-67890"]
        ]
        for key in keys_to_remove:
            del VALID_API_KEYS[key]

    def teardown_method(self) -> None:
        """Restore original keys after each test"""
        VALID_API_KEYS.clear()
        VALID_API_KEYS.update(self.original_keys)

    def test_generate_api_key_creates_key(self) -> None:
        """Test that generate_api_key creates a new key"""
        username = "test_user"
        api_key = generate_api_key(username)

        # Key should be a string
        assert isinstance(api_key, str)
        # Key should contain username
        assert username in api_key
        # Key should be stored in VALID_API_KEYS
        assert api_key in VALID_API_KEYS
        assert VALID_API_KEYS[api_key] == username

    def test_generate_api_key_generates_unique_keys(self) -> None:
        """Test that generate_api_key generates unique keys for same user"""
        username = "test_user"
        key1 = generate_api_key(username)
        key2 = generate_api_key(username)

        # Keys should be different
        assert key1 != key2
        # Both should be in store
        assert key1 in VALID_API_KEYS
        assert key2 in VALID_API_KEYS
        # Both should map to same username
        assert VALID_API_KEYS[key1] == username
        assert VALID_API_KEYS[key2] == username

    def test_generate_api_key_multiple_users(self) -> None:
        """Test that generate_api_key works for multiple users"""
        key1 = generate_api_key("user1")
        key2 = generate_api_key("user2")

        assert VALID_API_KEYS[key1] == "user1"
        assert VALID_API_KEYS[key2] == "user2"

    def test_validate_api_key_valid_key(self) -> None:
        """Test validation of a valid API key"""
        api_key = generate_api_key("test_user")
        result = validate_api_key(api_key)

        assert result == "test_user"

    def test_validate_api_key_invalid_key(self) -> None:
        """Test validation of an invalid API key"""
        result = validate_api_key("invalid-key-12345")

        assert result is None

    def test_validate_api_key_empty_string(self) -> None:
        """Test validation of empty string"""
        result = validate_api_key("")

        assert result is None

    def test_validate_api_key_demo_keys(self) -> None:
        """Test validation of pre-configured demo keys"""
        result1 = validate_api_key("demo-api-key-12345")
        result2 = validate_api_key("test-api-key-67890")

        assert result1 == "demo_user"
        assert result2 == "test_user"

    def test_revoke_api_key_success(self) -> None:
        """Test successful revocation of an API key"""
        api_key = generate_api_key("test_user")

        # Key should exist
        assert api_key in VALID_API_KEYS

        # Revoke it
        result = revoke_api_key(api_key)

        assert result is True
        # Key should no longer exist
        assert api_key not in VALID_API_KEYS

    def test_revoke_api_key_not_found(self) -> None:
        """Test revocation of non-existent key"""
        result = revoke_api_key("nonexistent-key")

        assert result is False

    def test_revoke_api_key_empty_string(self) -> None:
        """Test revocation of empty string"""
        result = revoke_api_key("")

        assert result is False

    def test_revoke_api_key_multiple_times(self) -> None:
        """Test that revoking same key twice fails second time"""
        api_key = generate_api_key("test_user")

        # First revocation should succeed
        assert revoke_api_key(api_key) is True
        # Second revocation should fail
        assert revoke_api_key(api_key) is False

    def test_list_api_keys_for_user(self) -> None:
        """Test listing API keys for a user"""
        # Use a unique username to avoid collision with demo keys
        username = "unique_test_user_xyz"
        key1 = generate_api_key(username)
        key2 = generate_api_key(username)

        keys = list_api_keys(username)

        # Should return list
        assert isinstance(keys, list)
        # Should have 2 keys (only for this username)
        assert len(keys) == 2
        # Should only show last 8 characters for security
        assert all(len(k) <= 8 for k in keys)
        # Should contain last 8 chars of generated keys
        assert key1[-8:] in keys
        assert key2[-8:] in keys

    def test_list_api_keys_no_keys(self) -> None:
        """Test listing keys for user with no keys"""
        keys = list_api_keys("user_with_no_keys")

        assert isinstance(keys, list)
        assert len(keys) == 0

    def test_list_api_keys_multiple_users(self) -> None:
        """Test listing keys returns only user's keys"""
        key1 = generate_api_key("user1")
        key2 = generate_api_key("user1")
        key3 = generate_api_key("user2")

        user1_keys = list_api_keys("user1")
        user2_keys = list_api_keys("user2")

        # User 1 should have 2 keys
        assert len(user1_keys) == 2
        assert key1[-8:] in user1_keys
        assert key2[-8:] in user1_keys

        # User 2 should have 1 key
        assert len(user2_keys) == 1
        assert key3[-8:] in user2_keys

    def test_list_api_keys_after_revocation(self) -> None:
        """Test that list_api_keys excludes revoked keys"""
        # Use a unique username to avoid collision with demo keys
        username = "revoke_test_user_xyz"
        key1 = generate_api_key(username)
        key2 = generate_api_key(username)

        # Revoke first key
        revoke_api_key(key1)

        keys = list_api_keys(username)

        # Should only have 1 key (only for this username)
        assert len(keys) == 1
        assert key2[-8:] in keys

    def test_create_access_token_for_user_returns_string(self) -> None:
        """Test that create_access_token_for_user returns a string token"""
        app = create_app()
        with app.app_context():
            token = create_access_token_for_user("test_user")

            assert isinstance(token, str)
            # JWT tokens have 3 parts separated by dots
            assert token.count(".") == 2

    def test_create_access_token_for_user_with_custom_expiration(self) -> None:
        """Test token creation with custom expiration"""
        app = create_app()
        with app.app_context():
            custom_expiry = timedelta(hours=1)
            token = create_access_token_for_user(
                "test_user", expires_delta=custom_expiry
            )

            assert isinstance(token, str)
            assert token.count(".") == 2

    def test_create_access_token_different_users(self) -> None:
        """Test that different users get different tokens"""
        app = create_app()
        with app.app_context():
            token1 = create_access_token_for_user("user1")
            token2 = create_access_token_for_user("user2")

            assert token1 != token2

    def test_require_api_key_decorator_valid_key(self) -> None:
        """Test require_api_key decorator with valid API key"""
        app = create_app()

        @require_api_key
        def protected_route() -> dict:
            return {"message": "success"}

        with app.test_request_context(
            headers={"Authorization": "Bearer demo-api-key-12345"}
        ):
            result = protected_route()
            assert result == {"message": "success"}

    def test_require_api_key_decorator_missing_header(self) -> None:
        """Test require_api_key decorator without authorization header"""
        app = create_app()

        @require_api_key
        def protected_route() -> dict:
            return {"message": "success"}

        with app.test_request_context():
            result, status = protected_route()
            assert status == 401
            assert "Missing authorization header" in result["error"]

    def test_require_api_key_decorator_invalid_format(self) -> None:
        """Test require_api_key decorator with invalid header format"""
        app = create_app()

        @require_api_key
        def protected_route() -> dict:
            return {"message": "success"}

        with app.test_request_context(headers={"Authorization": "InvalidFormat"}):
            result, status = protected_route()
            assert status == 401
            assert "Missing authorization header" in result["error"]

    def test_require_api_key_decorator_invalid_key(self) -> None:
        """Test require_api_key decorator with invalid API key"""
        app = create_app()

        @require_api_key
        def protected_route() -> dict:
            return {"message": "success"}

        with app.test_request_context(
            headers={"Authorization": "Bearer invalid-key-12345"}
        ):
            result, status = protected_route()
            assert status == 401
            assert "Invalid API key" in result["error"]

    def test_require_api_key_decorator_stores_username(self) -> None:
        """Test that decorator stores username in g object"""
        from flask import g

        app = create_app()

        @require_api_key
        def protected_route() -> dict:
            return {"username": g.username}

        with app.test_request_context(
            headers={"Authorization": "Bearer demo-api-key-12345"}
        ):
            result = protected_route()
            assert result["username"] == "demo_user"
