"""
app/api/auth.py
API key management utilities

Provides in-memory API key storage and management functions.
JWT authentication is handled by app.auth.service (python-jose).
"""

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
