"""
app/api/auth.py
Authentication and authorization for the API
"""

from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
)
from functools import wraps
from flask import current_app, request
from datetime import timedelta
import os
import secrets
from typing import Dict, Optional

# ============================================================================
# API KEY STORE (Replace with database in production)
# ============================================================================

# Format: {"api_key": "username"}
VALID_API_KEYS: Dict[str, str] = {
    "demo-api-key-12345": "demo_user",
    "test-api-key-67890": "test_user",
}

# ============================================================================
# JWT INITIALIZATION
# ============================================================================


def init_jwt(app) -> JWTManager:
    """
    Initialize JWT authentication for the Flask app

    Args:
        app: Flask application instance

    Returns:
        JWTManager: Configured JWT manager instance
    """
    # Get secret key from environment or use default (change in production!)
    secret_key = os.getenv(
        "JWT_SECRET_KEY", "your-secret-key-change-in-production-12345"
    )
    app.config["JWT_SECRET_KEY"] = secret_key
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=30)

    jwt = JWTManager(app)

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        """Load user identity from JWT"""
        identity = jwt_data["sub"]
        return identity

    @jwt.additional_claims_loader
    def add_claims_to_access_token(identity):
        """Add custom claims to JWT token"""
        return {"username": identity, "api_version": "1.0.0"}

    return jwt


# ============================================================================
# API KEY VALIDATION
# ============================================================================


def require_api_key(f):
    """
    Decorator to require API key authentication

    Validates the Bearer token in the Authorization header against
    valid API keys. Uses "Authorization: Bearer <api_key>" format.

    Usage:
        @require_api_key
        def my_route():
            return {'data': 'value'}
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get authorization header
        auth_header = request.headers.get("Authorization", "")

        # Extract token from "Bearer <token>" format
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix

        # Validate token exists
        if not token:
            return {
                "error": "Missing authorization header. Use: Authorization: Bearer <api_key>",
                "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            }, 401

        # Validate token is in whitelist
        if token not in VALID_API_KEYS:
            return {
                "error": "Invalid API key",
                "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            }, 401

        # Store username in request context
        current_app.username = VALID_API_KEYS[token]

        return f(*args, **kwargs)

    return decorated_function


# ============================================================================
# API KEY MANAGEMENT
# ============================================================================


def generate_api_key(username: str) -> str:
    """
    Generate a new API key for a user

    In production, this should:
    1. Store the key securely (hashed) in database
    2. Track creation date and last used date
    3. Allow key rotation and revocation

    Args:
        username: Username to generate key for

    Returns:
        str: New API key
    """
    # Generate secure random token (32 bytes = 256 bits)
    random_part = secrets.token_urlsafe(32)
    api_key = f"{username}-{random_part}"

    # Store in memory (replace with database call in production)
    VALID_API_KEYS[api_key] = username

    return api_key


def validate_api_key(api_key: str) -> Optional[str]:
    """
    Validate an API key and return the associated username

    Args:
        api_key: API key to validate

    Returns:
        str: Username if valid, None if invalid
    """
    return VALID_API_KEYS.get(api_key)


def revoke_api_key(api_key: str) -> bool:
    """
    Revoke an API key

    Args:
        api_key: API key to revoke

    Returns:
        bool: True if revoked, False if key not found
    """
    if api_key in VALID_API_KEYS:
        del VALID_API_KEYS[api_key]
        return True
    return False


def list_api_keys(username: str) -> list:
    """
    List all API keys for a user (for security, only return partial keys)

    Args:
        username: Username to list keys for

    Returns:
        list: List of partial API keys (last 8 chars only for security)
    """
    keys = [key[-8:] for key, user in VALID_API_KEYS.items() if user == username]
    return keys


# ============================================================================
# JWT TOKEN GENERATION
# ============================================================================


def create_access_token_for_user(
    username: str, expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token for a user

    This is for programmatic access (e.g., integration tests, scripts).
    For API access, users should use API keys instead.

    Args:
        username: Username to create token for
        expires_delta: Token expiration time (default: 30 days)

    Returns:
        str: JWT access token
    """
    if expires_delta is None:
        expires_delta = timedelta(days=30)

    return create_access_token(identity=username, expires_delta=expires_delta)


# ============================================================================
# AUTHENTICATION EXAMPLES FOR DOCUMENTATION
# ============================================================================

AUTHENTICATION_EXAMPLES = {
    "api_key_header": {
        "description": "API Key Authentication",
        "header": "Authorization: Bearer your-api-key-here",
        "curl_example": 'curl -H "Authorization: Bearer your-api-key-here" https://api.example.com/api/portfolio',
    },
    "get_api_key": {
        "description": "Getting an API Key",
        "steps": [
            "1. Contact your administrator",
            "2. Request an API key for your account",
            "3. Store it securely (never commit to git)",
            "4. Use in Authorization header as shown above",
        ],
    },
    "error_responses": {
        "missing_key": {
            "status": 401,
            "response": {
                "error": "Missing authorization header. Use: Authorization: Bearer <api_key>",
                "timestamp": "2024-11-25T12:00:00",
            },
        },
        "invalid_key": {
            "status": 401,
            "response": {
                "error": "Invalid API key",
                "timestamp": "2024-11-25T12:00:00",
            },
        },
    },
}
