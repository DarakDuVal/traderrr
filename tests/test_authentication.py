"""
tests/test_authentication.py
Comprehensive tests for Phase 1 authentication and authorization

Tests cover:
- User registration and login
- JWT token generation and refresh
- API key creation and management
- Role-based access control
- User data isolation
- Admin user management
"""

import pytest
import json
from datetime import datetime, timedelta
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy.orm import Session

from app import create_app
from app.auth.service import AuthService
from app.auth.security import (
    PasswordSecurity,
    APIKeySecurity,
    validate_password_strength,
)
from app.db import DatabaseManager
from app.models import User, Role, APIKey, RoleEnum, Base


class TestPasswordSecurity:
    """Test password hashing and validation"""

    def test_password_hashing(self):
        """Test that passwords are properly hashed"""
        password = "TestPassword123"
        hashed = PasswordSecurity.hash_password(password)

        # Hash should not be the plaintext password
        assert hashed != password

        # Verification should work
        assert PasswordSecurity.verify_password(password, hashed)

        # Wrong password should not verify
        assert not PasswordSecurity.verify_password("WrongPassword123", hashed)

    def test_password_strength_validation(self):
        """Test password strength requirements"""
        # Strong password
        is_valid, error = validate_password_strength("ValidPass123")
        assert is_valid
        assert error is None

        # Too short
        is_valid, error = validate_password_strength("Short1")
        assert not is_valid
        assert "8 characters" in error

        # No numbers
        is_valid, error = validate_password_strength("OnlyLetters")
        assert not is_valid
        assert "number" in error.lower()

        # No letters
        is_valid, error = validate_password_strength("12345678")
        assert not is_valid
        assert "letter" in error.lower()


class TestAPIKeySecurity:
    """Test API key generation and validation"""

    def test_api_key_generation(self):
        """Test that API keys are properly generated"""
        key = APIKeySecurity.generate_api_key()

        # Should be a string
        assert isinstance(key, str)

        # Should have reasonable length (URL-safe base64)
        assert len(key) > 20

    def test_api_key_hashing(self):
        """Test that API keys are hashed"""
        key = APIKeySecurity.generate_api_key()
        hashed = APIKeySecurity.hash_api_key(key)

        # Hash should not be the plaintext key
        assert hashed != key

        # Verification should work
        assert APIKeySecurity.verify_api_key(key, hashed)

        # Wrong key should not verify
        wrong_key = APIKeySecurity.generate_api_key()
        assert not APIKeySecurity.verify_api_key(wrong_key, hashed)


class TestUserRegistration:
    """Test user registration flow"""

    @pytest.fixture
    def db_session(self):
        """Create a test database session"""
        db_manager = DatabaseManager("sqlite:///:memory:")
        Base.metadata.create_all(db_manager.engine)

        # Create default roles
        session = db_manager.get_session()
        for role_name, description in [
            ("admin", "Administrator"),
            ("user", "Regular user"),
            ("analyst", "Analyst"),
        ]:
            role = Role(name=role_name, description=description)
            session.add(role)
        session.commit()

        yield session
        session.close()

    def test_register_user_success(self, db_session):
        """Test successful user registration"""
        success, user, error = AuthService.register_user(
            db_session,
            "testuser",
            "test@example.com",
            "ValidPass123",
            role_name=RoleEnum.USER,
        )

        assert success
        assert user is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role.name == "user"

    def test_register_user_weak_password(self, db_session):
        """Test registration with weak password"""
        success, user, error = AuthService.register_user(
            db_session,
            "testuser",
            "test@example.com",
            "weak",
            role_name=RoleEnum.USER,
        )

        assert not success
        assert user is None
        assert "password" in error.lower()

    def test_register_duplicate_username(self, db_session):
        """Test registration with duplicate username"""
        # Register first user
        AuthService.register_user(
            db_session,
            "testuser",
            "test1@example.com",
            "ValidPass123",
            role_name=RoleEnum.USER,
        )

        # Try to register with same username
        success, user, error = AuthService.register_user(
            db_session,
            "testuser",
            "test2@example.com",
            "ValidPass123",
            role_name=RoleEnum.USER,
        )

        assert not success
        assert user is None
        assert "already exists" in error.lower() or "username" in error.lower()

    def test_register_duplicate_email(self, db_session):
        """Test registration with duplicate email"""
        # Register first user
        AuthService.register_user(
            db_session,
            "testuser1",
            "test@example.com",
            "ValidPass123",
            role_name=RoleEnum.USER,
        )

        # Try to register with same email
        success, user, error = AuthService.register_user(
            db_session,
            "testuser2",
            "test@example.com",
            "ValidPass123",
            role_name=RoleEnum.USER,
        )

        assert not success
        assert user is None
        assert "email" in error.lower() or "already exists" in error.lower()


