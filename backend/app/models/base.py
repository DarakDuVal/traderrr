"""
Base model class for SQLAlchemy ORM

Provides:
- Base DeclarativeBase for all models
- TimestampMixin for automatic created_at/updated_at tracking
"""

from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""

    pass


class TimestampMixin:
    """Mixin class for automatic timestamp tracking

    Adds created_at and updated_at columns to any model that uses this mixin.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
