"""
Password and API key security utilities

Provides secure password hashing, verification, and API key generation.
"""

import hashlib
import secrets
from typing import Tuple
import bcrypt


class PasswordSecurity:
    """Password hashing and verification using bcrypt"""

    WORKFACTOR = 12  # Security vs performance balance

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt

        Args:
            password: Plain text password to hash

        Returns:
            Hashed password (safe to store in database)
        """
        salt = bcrypt.gensalt(rounds=PasswordSecurity.WORKFACTOR)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against its hash

        Args:
            password: Plain text password to verify
            password_hash: Hashed password from database

        Returns:
            True if password matches hash, False otherwise
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception:
            # Bcrypt errors (e.g., invalid hash format)
            return False


class APIKeySecurity:
    """API key generation and verification"""

    KEY_LENGTH = 32  # 256-bit entropy (32 bytes)

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure random API key

        Returns:
            Random 32-byte API key as URL-safe base64 string
        """
        return secrets.token_urlsafe(APIKeySecurity.KEY_LENGTH)

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash an API key for storage

        Args:
            api_key: The plaintext API key

        Returns:
            SHA256 hash of the key (safe to store in database)
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    @staticmethod
    def verify_api_key(api_key: str, api_key_hash: str) -> bool:
        """Verify an API key against its hash

        Args:
            api_key: The plaintext API key to verify
            api_key_hash: The stored hash from database

        Returns:
            True if key matches hash, False otherwise
        """
        computed_hash = APIKeySecurity.hash_api_key(api_key)
        # Use constant-time comparison to prevent timing attacks
        return secrets.compare_digest(computed_hash, api_key_hash)


class TokenSecurity:
    """Token generation and management"""

    @staticmethod
    def generate_token_id() -> str:
        """Generate a unique token identifier

        Returns:
            Random token ID as hex string
        """
        return secrets.token_hex(16)


def validate_password_strength(password: str) -> Tuple[bool, str | None]:
    """Validate password meets minimum requirements

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
        If valid: (True, None)
        If invalid: (False, reason)
    """
    if not password:
        return False, "Password cannot be empty"

    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if len(password) > 128:
        return False, "Password must not exceed 128 characters"

    # Basic complexity check: at least one letter and one number
    has_letter = any(c.isalpha() for c in password)
    has_number = any(c.isdigit() for c in password)

    if not (has_letter and has_number):
        return False, "Password must contain at least one letter and one number"

    return True, None
