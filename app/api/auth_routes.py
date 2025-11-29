"""
Authentication API endpoints

Provides user registration, login, and token management endpoints.
"""

import logging
from typing import Tuple, Any
from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.auth import AuthService, validate_password_strength
from app.auth.decorators import require_login, require_api_key
from app.db import get_db_manager
from app.models import User

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register() -> Tuple[Response, int]:
    """Register a new user

    Request JSON:
    {
        "username": "user123",
        "email": "user@example.com",
        "password": "SecurePass123"
    }

    Returns:
    {
        "success": true,
        "message": "User registered successfully",
        "user": {
            "id": 1,
            "username": "user123",
            "email": "user@example.com"
        }
    }
    """
    try:
        # Check if registration is allowed
        from config.settings import Config

        if not Config.ALLOW_REGISTRATION:
            return jsonify({"error": "Registration is disabled"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        username = data.get("username", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password", "")

        if not username or not email or not password:
            return jsonify({"error": "Missing required fields"}), 400

        # Get database session
        db_manager = get_db_manager()
        session = db_manager.get_session()

        try:
            success, user, error = AuthService.register_user(
                session, username, email, password
            )

            if not success:
                return jsonify({"error": error}), 400

            logger.info(f"User registered: {username}")
            if not user:
                return jsonify({"error": "User creation failed"}), 500

            return (
                jsonify(
                    {
                        "success": True,
                        "message": "User registered successfully",
                        "user": {
                            "id": user.id,
                            "username": user.username,
                            "email": user.email,
                        },
                    }
                ),
                201,
            )

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({"error": "Registration failed"}), 500


@auth_bp.route("/login", methods=["POST"])
def login() -> Tuple[Response, int]:
    """Login with username and password

    Request JSON:
    {
        "username": "user123",
        "password": "SecurePass123"
    }

    Returns:
    {
        "success": true,
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "user": {
            "id": 1,
            "username": "user123",
            "role": "user"
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        username = data.get("username", "").strip()
        password = data.get("password", "")

        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400

        # Get database session
        db_manager = get_db_manager()
        session = db_manager.get_session()

        try:
            success, user, error = AuthService.login_user(session, username, password)

            if not success or not user:
                logger.warning(f"Login failed for user: {username}")
                return jsonify({"error": error}), 401

            # Create access token
            access_token = AuthService.create_access_token(user)

            logger.info(f"User logged in: {username}")
            return (
                jsonify(
                    {
                        "success": True,
                        "access_token": access_token,
                        "user": {
                            "id": user.id,
                            "username": user.username,
                            "email": user.email,
                            "role": user.role.name,
                        },
                    }
                ),
                200,
            )

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"error": "Login failed"}), 500


@auth_bp.route("/refresh", methods=["POST"])
@require_login
def refresh_token() -> Tuple[Response, int]:
    """Refresh JWT access token

    Requires: Valid JWT token in Authorization header

    Returns:
    {
        "success": true,
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
    """
    try:
        user: User = request.user  # type: ignore[attr-defined]

        # Create new access token
        access_token = AuthService.create_access_token(user)

        return jsonify({"success": True, "access_token": access_token}), 200

    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return jsonify({"error": "Token refresh failed"}), 500


@auth_bp.route("/api-keys", methods=["GET"])
@require_login
def list_api_keys() -> Tuple[Response, int]:
    """List user's API keys

    Requires: Valid JWT token in Authorization header

    Returns:
    {
        "api_keys": [
            {
                "id": 1,
                "name": "Production Key",
                "created_at": "2025-11-27T12:00:00",
                "expires_at": "2026-11-27T12:00:00",
                "last_used": "2025-11-27T15:30:00",
                "is_revoked": false
            }
        ]
    }
    """
    try:
        user: User = request.user  # type: ignore[attr-defined]

        # Get database session
        db_manager = get_db_manager()
        session = db_manager.get_session()

        try:
            api_keys = AuthService.get_user_api_keys(session, user)

            return (
                jsonify(
                    {
                        "api_keys": [
                            {
                                "id": key.id,
                                "name": key.name,
                                "created_at": key.created_at.isoformat(),
                                "expires_at": (
                                    key.expires_at.isoformat()
                                    if key.expires_at
                                    else None
                                ),
                                "last_used": (
                                    key.last_used.isoformat() if key.last_used else None
                                ),
                                "is_revoked": key.is_revoked,
                            }
                            for key in api_keys
                        ]
                    }
                ),
                200,
            )

        finally:
            session.close()

    except Exception as e:
        logger.error(f"List API keys error: {e}")
        return jsonify({"error": "Failed to list API keys"}), 500


@auth_bp.route("/api-keys", methods=["POST"])
@require_login
def create_api_key() -> Tuple[Response, int]:
    """Create new API key for user

    Requires: Valid JWT token in Authorization header

    Request JSON:
    {
        "name": "Production Key",
        "expires_in_days": 90
    }

    Returns:
    {
        "success": true,
        "api_key": "dlKxH2-vJ8zQ....",
        "key_info": {
            "id": 1,
            "name": "Production Key",
            "created_at": "2025-11-27T12:00:00",
            "expires_at": "2026-02-25T12:00:00"
        },
        "warning": "Save the API key now. It will not be displayed again."
    }
    """
    try:
        user: User = request.user  # type: ignore[attr-defined]

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        name = data.get("name", "").strip()
        expires_in_days = data.get("expires_in_days")

        if not name:
            return jsonify({"error": "API key name required"}), 400

        if expires_in_days and (
            not isinstance(expires_in_days, int) or expires_in_days < 1
        ):
            return jsonify({"error": "expires_in_days must be a positive integer"}), 400

        # Get database session
        db_manager = get_db_manager()
        session = db_manager.get_session()

        try:
            plaintext_key, api_key_record = AuthService.create_api_key(
                session, user, name, expires_in_days
            )

            if not plaintext_key or not api_key_record:
                return jsonify({"error": "Failed to create API key"}), 500

            logger.info(f"API key created for user {user.username}: {name}")
            return (
                jsonify(
                    {
                        "success": True,
                        "api_key": plaintext_key,
                        "key_info": {
                            "id": api_key_record.id,
                            "name": api_key_record.name,
                            "created_at": api_key_record.created_at.isoformat(),
                            "expires_at": (
                                api_key_record.expires_at.isoformat()
                                if api_key_record.expires_at
                                else None
                            ),
                        },
                        "warning": "Save the API key now. It will not be displayed again.",
                    }
                ),
                201,
            )

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Create API key error: {e}")
        return jsonify({"error": "Failed to create API key"}), 500


@auth_bp.route("/api-keys/<int:key_id>", methods=["DELETE"])
@require_login
def revoke_api_key(key_id: int) -> Tuple[Response, int]:
    """Revoke an API key

    Requires: Valid JWT token in Authorization header

    Returns:
    {
        "success": true,
        "message": "API key revoked"
    }
    """
    try:
        user: User = request.user  # type: ignore[attr-defined]

        # Get database session
        db_manager = get_db_manager()
        session = db_manager.get_session()

        try:
            success = AuthService.revoke_api_key(session, key_id, user)

            if not success:
                return jsonify({"error": "API key not found"}), 404

            logger.info(f"API key revoked by user {user.username}: {key_id}")
            return jsonify({"success": True, "message": "API key revoked"}), 200

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Revoke API key error: {e}")
        return jsonify({"error": "Failed to revoke API key"}), 500
