"""
Audit logging models for system-wide event tracking

This module provides generic audit logging capability for tracking
application events and user actions across the system.
"""

from datetime import datetime
from sqlalchemy import String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SystemAuditLog(Base, TimestampMixin):
    """System-wide audit log

    Tracks application events including data changes, API calls,
    and system operations. Can be tied to users or generic system events.
    """
    __tablename__ = "system_audit_logs"
    __table_args__ = (
        Index("idx_system_audit_logs_action", "action"),
        Index("idx_system_audit_logs_resource_type", "resource_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(String(50))  # create, update, delete, etc.
    resource_type: Mapped[str] = mapped_column(String(50))  # user, portfolio, signal, etc.
    resource_id: Mapped[str | None] = mapped_column(String(50), default=None)
    user_id: Mapped[int | None] = mapped_column(default=None)  # Can be null for system events
    changes: Mapped[str | None] = mapped_column(Text, default=None)  # JSON with before/after
    details: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(String(20), default="success")  # success, failed, warning
