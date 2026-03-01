"""
Market data models for OHLCV data, intraday data, and metadata

Tables:
- daily_data: Daily OHLCV data
- intraday_data: Intraday market data
- metadata: Stock metadata (company info, sector, industry, etc.)
"""

from datetime import date as date_type, datetime as datetime_type
from decimal import Decimal
from sqlalchemy import Index, String, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class DailyData(Base, TimestampMixin):
    """Daily OHLCV market data

    Stores daily open, high, low, close, volume data along with
    dividend and stock split adjustments.
    """

    __tablename__ = "daily_data"
    __table_args__ = (Index("idx_daily_data_ticker_date", "ticker", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    ticker: Mapped[str] = mapped_column(String(10))
    date: Mapped[date_type] = mapped_column(Date())
    open: Mapped[Decimal] = mapped_column()
    high: Mapped[Decimal] = mapped_column()
    low: Mapped[Decimal] = mapped_column()
    close: Mapped[Decimal] = mapped_column()
    volume: Mapped[int] = mapped_column()
    dividends: Mapped[Decimal | None] = mapped_column(default=None)
    stock_splits: Mapped[Decimal | None] = mapped_column(default=None)


class IntradayData(Base, TimestampMixin):
    """Intraday market data

    Stores intraday OHLCV data at minute or hour granularity.
    """

    __tablename__ = "intraday_data"
    __table_args__ = (Index("idx_intraday_data_ticker_datetime", "ticker", "datetime"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    ticker: Mapped[str] = mapped_column(String(10))
    datetime: Mapped[datetime_type] = mapped_column(DateTime())
    open: Mapped[Decimal] = mapped_column()
    high: Mapped[Decimal] = mapped_column()
    low: Mapped[Decimal] = mapped_column()
    close: Mapped[Decimal] = mapped_column()
    volume: Mapped[int] = mapped_column()


class Metadata(Base, TimestampMixin):
    """Stock metadata information

    Stores company information like name, sector, industry,
    market cap, and last update timestamp.
    """

    __tablename__ = "metadata"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), unique=True)
    company_name: Mapped[str | None] = mapped_column(default=None)
    sector: Mapped[str | None] = mapped_column(default=None)
    industry: Mapped[str | None] = mapped_column(default=None)
    market_cap: Mapped[Decimal | None] = mapped_column(default=None)
    last_updated: Mapped[datetime_type | None] = mapped_column(DateTime(), default=None)
