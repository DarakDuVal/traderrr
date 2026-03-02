"""
Auth routes — POST /api/v1/auth/login, /refresh, /logout, GET /me
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.auth.service import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from config.settings import Settings, get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Authenticate user, return access_token and set refresh_token cookie."""
    result = await db.execute(
        select(User)
        .options(selectinload(User.role))
        .where(User.username == body.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is not active",
        )

    access = create_access_token(
        user.id,
        user.role.name,
        settings.SECRET_KEY,
        settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    refresh = create_refresh_token(
        user.id,
        settings.SECRET_KEY,
        settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        secure=settings.ENVIRONMENT != "development",
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",
    )

    return TokenResponse(access_token=access)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Read refresh_token from httpOnly cookie, return new access_token."""
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )

    try:
        payload = decode_token(token, settings.SECRET_KEY)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    result = await db.execute(
        select(User)
        .options(selectinload(User.role))
        .where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()

    if not user or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    access = create_access_token(
        user.id,
        user.role.name,
        settings.SECRET_KEY,
        settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    return TokenResponse(access_token=access)


@router.post("/logout")
async def logout(response: Response) -> dict:
    """Clear the refresh_token cookie."""
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")
    return {"detail": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return current authenticated user profile."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role.name,
        status=current_user.status,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
    )
