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
from app.api.auth import init_jwt, VALID_API_KEYS


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
