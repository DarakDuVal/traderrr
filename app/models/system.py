"""
System models for application events and logging

Tables:
- system_events: Application system events log
"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SystemEvent(Base, TimestampMixin):
    """System event log

    Logs application events including info, warnings, and errors.
    """

    __tablename__ = "system_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(String(255))
    details: Mapped[str | None] = mapped_column(Text, default=None)
    severity: Mapped[str] = mapped_column(String(20))  # INFO, WARNING, ERROR
