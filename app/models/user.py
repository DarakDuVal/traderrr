"""
User authentication and authorization models

Tables:
- users: User accounts with password hashing
- roles: User roles (admin, user, analyst)
- permissions: Fine-grained permissions
- role_permissions: Many-to-many relationship
- api_keys: User API keys for programmatic access
"""

from datetime import datetime
from sqlalchemy import String, Text, Boolean, ForeignKey, Table, Column, Integer, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import Base, TimestampMixin


class RoleEnum(str, enum.Enum):
    """Role enumeration"""
    ADMIN = "admin"
    USER = "user"
    ANALYST = "analyst"


class Permission(Base, TimestampMixin):
    """Permission definition

    Fine-grained permission control for role-based access.
    Permissions can be combined to create roles with specific capabilities.
    """
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(255), default=None)

    # Relationships
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions"
    )


class Role(Base, TimestampMixin):
    """User role

    Defines role with associated permissions.
    Three built-in roles: admin, user, analyst.
    """
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str | None] = mapped_column(String(255), default=None)

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="role"
    )
    permissions: Mapped[list[Permission]] = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles"
    )


# Association table for role-permission many-to-many relationship
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)


class User(Base, TimestampMixin):
    """User account

    Stores user credentials and profile information.
    Each user has a role determining their permissions.
    """
    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_username", "username"),
        Index("idx_users_email", "email"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(120), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    status: Mapped[str] = mapped_column(
        String(20),
        default="active"
    )  # active, inactive, suspended
    last_login: Mapped[datetime | None] = mapped_column(default=None)

    # Relationships
    role: Mapped[Role] = relationship("Role", back_populates="users")
    api_keys: Mapped[list["APIKey"]] = relationship(
        "APIKey",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["UserAuditLog"]] = relationship(
        "UserAuditLog",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class APIKey(Base, TimestampMixin):
    """API key for programmatic access

    Allows users to authenticate via API keys instead of passwords.
    Keys are hashed and never stored in plaintext.
    """
    __tablename__ = "api_keys"
    __table_args__ = (
        Index("idx_api_keys_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    key_hash: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(100))  # For user reference
    expires_at: Mapped[datetime | None] = mapped_column(default=None)
    last_used: Mapped[datetime | None] = mapped_column(default=None)
    is_revoked: Mapped[bool] = mapped_column(default=False)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="api_keys")


class UserAuditLog(Base, TimestampMixin):
    """User action audit log

    Tracks all user actions for security and compliance purposes.
    Records login, logout, API calls, and data modifications.
    """
    __tablename__ = "user_audit_logs"
    __table_args__ = (
        Index("idx_audit_logs_user_id", "user_id"),
        Index("idx_audit_logs_action", "action"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(50))  # login, logout, api_call, etc.
    resource: Mapped[str | None] = mapped_column(String(100), default=None)  # portfolio, signal, etc.
    details: Mapped[str | None] = mapped_column(Text, default=None)  # JSON with additional info
    ip_address: Mapped[str | None] = mapped_column(String(50), default=None)
    user_agent: Mapped[str | None] = mapped_column(String(255), default=None)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="audit_logs")
