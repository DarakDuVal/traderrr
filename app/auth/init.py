"""
Authentication initialization module

Handles first-run setup of admin users via environment variables or CLI.
Supports two modes:
1. Environment variable bootstrap: Set ADMIN_USERNAME and ADMIN_PASSWORD
2. CLI interactive mode: Run `python -m app.cli setup-admin`
"""

import logging
import os
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def check_admin_exists(session) -> bool:
    """
    Check if any admin user exists in database

    Args:
        session: SQLAlchemy database session

    Returns:
        bool: True if admin exists, False otherwise
    """
    try:
        from app.models import User, RoleEnum

        admin_user = session.query(User).join(User.role).filter_by(name="admin").first()
        return admin_user is not None
    except Exception as e:
        logger.warning(f"Error checking for admin user: {e}")
        return False


def create_admin_from_env(session) -> Optional[str]:
    """
    Create admin user from environment variables

    Environment variables:
    - ADMIN_USERNAME: Username for admin account
    - ADMIN_PASSWORD: Password for admin account

    Args:
        session: SQLAlchemy database session

    Returns:
        str: Success message if created, None if failed or env vars not set
    """
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")

    if not username or not password:
        logger.debug("ADMIN_USERNAME or ADMIN_PASSWORD not set, skipping env bootstrap")
        return None

    try:
        from app.auth.service import AuthService
        from app.models import RoleEnum

        logger.info(f"Creating admin user from environment variables: {username}")

        success, user, error = AuthService.register_user(
            session,
            username,
            f"{username}@admin.local",
            password,
            role_name=RoleEnum.ADMIN,
        )

        if success:
            logger.info(f"Admin user created successfully: {username}")
            return f"Admin user '{username}' created"
        else:
            logger.error(f"Failed to create admin user: {error}")
            return None

    except Exception as e:
        logger.error(f"Error creating admin from env: {e}")
        return None


def initialize_admin_on_startup(session) -> None:
    """
    Initialize admin user on application startup

    Called during app initialization. This function:
    1. Checks if any admin users exist
    2. If not, tries to create from environment variables
    3. If env vars not set, logs instructions for CLI setup

    Args:
        session: SQLAlchemy database session
    """
    try:
        # Check if admin already exists
        if check_admin_exists(session):
            logger.debug("Admin user already exists, skipping initialization")
            return

        logger.info("No admin user found, attempting to initialize...")

        # Try to create from environment variables
        result = create_admin_from_env(session)

        if result:
            logger.info(result)
        else:
            # Guide user to CLI setup
            logger.warning(
                "No admin user found and ADMIN_USERNAME/ADMIN_PASSWORD not set. "
                "To create admin user, run: python -m app.cli setup-admin"
            )

    except Exception as e:
        logger.error(f"Error during admin initialization: {e}")


def ensure_roles_exist(session) -> None:
    """
    Ensure default roles exist in database

    Creates standard roles (admin, user, analyst) if they don't exist.
    This should be called during database initialization.

    Args:
        session: SQLAlchemy database session
    """
    try:
        from app.models import Role

        default_roles = [
            ("admin", "Administrator with full system access"),
            ("user", "Regular user with personal portfolio access"),
            ("analyst", "Analyst with read-only access to portfolios"),
        ]

        for role_name, description in default_roles:
            existing_role = session.query(Role).filter_by(name=role_name).first()
            if not existing_role:
                role = Role(name=role_name, description=description)
                session.add(role)
                logger.info(f"Created default role: {role_name}")

        session.commit()
        logger.debug("Default roles initialized")

    except Exception as e:
        logger.error(f"Error ensuring roles exist: {e}")
        session.rollback()
