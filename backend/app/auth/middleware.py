"""
Authentication middleware for Flask

Handles:
- JWT token validation on requests
- User context injection
- Authorization for protected routes
"""

import logging
from functools import wraps
from typing import Optional, Callable, Any, Tuple
from flask import request, g, jsonify, Flask, Response
from flask_jwt_extended import decode_token

from app.db import get_db_manager
from app.models import User

logger = logging.getLogger(__name__)


def setup_auth_middleware(app: Flask) -> None:
    """Setup authentication middleware for Flask app"""

    @app.before_request
    def check_jwt_token() -> Optional[Tuple[Response, int]]:
        """Check JWT token on each request and inject user context"""
        # Skip auth check for public endpoints
        public_endpoints = [
            "/api/auth/login",
            "/api/auth/register",
            "/api/health",
            "/",
        ]

        # Check if current path is public
        if request.path in public_endpoints:
            return None

        # Check if path starts with any public prefix
        public_prefixes = ["/static/", "/api/docs"]
        if any(request.path.startswith(prefix) for prefix in public_prefixes):
            return None

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        token = None

        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove 'Bearer ' prefix

        # If no token in header, try to get from request body (for API calls)
        if not token and request.method == "POST":
            try:
                data = request.get_json() or {}
                token = data.get("token")
            except Exception:
                pass

        # If still no token, return unauthorized for protected endpoints
        if not token:
            # For API routes, return JSON error
            if request.path.startswith("/api/"):
                return jsonify({"error": "Missing authorization token"}), 401
            # For web routes, just skip (let template handle login screen)
            return None

        try:
            # Decode and validate token
            decoded = decode_token(token)
            user_id_str = decoded.get("sub")

            # Convert user_id to integer for database query
            try:
                user_id = int(user_id_str) if user_id_str is not None else 0
            except (ValueError, TypeError):
                logger.warning(f"Invalid user_id in token: {user_id_str}")
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Invalid token"}), 401
                return None

            # Get user from database
            db_manager = get_db_manager()
            session = db_manager.get_session()

            try:
                user = session.query(User).filter_by(id=user_id).first()

                if not user:
                    session.close()
                    if request.path.startswith("/api/"):
                        return jsonify({"error": "User not found"}), 401
                    return None

                # Attach user and session to request context
                g.user = user
                g.session = session
                g.user_id = user_id
                logger.debug(f"User {user.username} authenticated for {request.path}")
                return None

            except Exception as e:
                session.close()
                logger.error(f"Error loading user: {e}")
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Authentication error"}), 401
                return None

        except Exception as e:
            logger.warning(f"Token validation failed: {e}")
            if request.path.startswith("/api/"):
                return jsonify({"error": "Invalid token"}), 401
            return None

    @app.teardown_request
    def close_session(exception: Optional[BaseException] = None) -> None:
        """Close database session at end of request"""
        session = g.pop("session", None)
        if session:
            try:
                session.close()
            except Exception as e:
                logger.warning(f"Error closing session: {e}")


def require_authentication(f: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to require valid authentication for a route

    Usage:
        @app.route('/api/protected')
        @require_authentication
        def protected_route():
            user = g.user
            return {'message': f'Hello {user.username}'}
    """

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if not hasattr(g, "user") or g.user is None:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)

    return decorated_function


def get_current_user() -> Optional[User]:
    """Get currently authenticated user from request context

    Returns:
        User object or None if not authenticated
    """
    return getattr(g, "user", None)


def is_authenticated() -> bool:
    """Check if current request is authenticated

    Returns:
        bool: True if user is authenticated
    """
    return hasattr(g, "user") and g.user is not None
