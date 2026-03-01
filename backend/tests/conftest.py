"""
tests/conftest.py — FastAPI TestClient fixtures

Provides:
- db_session: isolated SQLite session per test (sync, for seeding data)
- client: FastAPI TestClient with async get_db override (aiosqlite)
- auth_headers: logged-in test user Bearer headers
"""

import os
import tempfile
import warnings
import pytest
import sys

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from fastapi.testclient import TestClient

from app.main import create_app
from app.models.base import Base
from app.models.user import User, Role, RoleEnum
from app.auth.service import hash_password, create_access_token
from config.settings import Settings


# ── Warning suppression (preserved from legacy conftest) ──────────────────

def pytest_configure(config):
    warnings.filterwarnings("ignore", category=ResourceWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    config.addinivalue_line("filterwarnings", "ignore::ResourceWarning")
    config.addinivalue_line("filterwarnings", "ignore::DeprecationWarning")
    config.addinivalue_line("filterwarnings", "ignore::FutureWarning")


def pytest_collection_modifyitems(config, items):
    for item in items:
        item.add_marker(pytest.mark.filterwarnings("ignore::ResourceWarning"))


_original_hook = sys.unraisablehook


def custom_unraisable_hook(unraisable_msg):
    if "unclosed database" not in str(unraisable_msg.exc_value):
        _original_hook(unraisable_msg)


sys.unraisablehook = custom_unraisable_hook


# ── Test settings ─────────────────────────────────────────────────────────

_TEST_SECRET = "test-secret-key-for-jwt-testing-32chars"


# ── File-based SQLite for shared sync/async access ───────────────────────

@pytest.fixture()
def db_file():
    """Create a temp SQLite file shared by sync and async engines."""
    f = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    f.close()
    yield f.name
    try:
        os.unlink(f.name)
    except OSError:
        pass


@pytest.fixture()
def db_engine(db_file):
    """Sync SQLite engine for seeding test data."""
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """Sync SQLAlchemy session for test setup/teardown."""
    factory = sessionmaker(bind=db_engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ── Seed roles and test user ──────────────────────────────────────────────

@pytest.fixture()
def seed_roles(db_session):
    """Ensure default roles exist."""
    for role_name in [RoleEnum.ADMIN, RoleEnum.USER, RoleEnum.ANALYST]:
        if not db_session.query(Role).filter_by(name=role_name).first():
            db_session.add(Role(name=role_name, description=f"{role_name} role"))
    db_session.commit()
    return db_session


@pytest.fixture()
def test_user(seed_roles):
    """Create and return a test user with 'user' role."""
    session = seed_roles
    user = session.query(User).filter_by(username="testuser").first()
    if not user:
        role = session.query(Role).filter_by(name=RoleEnum.USER).first()
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=hash_password("TestPass123"),
            role_id=role.id,
            status="active",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


@pytest.fixture()
def admin_user(seed_roles):
    """Create and return an admin user."""
    session = seed_roles
    user = session.query(User).filter_by(username="adminuser").first()
    if not user:
        role = session.query(Role).filter_by(name=RoleEnum.ADMIN).first()
        user = User(
            username="adminuser",
            email="admin@example.com",
            password_hash=hash_password("AdminPass123"),
            role_id=role.id,
            status="active",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def _get_test_settings(db_file: str):
    """Return a factory for test Settings pointing at the given db file."""
    def _factory() -> Settings:
        return Settings(
            DATABASE_URL=f"sqlite+aiosqlite:///{db_file}",
            SECRET_KEY=_TEST_SECRET,
            ENVIRONMENT="testing",
            REDIS_URL="redis://localhost:6379/0",
        )
    return _factory


# ── FastAPI TestClient ────────────────────────────────────────────────────

@pytest.fixture()
def client(db_file, db_engine, seed_roles):
    """FastAPI TestClient with async get_db override (aiosqlite)."""
    from app.api.deps import get_db
    from config.settings import get_settings

    app = create_app()

    # Async engine pointing at the same file-based SQLite
    async_engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    _async_session = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with _async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = _get_test_settings(db_file)

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.dependency_overrides.clear()


# ── Auth headers ──────────────────────────────────────────────────────────

@pytest.fixture()
def auth_headers(test_user) -> dict:
    """Return Bearer headers for the test user."""
    token = create_access_token(
        subject=test_user.id,
        role=test_user.role.name,
        secret_key=_TEST_SECRET,
        expires_minutes=60,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_headers(admin_user) -> dict:
    """Return Bearer headers for an admin user."""
    token = create_access_token(
        subject=admin_user.id,
        role=admin_user.role.name,
        secret_key=_TEST_SECRET,
        expires_minutes=60,
    )
    return {"Authorization": f"Bearer {token}"}
