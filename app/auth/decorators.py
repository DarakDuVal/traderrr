"""
Authentication decorators for API endpoints

Provides decorators for requiring authentication and role-based access control.
"""

import logging
from functools import wraps
from typing import Callable, Any
from flask import request, jsonify, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from sqlalchemy.orm import Session

from app.db import get_db_manager
from app.models import User, RoleEnum

logger = logging.getLogger(__name__)


def require_login(f: Callable) -> Callable:
    """Decorator requiring valid JWT token

    Checks for valid JWT token in Authorization header.
    Stores current user in request context.

    Usage:
        @app.route('/api/protected')
        @require_login
        def protected_route():
            current_user = request.user
            return {"user": current_user.username}
    """

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()

            # Get user from database
            db_manager = get_db_manager()
            session = db_manager.get_session()
            try:
                user = session.query(User).filter_by(id=user_id).first()
                session.close()

                if not user or user.status != "active":
                    return jsonify({"error": "User not found or inactive"}), 401

                # Store user in request context
                request.user = user  # type: ignore[attr-defined]
                return f(*args, **kwargs)

            finally:
                session.close()

        except Exception as e:
            logger.warning(f"Authentication failed: {e}")
            return jsonify({"error": "Authentication required"}), 401

    return decorated_function


def require_role(*allowed_roles: str) -> Callable:
    """Decorator requiring specific role(s)

    Checks if current user has one of the allowed roles.
    Must be used AFTER @require_login decorator.

    Usage:
        @app.route('/api/admin')
        @require_login
        @require_role(RoleEnum.ADMIN)
        def admin_only():
            return {"message": "Admin access"}

        @app.route('/api/users')
        @require_login
        @require_role(RoleEnum.ADMIN, RoleEnum.ANALYST)
        def multi_role():
            return {"message": "Admin or Analyst access"}
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            # Ensure require_login has already been called
            if not hasattr(request, "user"):
                return jsonify({"error": "Authentication required"}), 401

            user: User = request.user  # type: ignore[attr-defined]

            # Check if user's role is in allowed roles
            if user.role.name not in allowed_roles:
                logger.warning(
                    f"Access denied for user {user.username}: "
                    f"requires {allowed_roles}, has {user.role.name}"
                )
                return (
                    jsonify(
                        {
                            "error": f"Access denied. Required role: {', '.join(allowed_roles)}"
                        }
                    ),
                    403,
                )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def require_api_key(f: Callable) -> Callable:
    """Decorator requiring valid API key

    Checks for valid API key in Authorization header (Bearer <key>).
    Stores current user in request context.

    Usage:
        @app.route('/api/protected')
        @require_api_key
        def protected_route():
            current_user = request.user
            return {"user": current_user.username}
    """

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        from app.auth.service import AuthService

        try:
            # Get Authorization header
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return jsonify({"error": "Invalid authorization header"}), 401

            api_key = auth_header[7:]  # Remove "Bearer " prefix

            # Verify API key
            db_manager = get_db_manager()
            session = db_manager.get_session()
            try:
                user = AuthService.verify_api_key(session, api_key)
                if not user:
                    logger.warning("Invalid API key attempted")
                    return jsonify({"error": "Invalid API key"}), 401

                # Store user in request context
                request.user = user  # type: ignore[attr-defined]
                return f(*args, **kwargs)

            finally:
                session.close()

        except Exception as e:
            logger.warning(f"API key authentication failed: {e}")
            return jsonify({"error": "Authentication failed"}), 401

    return decorated_function


def require_authentication(f: Callable) -> Callable:
    """Decorator supporting both JWT and API key authentication

    Tries JWT first, then API key if JWT fails.
    Stores current user in request context.

    Usage:
        @app.route('/api/protected')
        @require_authentication
        def protected_route():
            current_user = request.user
            return {"user": current_user.username}
    """

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        from app.auth.service import AuthService

        # Try JWT first
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()

            db_manager = get_db_manager()
            session = db_manager.get_session()
            try:
                user = session.query(User).filter_by(id=user_id).first()
                if user and user.status == "active":
                    request.user = user  # type: ignore[attr-defined]
                    return f(*args, **kwargs)
            finally:
                session.close()

        except Exception:
            pass  # JWT failed, try API key

        # Try API key
        try:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                api_key = auth_header[7:]

                db_manager = get_db_manager()
                session = db_manager.get_session()
                try:
                    user = AuthService.verify_api_key(session, api_key)
                    if user:
                        request.user = user  # type: ignore[attr-defined]
                        return f(*args, **kwargs)
                finally:
                    session.close()

        except Exception as e:
            logger.warning(f"API key authentication failed: {e}")

        # Both failed
        return jsonify({"error": "Authentication required"}), 401

    return decorated_function
