"""
tests/__init__.py
Test package initialization with fixtures, mocks, and sample data
"""

import os
import sys
import tempfile
import unittest
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pandas as pd
import numpy as np

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


class BaseTestCase(unittest.TestCase):
    """Base test case with in-memory SQLite and temporary file fallback"""

    # Demo API key for testing (from app/api/auth.py)
    TEST_API_KEY = "test-api-key-67890"

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary database file for tests that require file paths
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.test_db.close()

        # Use in-memory SQLite for memory-based tests
        self.test_db_memory = sqlite3.connect(":memory:")
        self.test_db_path = self.test_db.name

        # Initialize database schema in both memory and file
        self._init_test_database(self.test_db_memory)
        # Create and properly close file-based connection
        file_db_conn = sqlite3.connect(self.test_db.name)
        self._init_test_database(file_db_conn)
        file_db_conn.close()

        # Set test environment
        os.environ["FLASK_ENV"] = "testing"
        os.environ["DATABASE_PATH"] = self.test_db.name

    def get_auth_headers(self, api_key=None):
        """Get headers with Bearer token authentication

        Args:
            api_key: API key to use (default: TEST_API_KEY)

        Returns:
            dict: Headers dict with Authorization bearer token
        """
        if api_key is None:
            api_key = self.TEST_API_KEY
        return {"Authorization": f"Bearer {api_key}"}

    def tearDown(self):
        """Clean up test fixtures"""
        # Close in-memory database connection
        if hasattr(self, "test_db_memory") and self.test_db_memory:
            try:
                # Rollback any pending transactions
                try:
                    self.test_db_memory.rollback()
                except Exception:
                    pass
                # Close all cursors and the connection
                self.test_db_memory.close()
            except Exception:
                pass
            finally:
                self.test_db_memory = None

        # Clean up temporary database file
        if hasattr(self, "test_db") and self.test_db.name:
            try:
                if os.path.exists(self.test_db.name):
                    os.unlink(self.test_db.name)
            except Exception:
                pass

    def _init_test_database(self, connection=None):
        """Initialize database schema for testing"""
        if connection is None:
            connection = self.test_db_memory
        cursor = connection.cursor()

        # Create all required tables
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_data (
                ticker TEXT,
                date DATE,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                dividends REAL,
                stock_splits REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (ticker, date)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS intraday_data (
                ticker TEXT,
                datetime TIMESTAMP,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (ticker, datetime)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                ticker TEXT PRIMARY KEY,
                company_name TEXT,
                sector TEXT,
                industry TEXT,
                market_cap REAL,
                last_updated TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS signal_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT,
                date DATE,
                signal_type TEXT,
                signal_value REAL,
                confidence REAL,
                entry_price REAL,
                target_price REAL,
                stop_loss REAL,
                regime TEXT,
                reasons TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS portfolio_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE,
                portfolio_value REAL,
                daily_return REAL,
                volatility REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS system_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                description TEXT,
                details TEXT,
                severity TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS portfolio_positions (
                ticker TEXT PRIMARY KEY,
                shares REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create indexes
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_daily_data_ticker_date
            ON daily_data(ticker, date DESC)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_signal_history_ticker_date
            ON signal_history(ticker, date DESC)
        """
        )

        cursor.close()
        connection.commit()
        # Close if not the in-memory instance
        if connection != self.test_db_memory:
            connection.close()


# ============================================================================
# SAMPLE DATA GENERATORS
# ============================================================================


class SampleDataGenerator:
    """Generate realistic sample market data for testing"""

    @staticmethod
    def generate_ohlcv_data(
        ticker: str = "AAPL",
        days: int = 100,
        start_price: float = 100.0,
        volatility: float = 0.02,
    ) -> pd.DataFrame:
        """Generate realistic OHLCV data using random walk"""
        dates = pd.date_range(end=datetime.now(), periods=days, freq="D")
        closes = [start_price]

        # Generate price using random walk
        for _ in range(days - 1):
            daily_return = np.random.normal(0.0005, volatility)
            closes.append(closes[-1] * (1 + daily_return))

        closes = np.array(closes)

        data = {
            "Date": dates,
            "Open": closes * (1 + np.random.uniform(-0.01, 0.01, days)),
            "High": closes * (1 + np.random.uniform(0.01, 0.03, days)),
            "Low": closes * (1 + np.random.uniform(-0.03, -0.01, days)),
            "Close": closes,
            "Volume": np.random.randint(1000000, 10000000, days),
            "Adj Close": closes,
            "Dividends": np.zeros(days),
            "Stock Splits": np.ones(days),
        }

        df = pd.DataFrame(data)
        df["Ticker"] = ticker
        return df

    @staticmethod
    def generate_signal_data(ticker: str = "AAPL") -> Dict[str, Any]:
        """Generate sample signal data"""
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
        """Generate sample portfolio position"""
        return {"ticker": ticker, "shares": shares}

    @staticmethod
    def generate_performance_data(days: int = 30, starting_value: float = 100000) -> List[Dict]:
        """Generate sample portfolio performance data"""
        performance = []
        values = [starting_value]

        for i in range(days):
            daily_return = np.random.normal(0.0005, 0.01)
            new_value = values[-1] * (1 + daily_return)
            values.append(new_value)

            performance.append(
                {
                    "date": (datetime.now() - timedelta(days=days - i)).date(),
                    "portfolio_value": new_value,
                    "daily_return": daily_return,
                    "volatility": 0.15,
                    "sharpe_ratio": 1.2,
                    "max_drawdown": 0.05,
                }
            )

        return performance


# ============================================================================
# MOCK HELPERS
# ============================================================================


class YFinanceMockHelper:
    """Helper for mocking yfinance API calls"""

    @staticmethod
    def create_mock_download(ticker_data: Dict[str, pd.DataFrame]):
        """Create a mock yfinance.download function"""

        def mock_download(tickers, start=None, end=None, progress=False):
            if isinstance(tickers, str):
                return ticker_data.get(tickers, pd.DataFrame())
            # Multi-ticker download
            return pd.concat(
                [ticker_data.get(t, pd.DataFrame()).assign(Ticker=t) for t in tickers],
                ignore_index=True,
            )

        return mock_download

    @staticmethod
    def create_mock_ticker():
        """Create a mock yfinance.Ticker class"""

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


# ============================================================================
# COMMON TEST FIXTURES
# ============================================================================


@staticmethod
def get_sample_portfolio() -> Dict[str, float]:
    """Get sample portfolio with test tickers"""
    return {
        "AAPL": 50.0,
        "MSFT": 30.0,
        "GOOGL": 20.0,
        "AMZN": 15.0,
    }


@staticmethod
def get_sample_prices() -> Dict[str, float]:
    """Get sample current prices"""
    return {
        "AAPL": 150.0,
        "MSFT": 330.0,
        "GOOGL": 140.0,
        "AMZN": 130.0,
    }


def run_all_tests():
    """Run all tests in the test suite"""
    loader = unittest.TestLoader()
    suite = loader.discover("tests", pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
