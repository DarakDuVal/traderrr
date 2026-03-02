"""
Admin routes — /api/v1/admin (admin role required)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, require_role
from app.models.user import User
from app.schemas.auth import UserResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/users", response_model=list[UserResponse])  # type: ignore[misc, untyped-decorator]
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
) -> list[UserResponse]:
    """List all users (admin only)."""
    result = await db.execute(select(User).options(selectinload(User.role)))
    users = result.scalars().all()
    return [
        UserResponse(
            id=u.id,
            username=u.username,
            email=u.email,
            role=u.role.name,
            status=u.status,
            created_at=u.created_at,
            last_login=u.last_login,
        )
        for u in users
    ]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)  # type: ignore[misc, untyped-decorator]
async def create_user(
    username: str,
    email: str,
    password: str,
    role: str = "user",
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
) -> UserResponse:
    """Create a new user (admin only)."""
    from app.auth.service import hash_password, validate_password_strength
    from app.models.user import Role

    is_valid, error = validate_password_strength(password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    # Check existing
    existing = await db.execute(
        select(User).where((User.username == username) | (User.email == email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )

    role_obj = (
        await db.execute(select(Role).where(Role.name == role))
    ).scalar_one_or_none()
    if not role_obj:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Role '{role}' not found"
        )

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        role_id=role_obj.id,
        status="active",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user, attribute_names=["role"])

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.name,
        status=user.status,
        created_at=user.created_at,
        last_login=user.last_login,
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)  # type: ignore[misc, untyped-decorator]
async def deactivate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
) -> dict:
    """Deactivate a user (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    user.status = "inactive"
    await db.flush()
    return {"detail": f"User {user.username} deactivated"}


@router.get("/system")  # type: ignore[misc, untyped-decorator]
async def system_status(
    admin: User = Depends(require_role("admin")),
) -> dict:
    """Return system status (admin only)."""
    import psutil

    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
    }
