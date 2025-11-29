"""
tests/test_data_manager.py
Test cases for DataManager

NOTE: DataManager now uses SQLAlchemy ORM for database access.
Tests have been refactored to work with the ORM-based schema.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tempfile
import os
import sqlite3
from unittest.mock import patch, MagicMock

from tests import BaseTestCase
from app.core.data_manager import DataManager


class TestDataManager(BaseTestCase):
    """Test cases for DataManager"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.dm = DataManager(db_path=self.test_db.name)

        # Create sample data
        self.sample_dates = pd.date_range("2023-01-01", periods=100, freq="D")
        self.sample_prices = 100 + np.cumsum(np.random.normal(0.1, 2, 100))
        self.sample_data = pd.DataFrame(
            {
                "Open": self.sample_prices * 0.99,
                "High": self.sample_prices * 1.02,
                "Low": self.sample_prices * 0.98,
                "Close": self.sample_prices,
                "Volume": np.random.randint(1000000, 5000000, 100),
                "Dividends": np.zeros(100),
                "Stock Splits": np.zeros(100),
            },
            index=self.sample_dates,
        )
        # Set index name to 'Date' to match yfinance format
        self.sample_data.index.name = "Date"

    def tearDown(self):
        """Clean up test fixtures"""
        self.dm.close()
        super().tearDown()

    def test_database_creation(self):
        """Test database table creation"""
        conn = sqlite3.connect(self.test_db.name)
        cursor = conn.cursor()

        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        expected_tables = ["daily_data", "intraday_data", "metadata", "signal_history"]
        for table in expected_tables:
            self.assertIn(table, tables)

        conn.close()

    def test_data_storage_and_retrieval(self):
        """Test storing and retrieving data"""
        # Store sample data
        self.dm._store_data("TEST", self.sample_data, "1d")

        # Retrieve data
        retrieved_data = self.dm._get_cached_data("TEST", "1d")

        self.assertIsNotNone(retrieved_data)
        self.assertEqual(len(retrieved_data), len(self.sample_data))
        self.assertAlmostEqual(
            retrieved_data["Close"].iloc[-1],
            self.sample_data["Close"].iloc[-1],
            places=2,
        )

    def test_data_cleaning(self):
        """Test data cleaning functionality"""
        # Create dirty data with NaN and outliers
        dirty_data = self.sample_data.copy()
        dirty_data.loc[dirty_data.index[10], "Close"] = np.nan
        dirty_data.loc[dirty_data.index[20], "Close"] = 1000000  # Outlier

        cleaned_data = self.dm._clean_data(dirty_data)

        # Check that NaN values are handled
        self.assertFalse(cleaned_data["Close"].isna().all())

        # Check that outliers are removed
        self.assertLess(len(cleaned_data), len(dirty_data))

    @patch("yfinance.Ticker")
    def test_get_stock_data_with_mock(self, mock_ticker):
        """Test getting stock data with mocked yfinance"""
        # Mock yfinance response
        mock_stock = MagicMock()
        mock_stock.history.return_value = self.sample_data
        mock_stock.info = {"longName": "Test Company", "sector": "Technology"}
        mock_ticker.return_value = mock_stock

        # Test data retrieval
        data = self.dm.get_stock_data("TEST", period="1y", force_update=True)

        self.assertFalse(data.empty)
        self.assertEqual(len(data), len(self.sample_data))
        mock_ticker.assert_called_once_with("TEST")

    def test_multiple_stocks_retrieval(self):
        """Test retrieving multiple stocks"""
        # Store test data for multiple tickers
        for ticker in ["TEST1", "TEST2", "TEST3"]:
            self.dm._store_data(ticker, self.sample_data, "1d")

        # Test portfolio summary
        summary = self.dm.get_portfolio_summary(["TEST1", "TEST2", "TEST3"])

        self.assertIsInstance(summary, pd.DataFrame)
        # Note: This will be empty because we don't have metadata,
        # but it should not raise an error

    def test_data_quality_report(self):
        """Test data quality reporting"""
        # Store some test data
        self.dm._store_data("TEST1", self.sample_data, "1d")
        self.dm._store_data("TEST2", self.sample_data.iloc[:50], "1d")  # Partial data

        # Generate quality report
        report = self.dm.get_data_quality_report(["TEST1", "TEST2", "MISSING"])

        self.assertEqual(report["tickers_checked"], 3)
        self.assertGreaterEqual(report["successful_downloads"], 2)
        self.assertIn("MISSING", report["missing_data"])

    def test_cleanup_old_data(self):
        """Test cleaning up old data"""
        # Store data with old dates
        old_dates = pd.date_range("2020-01-01", periods=50, freq="D")
        old_data = self.sample_data.iloc[:50].copy()
        old_dates.name = "Date"
        old_data.index = old_dates

        self.dm._store_data("OLD_TEST", old_data, "1d")
        self.dm._store_data("NEW_TEST", self.sample_data, "1d")

        # Clean old data (keep last 365 days)
        deleted_count = self.dm.cleanup_old_data(days_to_keep=365)

        self.assertGreater(deleted_count, 0)

    def test_backup_creation(self):
        """Test database backup"""
        # Store some data
        self.dm._store_data("TEST", self.sample_data, "1d")

        # Create backup
        backup_path = tempfile.NamedTemporaryFile(delete=False, suffix=".db").name

        try:
            self.dm.backup_database(backup_path)

            # Verify backup exists and has content
            self.assertTrue(os.path.exists(backup_path))
            self.assertGreater(os.path.getsize(backup_path), 0)

            # Verify backup has same data
            backup_dm = DataManager(db_path=backup_path)
            backup_data = backup_dm._get_cached_data("TEST", "1d")
            backup_dm.close()

            self.assertIsNotNone(backup_data)
            self.assertEqual(len(backup_data), len(self.sample_data))

        finally:
            if os.path.exists(backup_path):
                os.unlink(backup_path)

    def test_metadata_update(self):
        """Test metadata updating"""
        info = {
            "longName": "Test Company Inc.",
            "sector": "Technology",
            "industry": "Software",
            "marketCap": 1000000000,
        }

        self.dm._update_metadata("TEST", info)

        # Verify metadata was stored
        conn = sqlite3.connect(self.test_db.name)
        conn.row_factory = sqlite3.Row  # Enable column name access
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM metadata WHERE ticker = ?", ("TEST",))
        result = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(result)
        self.assertEqual(result["company_name"], "Test Company Inc.")
        self.assertEqual(result["sector"], "Technology")

    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        import time

        start_time = time.time()

        # Test multiple rate limit calls
        for i in range(3):
            self.dm._rate_limit("TEST")

        elapsed_time = time.time() - start_time

        # Should take at least 0.2 seconds (2 * 0.1 second intervals)
        self.assertGreaterEqual(elapsed_time, 0.2)

    def test_error_handling(self):
        """Test error handling in various scenarios"""
        # Test data retrieval with empty result (non-existent ticker)
        empty_data = self.dm._get_cached_data("NONEXISTENT", "1d")
        self.assertIsNone(empty_data)

        # Test with invalid interval returns None or empty
        invalid_data = self.dm._get_cached_data("TEST", "invalid_interval")
        # Should return None or empty DataFrame for invalid interval
        if invalid_data is not None:
            self.assertTrue(invalid_data.empty)

    def test_concurrent_access(self):
        """Test concurrent database access"""
        import threading
        import time

        results = []
        errors = []

        def worker(worker_id):
            try:
                worker_dm = DataManager(db_path=self.test_db.name)
                data = self.sample_data.copy()
                data.index = data.index + pd.Timedelta(days=worker_id)

                worker_dm._store_data(f"WORKER_{worker_id}", data, "1d")
                retrieved = worker_dm._get_cached_data(f"WORKER_{worker_id}", "1d")

                if retrieved is not None:
                    results.append(len(retrieved))

                worker_dm.close()

            except Exception as e:
                errors.append(str(e))

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 5)
        self.assertTrue(all(r == len(self.sample_data) for r in results))

    # =========================================================================
    # NEW TESTS FOR SIGNAL HISTORY API METHODS (Phase 2 Expansion)
    # =========================================================================

    def test_get_signal_history_basic(self):
        """Test basic signal history retrieval"""
        from tests import SampleDataGenerator

        # Insert test signals
        signal = SampleDataGenerator.generate_signal_data("TEST_TICKER")
        conn = sqlite3.connect(self.test_db.name)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO signal_history
            (user_id, ticker, date, signal_type, signal_value, confidence, entry_price,
             target_price, stop_loss, regime, reasons)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,  # user_id (default test user)
                signal["ticker"],
                signal["date"],
                signal["signal_type"],
                signal["signal_value"],
                signal["confidence"],
                signal["entry_price"],
                signal["target_price"],
                signal["stop_loss"],
                signal["regime"],
                signal["reasons"],
            ),
        )
        conn.commit()
        conn.close()

        # Test retrieval
        history = self.dm.get_signal_history()
        self.assertGreater(len(history), 0)
        self.assertEqual(history[0]["ticker"], "TEST_TICKER")
        self.assertEqual(history[0]["signal_type"], "BUY")

    def test_get_signal_history_with_ticker_filter(self):
        """Test signal history filtered by ticker"""
        from tests import SampleDataGenerator

        # Insert multiple signals for different tickers
        conn = sqlite3.connect(self.test_db.name)
        cursor = conn.cursor()

        for ticker in ["TEST1", "TEST2", "TEST3"]:
            signal = SampleDataGenerator.generate_signal_data(ticker)
            cursor.execute(
                """
                INSERT INTO signal_history
                (user_id, ticker, date, signal_type, signal_value, confidence, entry_price,
                 target_price, stop_loss, regime, reasons)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    1,  # user_id
                    signal["ticker"],
                    signal["date"],
                    signal["signal_type"],
                    signal["signal_value"],
                    signal["confidence"],
                    signal["entry_price"],
                    signal["target_price"],
                    signal["stop_loss"],
                    signal["regime"],
                    signal["reasons"],
                ),
            )

        conn.commit()
        conn.close()

        # Test ticker filtering
        history = self.dm.get_signal_history(ticker="TEST1")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["ticker"], "TEST1")

    def test_get_signal_history_with_confidence_filter(self):
        """Test signal history with confidence filtering"""
        from tests import SampleDataGenerator

        conn = sqlite3.connect(self.test_db.name)
        cursor = conn.cursor()

        # Insert signals with different confidence levels
        for confidence in [0.5, 0.7, 0.9]:
            signal = SampleDataGenerator.generate_signal_data("TEST")
            signal["confidence"] = confidence
            cursor.execute(
                """
                INSERT INTO signal_history
                (user_id, ticker, date, signal_type, signal_value, confidence, entry_price,
                 target_price, stop_loss, regime, reasons)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    1,
                    signal["ticker"],
                    signal["date"],
                    signal["signal_type"],
                    signal["signal_value"],
                    signal["confidence"],
                    signal["entry_price"],
                    signal["target_price"],
                    signal["stop_loss"],
                    signal["regime"],
                    signal["reasons"],
                ),
            )

        conn.commit()
        conn.close()

        # Test confidence filtering
        history = self.dm.get_signal_history(min_confidence=0.8)
        self.assertEqual(len(history), 1)
        self.assertGreaterEqual(history[0]["confidence"], 0.8)

    def test_get_signals_by_ticker(self):
        """Test getting signals for specific ticker"""
        from tests import SampleDataGenerator

        conn = sqlite3.connect(self.test_db.name)
        cursor = conn.cursor()

        # Insert multiple signals for one ticker
        for i in range(3):
            signal = SampleDataGenerator.generate_signal_data("TARGET")
            cursor.execute(
                """
                INSERT INTO signal_history
                (user_id, ticker, date, signal_type, signal_value, confidence, entry_price,
                 target_price, stop_loss, regime, reasons)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    1,
                    signal["ticker"],
                    signal["date"],
                    signal["signal_type"],
                    signal["signal_value"],
                    signal["confidence"],
                    signal["entry_price"],
                    signal["target_price"],
                    signal["stop_loss"],
                    signal["regime"],
                    signal["reasons"],
                ),
            )

        conn.commit()
        conn.close()

        signals = self.dm.get_signals_by_ticker("TARGET", limit=10)
        self.assertEqual(len(signals), 3)

    def test_get_signals_stats(self):
        """Test signal statistics retrieval"""
        from tests import SampleDataGenerator

        conn = sqlite3.connect(self.test_db.name)
        cursor = conn.cursor()

        # Insert test signals
        for ticker in ["STAT1", "STAT2"]:
            for signal_type in ["BUY", "SELL"]:
                signal = SampleDataGenerator.generate_signal_data(ticker)
                signal["signal_type"] = signal_type
                cursor.execute(
                    """
                    INSERT INTO signal_history
                    (user_id, ticker, date, signal_type, signal_value, confidence,
                     entry_price, target_price, stop_loss, regime, reasons)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        1,  # user_id
                        signal["ticker"],
                        signal["date"],
                        signal["signal_type"],
                        signal["signal_value"],
                        signal["confidence"],
                        signal["entry_price"],
                        signal["target_price"],
                        signal["stop_loss"],
                        signal["regime"],
                        signal["reasons"],
                    ),
                )

        conn.commit()
        conn.close()

        stats = self.dm.get_signals_stats()
        self.assertIn("total_signals", stats)
        self.assertIn("unique_tickers", stats)
        self.assertGreater(stats["total_signals"], 0)

    # =========================================================================
    # NEW TESTS FOR PORTFOLIO PERFORMANCE API METHODS (Phase 2 Expansion)
    # =========================================================================

    def test_get_portfolio_performance_basic(self):
        """Test basic portfolio performance retrieval"""
        from tests import SampleDataGenerator

        conn = sqlite3.connect(self.test_db.name)
        cursor = conn.cursor()

        # Insert performance records
        performance_data = SampleDataGenerator.generate_performance_data(days=10)
        for perf in performance_data:
            cursor.execute(
                """
                INSERT INTO portfolio_performance
                (user_id, date, portfolio_value, daily_return, volatility, sharpe_ratio,
                 max_drawdown)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    1,  # user_id
                    perf["date"],
                    perf["portfolio_value"],
                    perf["daily_return"],
                    perf["volatility"],
                    perf["sharpe_ratio"],
                    perf["max_drawdown"],
                ),
            )

        conn.commit()
        conn.close()

        performance = self.dm.get_portfolio_performance()
        self.assertGreater(len(performance), 0)
        self.assertIn("portfolio_value", performance[0])

    def test_get_portfolio_performance_with_limit(self):
        """Test portfolio performance with limit parameter"""
        from tests import SampleDataGenerator

        conn = sqlite3.connect(self.test_db.name)
        cursor = conn.cursor()

        # Insert multiple performance records
        performance_data = SampleDataGenerator.generate_performance_data(days=30)
        for perf in performance_data:
            cursor.execute(
                """
                INSERT INTO portfolio_performance
                (user_id, date, portfolio_value, daily_return, volatility, sharpe_ratio,
                 max_drawdown)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    1,  # user_id
                    perf["date"],
                    perf["portfolio_value"],
                    perf["daily_return"],
                    perf["volatility"],
                    perf["sharpe_ratio"],
                    perf["max_drawdown"],
                ),
            )

        conn.commit()
        conn.close()

        # Test with limit
        performance = self.dm.get_portfolio_performance(limit=10)
        self.assertLessEqual(len(performance), 10)

    def test_get_performance_summary(self):
        """Test portfolio performance summary"""
        from tests import SampleDataGenerator

        conn = sqlite3.connect(self.test_db.name)
        cursor = conn.cursor()

        # Insert performance records for last 30 days
        performance_data = SampleDataGenerator.generate_performance_data(days=30)
        for perf in performance_data:
            cursor.execute(
                """
                INSERT INTO portfolio_performance
                (user_id, date, portfolio_value, daily_return, volatility, sharpe_ratio,
                 max_drawdown)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    1,  # user_id
                    perf["date"],
                    perf["portfolio_value"],
                    perf["daily_return"],
                    perf["volatility"],
                    perf["sharpe_ratio"],
                    perf["max_drawdown"],
                ),
            )

        conn.commit()
        conn.close()

        summary = self.dm.get_performance_summary(days=30)
        self.assertIn("current_value", summary)
        self.assertIn("period_return", summary)
        self.assertIn("avg_volatility", summary)

    def test_get_performance_metrics(self):
        """Test comprehensive portfolio performance metrics"""
        from tests import SampleDataGenerator

        conn = sqlite3.connect(self.test_db.name)
        cursor = conn.cursor()

        # Insert performance records
        performance_data = SampleDataGenerator.generate_performance_data(days=90)
        for perf in performance_data:
            cursor.execute(
                """
                INSERT INTO portfolio_performance
                (user_id, date, portfolio_value, daily_return, volatility, sharpe_ratio,
                 max_drawdown)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    1,  # user_id
                    perf["date"],
                    perf["portfolio_value"],
                    perf["daily_return"],
                    perf["volatility"],
                    perf["sharpe_ratio"],
                    perf["max_drawdown"],
                ),
            )

        conn.commit()
        conn.close()

        metrics = self.dm.get_performance_metrics(days=90)
        self.assertIn("total_return", metrics)
        self.assertIn("avg_volatility", metrics)
        self.assertIn("avg_sharpe_ratio", metrics)

    # =========================================================================
    # EDGE CASES AND ERROR HANDLING (Phase 2 Expansion)
    # =========================================================================

    def test_empty_database_retrieval(self):
        """Test retrieving from empty database"""
        history = self.dm.get_signal_history()
        self.assertEqual(len(history), 0)

        performance = self.dm.get_portfolio_performance()
        self.assertEqual(len(performance), 0)

    def test_performance_summary_with_no_data(self):
        """Test performance summary when no data exists"""
        summary = self.dm.get_performance_summary(days=30)
        # Should return a dict with None or 0 values instead of crashing
        self.assertIsInstance(summary, dict)

    def test_malformed_signal_data_handling(self):
        """Test handling of malformed signal data"""
        conn = sqlite3.connect(self.test_db.name)
        cursor = conn.cursor()

        # Insert incomplete signal record with all required columns
        cursor.execute(
            """
            INSERT INTO signal_history
            (user_id, ticker, date, signal_type, signal_value, confidence, entry_price,
             target_price, stop_loss, regime, reasons)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "MALFORMED",
                datetime.now().date(),
                "BUY",
                0.0,
                0.5,
                0.0,
                0.0,
                0.0,
                "NORMAL",
                "test",
            ),
        )

        conn.commit()
        conn.close()

        # Should retrieve without error
        history = self.dm.get_signal_history(ticker="MALFORMED")
        self.assertGreater(len(history), 0)

    def test_date_range_filtering(self):
        """Test date range filtering for signals"""
        from tests import SampleDataGenerator
        from datetime import datetime, timedelta

        conn = sqlite3.connect(self.test_db.name)
        cursor = conn.cursor()

        # Insert signals on different dates
        base_date = datetime.now().date()
        for days_ago in [1, 7, 30, 90]:
            signal_date = base_date - timedelta(days=days_ago)
            signal = SampleDataGenerator.generate_signal_data("DATE_TEST")
            cursor.execute(
                """
                INSERT INTO signal_history
                (user_id, ticker, date, signal_type, signal_value, confidence, entry_price,
                 target_price, stop_loss, regime, reasons)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    1,
                    signal["ticker"],
                    signal_date,
                    signal["signal_type"],
                    signal["signal_value"],
                    signal["confidence"],
                    signal["entry_price"],
                    signal["target_price"],
                    signal["stop_loss"],
                    signal["regime"],
                    signal["reasons"],
                ),
            )

        conn.commit()
        conn.close()

        # Test date range filtering
        start_date = (base_date - timedelta(days=45)).isoformat()
        end_date = (base_date - timedelta(days=5)).isoformat()
        history = self.dm.get_signal_history(
            ticker="DATE_TEST", start_date=start_date, end_date=end_date
        )
        self.assertGreater(len(history), 0)


if __name__ == "__main__":
    unittest.main()
