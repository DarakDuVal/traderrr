"""
Authentication service layer

Handles user registration, login, token generation, and API key management.
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from flask_jwt_extended import create_access_token as jwt_create_access_token

from app.models import User, APIKey, Role, RoleEnum
from app.auth.security import (
    PasswordSecurity,
    APIKeySecurity,
    validate_password_strength,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service for user and API key management"""

    @staticmethod
    def register_user(
        session: Session,
        username: str,
        email: str,
        password: str,
        role_name: str = RoleEnum.USER,
    ) -> tuple[bool, User | None, str | None]:
        """Register a new user

        Args:
            session: Database session
            username: Unique username (3-50 chars)
            email: Unique email address
            password: Plain text password
            role_name: Role to assign (default: user)

        Returns:
            Tuple of (success, user, error_message)
        """
        # Validate inputs
        if not username or len(username) < 3 or len(username) > 50:
            return False, None, "Username must be 3-50 characters"

        if not email or "@" not in email:
            return False, None, "Invalid email format"

        # Validate password strength
        is_valid, error = validate_password_strength(password)
        if not is_valid:
            return False, None, error

        # Check if user already exists
        existing_user = (
            session.query(User)
            .filter((User.username == username) | (User.email == email))
            .first()
        )
        if existing_user:
            return False, None, "Username or email already exists"

        # Get role from database
        role = session.query(Role).filter_by(name=role_name).first()
        if not role:
            return False, None, f"Role '{role_name}' does not exist"

        # Create user
        try:
            password_hash = PasswordSecurity.hash_password(password)
            user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                role_id=role.id,
                status="active",
            )
            session.add(user)
            session.commit()
            logger.info(f"User registered: {username}")
            return True, user, None
        except Exception as e:
            session.rollback()
            logger.error(f"User registration failed: {e}")
            return False, None, "Registration failed"

    @staticmethod
    def login_user(
        session: Session,
        username: str,
        password: str,
    ) -> tuple[bool, User | None, str | None]:
        """Authenticate user with password

        Args:
            session: Database session
            username: Username
            password: Plain text password

        Returns:
            Tuple of (success, user, error_message)
        """
        # Find user
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return False, None, "Invalid username or password"

        # Check status
        if user.status != "active":
            return False, None, "User account is not active"

        # Verify password
        if not PasswordSecurity.verify_password(password, user.password_hash):
            return False, None, "Invalid username or password"

        # Update last login
        try:
            user.last_login = datetime.utcnow()
            session.commit()
            logger.info(f"User logged in: {username}")
            return True, user, None
        except Exception as e:
            session.rollback()
            logger.error(f"Login update failed: {e}")
            return True, user, None  # Auth succeeded, but couldn't update timestamp

    @staticmethod
    def create_access_token(
        user: User,
        expires_in_hours: int = 24,
    ) -> str:
        """Create JWT access token for user

        Args:
            user: User object
            expires_in_hours: Token expiration in hours (default: 24)

        Returns:
            JWT access token
        """
        identity = str(user.id)
        additional_claims = {
            "username": user.username,
            "role": user.role.name if user.role else RoleEnum.USER,
        }
        expires_delta = timedelta(hours=expires_in_hours)
        token: str = jwt_create_access_token(
            identity=identity,
            additional_claims=additional_claims,
            expires_delta=expires_delta,
        )
        return token

    @staticmethod
    def create_api_key(
        session: Session,
        user: User,
        name: str,
        expires_in_days: int | None = None,
    ) -> tuple[str, APIKey] | tuple[None, None]:
        """Create new API key for user

        Args:
            session: Database session
            user: User object
            name: Name for the API key (for reference)
            expires_in_days: Optional expiration in days

        Returns:
            Tuple of (plaintext_key, APIKey_object) or (None, None) on error
            Note: Plaintext key is returned ONLY on creation, never retrievable after
        """
        try:
            # Generate key and hash it
            plaintext_key = APIKeySecurity.generate_api_key()
            key_hash = APIKeySecurity.hash_api_key(plaintext_key)

            # Determine expiration
            expires_at = None
            if expires_in_days:
                expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

            # Create API key record
            api_key = APIKey(
                user_id=user.id,
                key_hash=key_hash,
                name=name,
                expires_at=expires_at,
                is_revoked=False,
            )

            session.add(api_key)
            session.commit()
            logger.info(f"API key created for user {user.username}: {name}")
            return plaintext_key, api_key

        except Exception as e:
            session.rollback()
            logger.error(f"API key creation failed: {e}")
            return None, None

    @staticmethod
    def verify_api_key(
        session: Session,
        api_key: str,
    ) -> User | None:
        """Verify API key and return associated user

        Args:
            session: Database session
            api_key: The plaintext API key to verify

        Returns:
            User object if valid, None otherwise
        """
        try:
            # Hash the provided key to search in database
            key_hash = APIKeySecurity.hash_api_key(api_key)

            # Find the key record
            api_key_record = (
                session.query(APIKey)
                .filter_by(
                    key_hash=key_hash,
                    is_revoked=False,
                )
                .first()
            )

            if not api_key_record:
                return None

            # Check expiration
            if api_key_record.expires_at:
                if datetime.utcnow() > api_key_record.expires_at:
                    logger.warning(f"Expired API key attempted: {api_key_record.id}")
                    return None

            # Check user status
            user = api_key_record.user
            if user.status != "active":
                return None

            # Update last used timestamp
            try:
                api_key_record.last_used = datetime.utcnow()
                session.commit()
            except Exception:
                session.rollback()

            return user

        except Exception as e:
            logger.error(f"API key verification failed: {e}")
            return None

    @staticmethod
    def revoke_api_key(
        session: Session,
        api_key_id: int,
        user: User,
    ) -> bool:
        """Revoke an API key

        Args:
            session: Database session
            api_key_id: ID of API key to revoke
            user: User object (must own the key)

        Returns:
            True if revoked successfully, False otherwise
        """
        try:
            api_key = (
                session.query(APIKey)
                .filter_by(
                    id=api_key_id,
                    user_id=user.id,
                )
                .first()
            )

            if not api_key:
                return False

            api_key.is_revoked = True
            session.commit()
            logger.info(f"API key revoked: {api_key.id}")
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"API key revocation failed: {e}")
            return False

    @staticmethod
    def get_user_api_keys(
        session: Session,
        user: User,
    ) -> list[APIKey]:
        """Get all API keys for a user

        Args:
            session: Database session
            user: User object

        Returns:
            List of APIKey objects (does not include plaintext keys)
        """
        return session.query(APIKey).filter_by(user_id=user.id).all()

    @staticmethod
    def reset_password(
        session: Session,
        user: User,
        new_password: str,
    ) -> tuple[bool, str | None]:
        """Reset user password (admin or user self-service)

        Args:
            session: Database session
            user: User object
            new_password: New plain text password

        Returns:
            Tuple of (success, error_message)
        """
        # Validate password strength
        is_valid, error = validate_password_strength(new_password)
        if not is_valid:
            return False, error

        try:
            password_hash = PasswordSecurity.hash_password(new_password)
            user.password_hash = password_hash
            session.commit()
            logger.info(f"Password reset for user: {user.username}")
            return True, None
        except Exception as e:
            session.rollback()
            logger.error(f"Password reset failed: {e}")
            return False, "Password reset failed"
