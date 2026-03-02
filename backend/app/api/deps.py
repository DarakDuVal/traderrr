"""
app/api/deps.py — Shared FastAPI dependencies

Provides:
- get_db: async database session
- get_current_user: JWT Bearer auth
- require_role: RBAC enforcement
"""

import logging
from typing import AsyncIterator, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config.settings import Settings, get_settings
from app.auth.service import decode_token
from app.models.user import User

logger = logging.getLogger(__name__)

security = HTTPBearer()


# ── Database session ──────────────────────────────────────────────────────

_engine = None
_async_session_factory = None


def _get_engine(settings: Settings) -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            pool_size=20,
            max_overflow=40,
        )
    return _engine


def _get_session_factory(settings: Settings) -> async_sessionmaker:
    global _async_session_factory
    if _async_session_factory is None:
        engine = _get_engine(settings)
        _async_session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
    return _async_session_factory


async def get_db(
    settings: Settings = Depends(get_settings),
) -> AsyncIterator[AsyncSession]:
    """Yield an async database session, then close it."""
    factory = _get_session_factory(settings)
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Current user (JWT) ────────────────────────────────────────────────────


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """Validate JWT Bearer token and return the current user."""
    token = credentials.credentials
    try:
        payload = decode_token(token, settings.SECRET_KEY)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id: int | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()

    if user is None or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


# ── Role-based access ─────────────────────────────────────────────────────


def require_role(*allowed_roles: str) -> Callable:
    """Return a dependency that checks the user's role."""

    async def _check_role(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role.name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}",
            )
        return current_user

    return _check_role