class TestUserLogin:
    """Test user login flow"""

    @pytest.fixture
    def db_with_user(self):
        """Create database with test user"""
        db_manager = DatabaseManager("sqlite:///:memory:")
        Base.metadata.create_all(db_manager.engine)

        session = db_manager.get_session()

        # Create default role
        role = Role(name="user", description="Regular user")
        session.add(role)
        session.commit()

        # Create test user
        AuthService.register_user(
            session,
            "testuser",
            "test@example.com",
            "ValidPass123",
            role_name=RoleEnum.USER,
        )

        yield session
        session.close()

    def test_login_success(self, db_with_user):
        """Test successful login"""
        success, user, error = AuthService.login_user(
            db_with_user, "testuser", "ValidPass123"
        )

        assert success
        assert user is not None
        assert user.username == "testuser"

    def test_login_wrong_password(self, db_with_user):
        """Test login with wrong password"""
        success, user, error = AuthService.login_user(
            db_with_user, "testuser", "WrongPass123"
        )

        assert not success
        assert user is None

    def test_login_nonexistent_user(self, db_with_user):
        """Test login with nonexistent user"""
        success, user, error = AuthService.login_user(
            db_with_user, "nonexistent", "ValidPass123"
        )

        assert not success
        assert user is None

    def test_login_updates_last_login(self, db_with_user):
        """Test that login updates last_login timestamp"""
        user_before = db_with_user.query(User).filter_by(username="testuser").first()
        assert user_before.last_login is None

        AuthService.login_user(db_with_user, "testuser", "ValidPass123")

        user_after = db_with_user.query(User).filter_by(username="testuser").first()
        assert user_after.last_login is not None


@pytest.mark.integration
class TestJWTTokens:
    """Test JWT token generation and validation (requires app context)"""

    @pytest.fixture
    def app(self):
        """Create Flask app for JWT testing"""
        test_app = create_app()
        test_app.config["TESTING"] = True
        test_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        return test_app

    @pytest.fixture
    def db_with_user(self, app):
        """Create database with test user"""
        with app.app_context():
            from app.models import Base
            from app.db import init_db_manager, get_db_manager

            # Initialize database manager before use
            init_db_manager("sqlite:///:memory:")

            db_manager = get_db_manager()
            Base.metadata.create_all(db_manager.engine)

            session = db_manager.get_session()

            role = Role(name="user", description="Regular user")
            session.add(role)
            session.commit()

            AuthService.register_user(
                session,
                "testuser",
                "test@example.com",
                "ValidPass123",
                role_name=RoleEnum.USER,
            )

            yield session
            session.close()

    def test_access_token_creation(self, app, db_with_user):
        """Test access token creation"""
        with app.app_context():
            user = db_with_user.query(User).filter_by(username="testuser").first()
            token = AuthService.create_access_token(user)

            assert token is not None
            assert isinstance(token, str)
            assert len(token) > 0

    def test_access_token_contains_user_id(self, app, db_with_user):
        """Test that token contains user_id"""
        with app.app_context():
            user = db_with_user.query(User).filter_by(username="testuser").first()
            token = AuthService.create_access_token(user)

            # Token should be decodable (basic JWT structure check)
            parts = token.split(".")
            assert len(parts) == 3  # JWT has 3 parts


