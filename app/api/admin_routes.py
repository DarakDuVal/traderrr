"""
Admin API endpoints for user management

Provides admin-only endpoints for managing users, roles, and permissions.
Requires admin role for access.
"""

import logging
from flask import Blueprint, request, jsonify

from app.auth import AuthService
from app.auth.decorators import require_login, require_role
from app.db import get_db_manager
from app.models import User, Role, RoleEnum

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.route("/users", methods=["GET"])
@require_login
@require_role(RoleEnum.ADMIN)
def list_users():
    """List all users (admin only)

    Returns:
    {
        "users": [
            {
                "id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "role": "admin",
                "status": "active",
                "created_at": "2025-11-27T12:00:00",
                "last_login": "2025-11-27T15:30:00"
            }
        ]
    }
    """
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()

        try:
            users = session.query(User).all()

            return (
                jsonify(
                    {
                        "users": [
                            {
                                "id": user.id,
                                "username": user.username,
                                "email": user.email,
                                "role": user.role.name,
                                "status": user.status,
                                "created_at": user.created_at.isoformat(),
                                "last_login": (
                                    user.last_login.isoformat()
                                    if user.last_login
                                    else None
                                ),
                            }
                            for user in users
                        ]
                    }
                ),
                200,
            )

        finally:
            session.close()

    except Exception as e:
        logger.error(f"List users error: {e}")
        return jsonify({"error": "Failed to list users"}), 500


@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@require_login
@require_role(RoleEnum.ADMIN)
def get_user(user_id):
    """Get user details (admin only)

    Returns:
    {
        "user": {
            "id": 1,
            "username": "admin",
            "email": "admin@example.com",
            "role": "admin",
            "status": "active",
            "created_at": "2025-11-27T12:00:00",
            "last_login": "2025-11-27T15:30:00"
        }
    }
    """
    try:
        db_manager = get_db_manager()
        session = db_manager.get_session()

        try:
            user = session.query(User).filter_by(id=user_id).first()

            if not user:
                return jsonify({"error": "User not found"}), 404

            return (
                jsonify(
                    {
                        "user": {
                            "id": user.id,
                            "username": user.username,
                            "email": user.email,
                            "role": user.role.name,
                            "status": user.status,
                            "created_at": user.created_at.isoformat(),
                            "last_login": (
                                user.last_login.isoformat() if user.last_login else None
                            ),
                        }
                    }
                ),
                200,
            )

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Get user error: {e}")
        return jsonify({"error": "Failed to get user"}), 500


@admin_bp.route("/users/<int:user_id>", methods=["PATCH"])
@require_login
@require_role(RoleEnum.ADMIN)
def update_user(user_id):
    """Update user (admin only)

    Request JSON:
    {
        "status": "active|inactive|suspended",
        "role": "admin|user|analyst"
    }

    Returns:
    {
        "success": true,
        "user": {
            "id": 1,
            "username": "user123",
            "status": "active",
            "role": "user"
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        db_manager = get_db_manager()
        session = db_manager.get_session()

        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return jsonify({"error": "User not found"}), 404

            # Update status if provided
            if "status" in data:
                status = data["status"].lower()
                if status not in ("active", "inactive", "suspended"):
                    return (
                        jsonify(
                            {
                                "error": "Invalid status. Must be active, inactive, or suspended"
                            }
                        ),
                        400,
                    )
                user.status = status

            # Update role if provided
            if "role" in data:
                role_name = data["role"].lower()
                role = session.query(Role).filter_by(name=role_name).first()
                if not role:
                    return jsonify({"error": f"Role '{role_name}' not found"}), 400
                user.role_id = role.id

            session.commit()
            logger.info(f"User updated by admin: {user.username}")

            return (
                jsonify(
                    {
                        "success": True,
                        "user": {
                            "id": user.id,
                            "username": user.username,
                            "status": user.status,
                            "role": user.role.name,
                        },
                    }
                ),
                200,
            )

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Update user error: {e}")
        return jsonify({"error": "Failed to update user"}), 500


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@require_login
@require_role(RoleEnum.ADMIN)
def delete_user(user_id):
    """Delete user (admin only, cannot delete self)

    Returns:
    {
        "success": true,
        "message": "User deleted"
    }
    """
    try:
        admin_user: User = request.user

        # Prevent self-deletion
        if admin_user.id == user_id:
            return jsonify({"error": "Cannot delete your own user account"}), 400

        db_manager = get_db_manager()
        session = db_manager.get_session()

        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return jsonify({"error": "User not found"}), 404

            username = user.username
            session.delete(user)
            session.commit()
            logger.info(f"User deleted by admin: {username}")

            return jsonify({"success": True, "message": "User deleted"}), 200

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Delete user error: {e}")
        return jsonify({"error": "Failed to delete user"}), 500


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@require_login
@require_role(RoleEnum.ADMIN)
def reset_user_password(user_id):
    """Reset user password (admin only)

    Request JSON:
    {
        "new_password": "NewSecurePass123"
    }

    Returns:
    {
        "success": true,
        "message": "Password reset successfully"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        new_password = data.get("new_password", "")
        if not new_password:
            return jsonify({"error": "new_password required"}), 400

        db_manager = get_db_manager()
        session = db_manager.get_session()

        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return jsonify({"error": "User not found"}), 404

            success, error = AuthService.reset_password(session, user, new_password)
            if not success:
                return jsonify({"error": error}), 400

            logger.info(f"Password reset by admin for user: {user.username}")
            return (
                jsonify({"success": True, "message": "Password reset successfully"}),
                200,
            )

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Reset password error: {e}")
        return jsonify({"error": "Failed to reset password"}), 500
