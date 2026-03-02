"""
Authentication service layer (FastAPI / python-jose / passlib)

Provides JWT creation/decoding and password hashing.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models.user import User, Role, RoleEnum, APIKey
from app.auth.security import APIKeySecurity

logger = logging.getLogger(__name__)

# ── Password hashing ─────────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    """Hash a plaintext password."""
    return pwd_context.hash(plain)  # type: ignore[no-any-return]


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against its hash."""
    return pwd_context.verify(plain, hashed)  # type: ignore[no-any-return]


# ── JWT tokens ────────────────────────────────────────────────────────────


def create_access_token(
    subject: int | str,
    role: str,
    secret_key: str,
    expires_minutes: int = 15,
) -> str:
    """Create a short-lived access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, secret_key, algorithm=ALGORITHM)  # type: ignore[no-any-return]


def create_refresh_token(
    subject: int | str,
    secret_key: str,
    expires_days: int = 7,
) -> str:
    """Create a longer-lived refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(days=expires_days)
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, secret_key, algorithm=ALGORITHM)  # type: ignore[no-any-return]


def decode_token(token: str, secret_key: str) -> Dict[str, Any]:
    """Decode and validate a JWT token.

    Raises JWTError / ExpiredSignatureError on failure.
    """
    return jwt.decode(token, secret_key, algorithms=[ALGORITHM])  # type: ignore[no-any-return]


# ── Convenience wrappers (used by existing code) ─────────────────────────


def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """Validate password meets minimum requirements."""
    if not password:
        return False, "Password cannot be empty"
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if len(password) > 128:
        return False, "Password must not exceed 128 characters"
    has_letter = any(c.isalpha() for c in password)
    has_number = any(c.isdigit() for c in password)
    if not (has_letter and has_number):
        return False, "Password must contain at least one letter and one number"
    return True, None


class AuthService:
    """Authentication service for user and API key management.

    Kept as a class for backward compatibility with existing code.
    """

    @staticmethod
    def register_user(
        session: Session,
        username: str,
        email: str,
        password: str,
        role_name: str = RoleEnum.USER,
    ) -> Tuple[bool, Optional[User], Optional[str]]:
        if not username or len(username) < 3 or len(username) > 50:
            return False, None, "Username must be 3-50 characters"
        if not email or "@" not in email:
            return False, None, "Invalid email format"
        is_valid, error = validate_password_strength(password)
        if not is_valid:
            return False, None, error

        existing_user = (
            session.query(User)
            .filter((User.username == username) | (User.email == email))
            .first()
        )
        if existing_user:
            return False, None, "Username or email already exists"

        role = session.query(Role).filter_by(name=role_name).first()
        if not role:
            return False, None, f"Role '{role_name}' does not exist"

        try:
            password_hash = hash_password(password)
            user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                role_id=role.id,
                status="active",
            )
            session.add(user)
            session.commit()
            logger.info("User registered: %s", username)
            return True, user, None
        except Exception as e:
            session.rollback()
            logger.error("User registration failed: %s", e)
            return False, None, "Registration failed"

    @staticmethod
    def login_user(
        session: Session,
        username: str,
        password: str,
    ) -> Tuple[bool, Optional[User], Optional[str]]:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return False, None, "Invalid username or password"
        if user.status != "active":
            return False, None, "User account is not active"
        if not verify_password(password, user.password_hash):
            return False, None, "Invalid username or password"
        try:
            user.last_login = datetime.now(timezone.utc)
            session.commit()
        except Exception as e:
            logger.error("Failed to update last_login for %s: %s", username, e)
            session.rollback()
        return True, user, None

    @staticmethod
    def reset_password(
        session: Session,
        user: User,
        new_password: str,
    ) -> Tuple[bool, Optional[str]]:
        is_valid, error = validate_password_strength(new_password)
        if not is_valid:
            return False, error
        try:
            user.password_hash = hash_password(new_password)
            session.commit()
            return True, None
        except Exception as e:
            session.rollback()
            return False, "Password reset failed"

    # ── API Key Management ────────────────────────────────────────────────

    @staticmethod
    def create_api_key(
        session: Session,
        user: User,
        name: str,
        expires_in_days: Optional[int] = None,
    ) -> Tuple[str, "APIKey"]:
        """Create a new API key for a user.

        Returns:
            Tuple of (plaintext_key, api_key_record)
        """
        plaintext_key = APIKeySecurity.generate_api_key()
        key_hash = APIKeySecurity.hash_api_key(plaintext_key)

        expires_at = None
        if expires_in_days is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        api_key = APIKey(
            user_id=user.id,
            key_hash=key_hash,
            name=name,
            expires_at=expires_at,
            is_revoked=False,
        )
        session.add(api_key)
        session.commit()
        session.refresh(api_key)
        logger.info("API key '%s' created for user %s", name, user.username)
        return plaintext_key, api_key

    @staticmethod
    def verify_api_key(
        session: Session,
        plaintext_key: str,
    ) -> Optional[User]:
        """Verify an API key and return the associated user.

        Returns:
            User if key is valid, None otherwise.
        """
        key_hash = APIKeySecurity.hash_api_key(plaintext_key)
        api_key = (
            session.query(APIKey)
            .filter_by(key_hash=key_hash, is_revoked=False)
            .first()
        )
        if api_key is None:
            return None
        # Check expiration
        if api_key.expires_at is not None:
            if api_key.expires_at < datetime.now(timezone.utc):
                return None
        # Update last_used
        try:
            api_key.last_used = datetime.now(timezone.utc)
            session.commit()
        except Exception:
            session.rollback()
        return api_key.user

    @staticmethod
    def revoke_api_key(
        session: Session,
        api_key_id: int,
        user: User,
    ) -> bool:
        """Revoke an API key.

        Returns:
            True if key was revoked, False if not found or not owned by user.
        """
        api_key = (
            session.query(APIKey)
            .filter_by(id=api_key_id, user_id=user.id)
            .first()
        )
        if api_key is None:
            return False
        try:
            api_key.is_revoked = True
            session.commit()
            logger.info("API key %d revoked for user %s", api_key_id, user.username)
            return True
        except Exception:
            session.rollback()
            return False

    @staticmethod
    def get_user_api_keys(
        session: Session,
        user: User,
    ) -> list:
        """Get all API keys for a user (including revoked).

        Returns:
            List of APIKey records.
        """
        return (
            session.query(APIKey)
            .filter_by(user_id=user.id)
            .all()
        )