class TestAPIKeyManagement:
    """Test API key creation and management"""

    @pytest.fixture
    def db_with_user(self):
        """Create database with test user"""
        db_manager = DatabaseManager("sqlite:///:memory:")
        Base.metadata.create_all(db_manager.engine)

        session = db_manager.get_session()

        role = Role(name="user", description="Regular user")
        session.add(role)
        session.commit()

        AuthService.register_user(
            session,
            "testuser",
            "test@example.com",
            "ValidPass123",
            role_name=RoleEnum.USER,
        )

        yield session
        session.close()

    def test_create_api_key(self, db_with_user):
        """Test API key creation"""
        user = db_with_user.query(User).filter_by(username="testuser").first()

        plaintext_key, api_key_record = AuthService.create_api_key(
            db_with_user, user, "Test Key"
        )

        assert plaintext_key is not None
        assert api_key_record is not None
        assert api_key_record.name == "Test Key"
        assert api_key_record.user_id == user.id

    def test_create_api_key_with_expiration(self, db_with_user):
        """Test API key creation with expiration"""
        user = db_with_user.query(User).filter_by(username="testuser").first()

        plaintext_key, api_key_record = AuthService.create_api_key(
            db_with_user, user, "Test Key", expires_in_days=7
        )

        assert api_key_record.expires_at is not None

    def test_verify_api_key(self, db_with_user):
        """Test API key verification"""
        user = db_with_user.query(User).filter_by(username="testuser").first()

        plaintext_key, _ = AuthService.create_api_key(db_with_user, user, "Test Key")

        # Verify the key
        verified_user = AuthService.verify_api_key(db_with_user, plaintext_key)

        assert verified_user is not None
        assert verified_user.id == user.id

    def test_revoke_api_key(self, db_with_user):
        """Test API key revocation"""
        user = db_with_user.query(User).filter_by(username="testuser").first()

        plaintext_key, api_key_record = AuthService.create_api_key(
            db_with_user, user, "Test Key"
        )

        # Revoke the key
        success = AuthService.revoke_api_key(db_with_user, api_key_record.id, user)
        assert success

        # Verify revoked key doesn't work
        verified_user = AuthService.verify_api_key(db_with_user, plaintext_key)
        assert verified_user is None

    def test_get_user_api_keys(self, db_with_user):
        """Test listing user API keys"""
        user = db_with_user.query(User).filter_by(username="testuser").first()

        # Create multiple keys
        AuthService.create_api_key(db_with_user, user, "Key 1")
        AuthService.create_api_key(db_with_user, user, "Key 2")

        # Get user's keys
        keys = AuthService.get_user_api_keys(db_with_user, user)

        assert len(keys) == 2
        assert keys[0].name in ["Key 1", "Key 2"]
        assert keys[1].name in ["Key 1", "Key 2"]


