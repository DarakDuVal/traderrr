"""
Trading-related models for signals and portfolio performance

Tables:
- signal_history: Historical trading signals
- portfolio_performance: Portfolio performance metrics over time
"""

from datetime import date as date_type, datetime
from decimal import Decimal
from sqlalchemy import Date, Index, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SignalHistory(Base, TimestampMixin):
    """Trading signal history

    Stores all generated trading signals with analysis details.
    Signal types: BUY, SELL, HOLD
    """
    __tablename__ = "signal_history"
    __table_args__ = (
        Index("idx_signal_history_ticker_date", "ticker", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    ticker: Mapped[str] = mapped_column(String(10))
    date: Mapped[date_type] = mapped_column(Date())
    signal_type: Mapped[str] = mapped_column(String(20))  # BUY, SELL, HOLD
    signal_value: Mapped[Decimal] = mapped_column()
    confidence: Mapped[Decimal] = mapped_column()
    entry_price: Mapped[Decimal] = mapped_column()
    target_price: Mapped[Decimal] = mapped_column()
    stop_loss: Mapped[Decimal] = mapped_column()
    regime: Mapped[str | None] = mapped_column(String(20), default=None)
    reasons: Mapped[str] = mapped_column(Text)


class PortfolioPerformance(Base, TimestampMixin):
    """Portfolio performance metrics

    Tracks daily portfolio performance including value, returns,
    volatility, Sharpe ratio, and maximum drawdown.
    """
    __tablename__ = "portfolio_performance"
    __table_args__ = (
        Index("idx_portfolio_performance_date", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    date: Mapped[date_type] = mapped_column(Date())
    portfolio_value: Mapped[Decimal] = mapped_column()
    daily_return: Mapped[Decimal] = mapped_column()
    volatility: Mapped[Decimal] = mapped_column()
    sharpe_ratio: Mapped[Decimal | None] = mapped_column(default=None)
    max_drawdown: Mapped[Decimal | None] = mapped_column(default=None)
