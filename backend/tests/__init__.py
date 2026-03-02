"""
tests/__init__.py
Test package — FastAPI + SQLite test infrastructure

Provides:
- BaseTestCase: Simplified base class for core-logic tests (no Flask)
- SampleDataGenerator: Realistic market data generation
- YFinanceMockHelper: yfinance API mocking
"""

import os
import sys
import tempfile
import unittest
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any

import numpy as np
import pandas as pd

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


# ============================================================================
# BASE TEST CASE (database-only, no Flask)
# ============================================================================


class BaseTestCase(unittest.TestCase):
    """Base test case with in-memory SQLite and temporary file fallback.

    Provides database setup for core logic tests that don't require a web
    framework.  The old Flask-specific helpers (get_auth_headers, create_app)
    have been removed — use the FastAPI fixtures in conftest.py instead.
    """

    def setUp(self):
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.test_db.close()
        self.test_db_memory = sqlite3.connect(":memory:")
        self.test_db_path = self.test_db.name

        os.environ.setdefault("FLASK_ENV", "testing")
        os.environ["DATABASE_PATH"] = self.test_db.name

    def tearDown(self):
        if hasattr(self, "test_db_memory") and self.test_db_memory:
            try:
                self.test_db_memory.rollback()
            except Exception:
                pass
            try:
                self.test_db_memory.close()
            except Exception:
                pass
            self.test_db_memory = None

        if hasattr(self, "test_db") and self.test_db.name:
            try:
                if os.path.exists(self.test_db.name):
                    os.unlink(self.test_db.name)
            except Exception:
                pass

    def _init_test_database(self, connection=None):
        """Initialize raw SQLite tables for testing."""
        if connection is None:
            connection = self.test_db_memory
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_data (
                ticker TEXT, date DATE, open REAL, high REAL, low REAL,
                close REAL, volume INTEGER, dividends REAL, stock_splits REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (ticker, date)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS intraday_data (
                ticker TEXT, datetime TIMESTAMP, open REAL, high REAL,
                low REAL, close REAL, volume INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (ticker, datetime)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                ticker TEXT PRIMARY KEY, company_name TEXT, sector TEXT,
                industry TEXT, market_cap REAL, last_updated TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signal_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT,
                date DATE, signal_type TEXT, signal_value REAL,
                confidence REAL, entry_price REAL, target_price REAL,
                stop_loss REAL, regime TEXT, reasons TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT, date DATE,
                portfolio_value REAL, daily_return REAL, volatility REAL,
                sharpe_ratio REAL, max_drawdown REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT,
                description TEXT, details TEXT, severity TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_positions (
                ticker TEXT PRIMARY KEY, shares REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_daily_data_ticker_date
            ON daily_data(ticker, date DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_signal_history_ticker_date
            ON signal_history(ticker, date DESC)
        """)

        cursor.close()
        connection.commit()
        if connection != self.test_db_memory:
            connection.close()


# ============================================================================
# SAMPLE DATA GENERATORS
# ============================================================================


class SampleDataGenerator:
    """Generate realistic sample market data for testing."""

    @staticmethod
    def generate_ohlcv_data(
        ticker: str = "AAPL",
        days: int = 100,
        start_price: float = 100.0,
        volatility: float = 0.02,
    ) -> pd.DataFrame:
        dates = pd.date_range(end=datetime.now(), periods=days, freq="D")
        closes = [start_price]
        for _ in range(days - 1):
            daily_return = np.random.normal(0.0005, volatility)
            closes.append(closes[-1] * (1 + daily_return))
        closes_arr = np.array(closes)
        data = {
            "Date": dates,
            "Open": closes_arr * (1 + np.random.uniform(-0.01, 0.01, days)),
            "High": closes_arr * (1 + np.random.uniform(0.01, 0.03, days)),
            "Low": closes_arr * (1 + np.random.uniform(-0.03, -0.01, days)),
            "Close": closes_arr,
            "Volume": np.random.randint(1000000, 10000000, days),
            "Adj Close": closes_arr,
            "Dividends": np.zeros(days),
            "Stock Splits": np.ones(days),
        }
        df = pd.DataFrame(data)
        df["Ticker"] = ticker
        return df

    @staticmethod
    def generate_signal_data(ticker: str = "AAPL") -> Dict[str, Any]:
        return {
            "ticker": ticker,
            "date": datetime.now().date().isoformat(),
            "signal_type": "BUY",
            "signal_value": 0.75,
            "confidence": 0.85,
            "entry_price": 150.0,
            "target_price": 160.0,
            "stop_loss": 145.0,
            "regime": "TRENDING_UP",
            "reasons": "RSI bullish, MACD positive crossover",
        }

    @staticmethod
    def generate_portfolio_position(ticker: str, shares: float) -> Dict:
        return {"ticker": ticker, "shares": shares}

    @staticmethod
    def generate_performance_data(
        days: int = 30, starting_value: float = 100000
    ) -> List[Dict]:
        performance = []
        values = [starting_value]
        for i in range(days):
            daily_return = np.random.normal(0.0005, 0.01)
            new_value = values[-1] * (1 + daily_return)
            values.append(new_value)
            performance.append({
                "date": (datetime.now() - timedelta(days=days - i)).date(),
                "portfolio_value": new_value,
                "daily_return": daily_return,
                "volatility": 0.15,
                "sharpe_ratio": 1.2,
                "max_drawdown": 0.05,
            })
        return performance


class YFinanceMockHelper:
    """Helper for mocking yfinance API calls."""

    @staticmethod
    def create_mock_download(ticker_data: Dict[str, pd.DataFrame]):
        def mock_download(tickers, start=None, end=None, progress=False):
            if isinstance(tickers, str):
                return ticker_data.get(tickers, pd.DataFrame())
            return pd.concat(
                [ticker_data.get(t, pd.DataFrame()).assign(Ticker=t) for t in tickers],
                ignore_index=True,
            )
        return mock_download

    @staticmethod
    def create_mock_ticker():
        class MockTicker:
            def __init__(self, ticker_name):
                self.ticker_name = ticker_name
            def history(self, period="1y", start=None, end=None):
                return SampleDataGenerator.generate_ohlcv_data(self.ticker_name)
            def info(self):
                return {
                    "symbol": self.ticker_name,
                    "longName": f"{self.ticker_name} Company",
                    "sector": "Technology",
                    "industry": "Software",
                    "marketCap": 2000000000000,
                }
        return MockTicker