class TestRoleBasedAccess:
    """Test role-based access control"""

    @pytest.fixture
    def db_with_users(self):
        """Create database with users of different roles"""
        db_manager = DatabaseManager("sqlite:///:memory:")
        Base.metadata.create_all(db_manager.engine)

        session = db_manager.get_session()

        # Create roles
        for role_name, description in [
            ("admin", "Administrator"),
            ("user", "Regular user"),
            ("analyst", "Analyst"),
        ]:
            role = Role(name=role_name, description=description)
            session.add(role)
        session.commit()

        # Create users
        AuthService.register_user(
            session,
            "admin_user",
            "admin@example.com",
            "AdminPass123",
            role_name=RoleEnum.ADMIN,
        )
        AuthService.register_user(
            session,
            "regular_user",
            "user@example.com",
            "UserPass123",
            role_name=RoleEnum.USER,
        )
        AuthService.register_user(
            session,
            "analyst_user",
            "analyst@example.com",
            "AnalystPass123",
            role_name=RoleEnum.ANALYST,
        )

        yield session
        session.close()

    def test_admin_role(self, db_with_users):
        """Test admin user has correct role"""
        admin = db_with_users.query(User).filter_by(username="admin_user").first()
        assert admin.role.name == "admin"

    def test_user_role(self, db_with_users):
        """Test regular user has correct role"""
        user = db_with_users.query(User).filter_by(username="regular_user").first()
        assert user.role.name == "user"

    def test_analyst_role(self, db_with_users):
        """Test analyst user has correct role"""
        analyst = db_with_users.query(User).filter_by(username="analyst_user").first()
        assert analyst.role.name == "analyst"


@pytest.mark.integration
class TestAuthenticationAPI:
    """Integration tests for authentication endpoints"""

    @pytest.fixture
    def app(self):
        """Create Flask app for testing"""
        test_app = create_app()
        test_app.config["TESTING"] = True
        test_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

        with test_app.app_context():
            from app.models import Base
            from app.db import init_db_manager, get_db_manager
            from app.auth.init import ensure_roles_exist

            # Initialize database manager before use
            init_db_manager("sqlite:///:memory:")

            db_manager = get_db_manager()
            Base.metadata.create_all(db_manager.engine)

            # Initialize default roles
            session = db_manager.get_session()
            try:
                ensure_roles_exist(session)
            finally:
                session.close()

            yield test_app

    @pytest.fixture
    def client(self, app):
        """Create Flask test client"""
        return app.test_client()

    def test_register_endpoint(self, client):
        """Test registration endpoint"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "ValidPass123",
            },
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["success"]
        assert data["user"]["username"] == "testuser"

    def test_login_endpoint(self, client):
        """Test login endpoint"""
        # Register first
        client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "ValidPass123",
            },
        )

        # Login
        response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "ValidPass123"},
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"]
        assert "access_token" in data
        assert data["user"]["username"] == "testuser"

    def test_register_invalid_password(self, client):
        """Test registration with invalid password"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "weak",
            },
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_login_wrong_password(self, client):
        """Test login with wrong password"""
        # Register first
        client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "ValidPass123",
            },
        )

        # Try to login with wrong password
        response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "WrongPass123"},
        )

        assert response.status_code == 401
        data = json.loads(response.data)
        assert "error" in data


class TestDataIsolation:
    """Test that user data is properly isolated"""

    @pytest.fixture
    def db_with_positions(self):
        """Create database with users and positions"""
        from app.models import PortfolioPosition

        db_manager = DatabaseManager("sqlite:///:memory:")
        Base.metadata.create_all(db_manager.engine)

        session = db_manager.get_session()

        # Create role
        role = Role(name="user", description="Regular user")
        session.add(role)
        session.commit()

        # Create two users
        success1, user1, _ = AuthService.register_user(
            session,
            "user1",
            "user1@example.com",
            "ValidPass123",
            role_name=RoleEnum.USER,
        )
        success2, user2, _ = AuthService.register_user(
            session,
            "user2",
            "user2@example.com",
            "ValidPass123",
            role_name=RoleEnum.USER,
        )

        if not (success1 and user1 and success2 and user2):
            raise RuntimeError("Failed to create test users")

        # Add positions for each user
        pos1 = PortfolioPosition(user_id=user1.id, ticker="AAPL", shares=10)
        pos2 = PortfolioPosition(user_id=user2.id, ticker="MSFT", shares=20)

        session.add(pos1)
        session.add(pos2)
        session.commit()

        yield session
        session.close()

    def test_user_can_only_see_own_positions(self, db_with_positions):
        """Test that user1 can only see their own positions"""
        from app.models import PortfolioPosition

        user1 = db_with_positions.query(User).filter_by(username="user1").first()
        user1_positions = (
            db_with_positions.query(PortfolioPosition).filter_by(user_id=user1.id).all()
        )

        assert len(user1_positions) == 1
        assert user1_positions[0].ticker == "AAPL"

    def test_users_have_separate_positions(self, db_with_positions):
        """Test that user1 and user2 have separate positions"""
        from app.models import PortfolioPosition

        user1 = db_with_positions.query(User).filter_by(username="user1").first()
        user2 = db_with_positions.query(User).filter_by(username="user2").first()

        user1_positions = (
            db_with_positions.query(PortfolioPosition).filter_by(user_id=user1.id).all()
        )
        user2_positions = (
            db_with_positions.query(PortfolioPosition).filter_by(user_id=user2.id).all()
        )

        assert len(user1_positions) == 1
        assert len(user2_positions) == 1
        assert user1_positions[0].ticker != user2_positions[0].ticker


