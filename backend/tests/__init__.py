"""
tests/__init__.py
Test package — FastAPI + SQLite test infrastructure

Legacy helpers (SampleDataGenerator, YFinanceMockHelper) are preserved
for core logic tests that don't depend on the web framework.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any

import numpy as np
import pandas as pd

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


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
