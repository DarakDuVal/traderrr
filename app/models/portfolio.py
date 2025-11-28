"""
Portfolio models for tracking held positions

Tables:
- portfolio_positions: Current portfolio holdings
"""

from decimal import Decimal
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PortfolioPosition(Base, TimestampMixin):
    """Portfolio position

    Tracks current held positions in the portfolio including
    ticker symbol and number of shares.
    """

    __tablename__ = "portfolio_positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    ticker: Mapped[str] = mapped_column(String(10))
    shares: Mapped[Decimal] = mapped_column()