class TestAuthInitialization:
    """Test auth module initialization functions"""

    def test_ensure_roles_exist(self) -> None:
        """Test that default roles are created"""
        from app.auth.init import ensure_roles_exist
        from app.db import DatabaseManager
        from config.settings import Config

        db_manager = DatabaseManager(
            Config.DATABASE_URL or "sqlite:///data/market_data.db"
        )
        session = db_manager.get_session()
        try:
            # Ensure roles exist
            ensure_roles_exist(session)

            # Verify roles were created
            admin_role = session.query(Role).filter_by(name="admin").first()
            user_role = session.query(Role).filter_by(name="user").first()
            analyst_role = session.query(Role).filter_by(name="analyst").first()

            assert admin_role is not None
            assert user_role is not None
            assert analyst_role is not None
            assert admin_role.description is not None
            assert user_role.description is not None
            assert analyst_role.description is not None
        finally:
            session.close()

    def test_ensure_roles_exist_idempotent(self) -> None:
        """Test that ensure_roles_exist is idempotent"""
        from app.auth.init import ensure_roles_exist
        from app.db import DatabaseManager
        from config.settings import Config

        db_manager = DatabaseManager(
            Config.DATABASE_URL or "sqlite:///data/market_data.db"
        )
        session = db_manager.get_session()
        try:
            # Call ensure_roles_exist twice
            ensure_roles_exist(session)
            initial_count = session.query(Role).count()

            ensure_roles_exist(session)
            second_count = session.query(Role).count()

            # Should not create duplicates
            assert initial_count == second_count
            assert initial_count >= 3  # At least admin, user, analyst
        finally:
            session.close()

    def test_check_admin_exists_true(self) -> None:
        """Test check_admin_exists returns True when admin exists"""
        from app.auth.init import check_admin_exists
        from app.db import DatabaseManager
        from config.settings import Config

        db_manager = DatabaseManager(
            Config.DATABASE_URL or "sqlite:///data/market_data.db"
        )
        session = db_manager.get_session()
        try:
            # Ensure admin role exists
            admin_role = session.query(Role).filter_by(name="admin").first()
            if not admin_role:
                admin_role = Role(name="admin", description="Admin role")
                session.add(admin_role)
                session.commit()

            # Create an admin user (delete if exists first to avoid uniqueness constraint)
            existing = (
                session.query(User).filter_by(username="auth_init_testadmin").first()
            )
            if existing:
                session.delete(existing)
                session.commit()

            admin_user = User(
                username="auth_init_testadmin",
                email="auth_init_admin@test.com",
                password_hash=PasswordSecurity.hash_password("TestPass123"),
                role_id=admin_role.id,
                status="active",
            )
            session.add(admin_user)
            session.commit()

            # Check admin exists
            assert check_admin_exists(session) is True
        finally:
            session.close()

    def test_check_admin_exists_false(self) -> None:
        """Test check_admin_exists returns False when no admin exists"""
        from app.auth.init import check_admin_exists
        from app.db import DatabaseManager
        from config.settings import Config

        db_manager = DatabaseManager(
            Config.DATABASE_URL or "sqlite:///data/market_data.db"
        )
        session = db_manager.get_session()
        try:
            # Delete all users
            session.query(User).delete()
            session.commit()

            # Check admin exists
            assert check_admin_exists(session) is False
        finally:
            session.close()

    def test_create_admin_from_env_missing_vars(self) -> None:
        """Test create_admin_from_env returns None when env vars not set"""
        from app.auth.init import create_admin_from_env
        from app.db import DatabaseManager
        from config.settings import Config
        import os

        # Ensure env vars are not set
        os.environ.pop("ADMIN_USERNAME", None)
        os.environ.pop("ADMIN_PASSWORD", None)

        db_manager = DatabaseManager(
            Config.DATABASE_URL or "sqlite:///data/market_data.db"
        )
        session = db_manager.get_session()
        try:
            result = create_admin_from_env(session)
            assert result is None
        finally:
            session.close()

    def test_create_admin_from_env_success(self) -> None:
        """Test successful admin creation from environment variables"""
        from app.auth.init import create_admin_from_env
        from app.db import DatabaseManager
        from config.settings import Config
        import os

        # Set environment variables
        os.environ["ADMIN_USERNAME"] = "envadmin"
        os.environ["ADMIN_PASSWORD"] = "EnvAdminPass123"

        db_manager = DatabaseManager(
            Config.DATABASE_URL or "sqlite:///data/market_data.db"
        )
        session = db_manager.get_session()
        try:
            # Delete existing user
            session.query(User).filter_by(username="envadmin").delete()
            session.commit()

            result = create_admin_from_env(session)
            assert result is not None
            assert "created" in result.lower()

            # Verify user was created
            user = session.query(User).filter_by(username="envadmin").first()
            assert user is not None
        finally:
            session.close()
            # Clean up env vars
            os.environ.pop("ADMIN_USERNAME", None)
            os.environ.pop("ADMIN_PASSWORD", None)

    def test_initialize_admin_on_startup_existing_admin(self) -> None:
        """Test initialize_admin_on_startup does nothing when admin exists"""
        from app.auth.init import initialize_admin_on_startup
        from app.db import DatabaseManager
        from config.settings import Config

        db_manager = DatabaseManager(
            Config.DATABASE_URL or "sqlite:///data/market_data.db"
        )
        session = db_manager.get_session()
        try:
            # Ensure admin exists
            admin_role = session.query(Role).filter_by(name="admin").first()
            if not admin_role:
                admin_role = Role(name="admin", description="Admin")
                session.add(admin_role)
                session.commit()

            existing_admin = (
                session.query(User).filter_by(username="startup_admin").first()
            )
            if not existing_admin:
                existing_admin = User(
                    username="startup_admin",
                    email="startup@test.com",
                    password_hash=PasswordSecurity.hash_password("Pass123"),
                    role_id=admin_role.id,
                    status="active",
                )
                session.add(existing_admin)
                session.commit()

            # Should not raise an exception
            initialize_admin_on_startup(session)
        finally:
            session.close()

    def test_initialize_admin_on_startup_no_admin(self) -> None:
        """Test initialize_admin_on_startup with no admin user"""
        from app.auth.init import initialize_admin_on_startup
        from app.db import DatabaseManager
        from config.settings import Config
        import os

        # Ensure env vars not set
        os.environ.pop("ADMIN_USERNAME", None)
        os.environ.pop("ADMIN_PASSWORD", None)

        db_manager = DatabaseManager(
            Config.DATABASE_URL or "sqlite:///data/market_data.db"
        )
        session = db_manager.get_session()
        try:
            # Delete all users
            session.query(User).delete()
            session.commit()

            # Should not raise an exception
            initialize_admin_on_startup(session)
        finally:
            session.close()
