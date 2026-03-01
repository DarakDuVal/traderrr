#!/usr/bin/env python3
"""
utils/dev_tools.py - Development utilities
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def generate_sample_data(ticker: str, days: int = 252) -> pd.DataFrame:
    """Generate realistic sample stock data for testing"""
    dates = pd.date_range(end=datetime.now(), periods=days, freq="D")

    # Generate realistic price movement
    returns = np.random.normal(0.0008, 0.02, days)  # ~20% annual vol
    prices = 100 * np.exp(np.cumsum(returns))

    # Generate OHLCV data
    data = pd.DataFrame(
        {
            "Date": dates,
            "Open": prices * np.random.uniform(0.995, 1.005, days),
            "High": prices * np.random.uniform(1.005, 1.025, days),
            "Low": prices * np.random.uniform(0.975, 0.995, days),
            "Close": prices,
            "Volume": np.random.randint(1000000, 10000000, days),
            "Dividends": np.zeros(days),
            "Stock Splits": np.zeros(days),
        }
    )

    # Set Date as index to match yfinance format
    data.set_index("Date", inplace=True)

    # Ensure OHLC consistency
    for i in range(len(data)):
        high = max(data.iloc[i][["Open", "High", "Close"]])
        low = min(data.iloc[i][["Open", "Low", "Close"]])
        data.iloc[i, data.columns.get_loc("High")] = high
        data.iloc[i, data.columns.get_loc("Low")] = low

    return data


def populate_sample_database():
    """Populate database with sample data for testing"""
    from app.core.data_manager import DataManager
    from config.settings import Config

    dm = DataManager()
    sample_tickers = ["AAPL", "MSFT", "GOOGL", "VTI", "SPY"]

    print("Generating sample data...")
    for ticker in sample_tickers:
        print(f"Creating sample data for {ticker}")
        sample_data = generate_sample_data(ticker, 365)
        dm._store_data(ticker, sample_data, "1d")

    dm.close()
    print("[OK] Sample database populated")


def quick_test():
    """Run quick functionality test"""
    from app.core.data_manager import DataManager
    from app.core.signal_generator import SignalGenerator

    print("Running quick test...")

    # Test data manager
    dm = DataManager()
    test_data = generate_sample_data("TEST", 100)
    dm._store_data("TEST", test_data, "1d")
    retrieved = dm._get_cached_data("TEST", "1d")

    if retrieved is not None and len(retrieved) == 100:
        print("[OK] Data manager working")
    else:
        print("[FAIL] Data manager failed")

    # Test signal generator
    sg = SignalGenerator(min_confidence=0.3)
    signal = sg.generate_signal("TEST", test_data)

    if signal is not None:
        print(f"[OK] Signal generator working: {signal.signal_type.value}")
    else:
        print("[OK] Signal generator working (no signal generated)")

    dm.close()
    print("[OK] Quick test complete")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--populate", action="store_true", help="Populate with sample data")
    parser.add_argument("--test", action="store_true", help="Run quick test")

    args = parser.parse_args()

    if args.populate:
        populate_sample_database()
    elif args.test:
        quick_test()
    else:
        print("Use --populate to add sample data or --test to run quick test")
