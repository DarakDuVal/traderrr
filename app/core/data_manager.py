"""
app/core/data_manager.py - Core data management system using Yahoo Finance
"""

import yfinance as yf
import pandas as pd
import numpy as np
import sqlite3
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union, Any
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests  # type: ignore
from requests.adapters import HTTPAdapter  # type: ignore
from urllib3.util.retry import Retry


class DataManager:
    """
    Production-grade data manager for Yahoo Finance data
    Handles data retrieval, storage, caching, and error recovery
    """

    def __init__(self, db_path: str = "data/market_data.db", cache_dir: str = "cache"):
        self.db_path = db_path
        self.cache_dir = cache_dir
        self.logger = self._setup_logging()

        # Create directories
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)

        # Initialize database
        # Note: Tables are created by DatabaseConfig.init_database() in main.py
        # This should be called before DataManager is instantiated
        self.conn = sqlite3.connect(db_path, check_same_thread=False)

        # Setup requests session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Rate limiting
        self.last_request_time: Dict[str, float] = {}
        self.min_request_interval = 0.1  # 100ms between requests

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger("DataManager")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _rate_limit(self, ticker: str) -> None:
        """Implement rate limiting"""
        now = time.time()
        if ticker in self.last_request_time:
            time_since_last = now - self.last_request_time[ticker]
            if time_since_last < self.min_request_interval:
                time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time[ticker] = time.time()

    def get_stock_data(
        self,
        ticker: str,
        period: str = "2y",
        interval: str = "1d",
        force_update: bool = False,
    ) -> pd.DataFrame:
        """
        Get stock data with caching and error handling

        Args:
            ticker: Stock symbol
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            force_update: Force fresh data download

        Returns:
            DataFrame with OHLCV data
        """
        try:
            self._rate_limit(ticker)

            # Check cache first
            if not force_update:
                cached_data = self._get_cached_data(ticker, interval)
                if cached_data is not None and not cached_data.empty:
                    # Check if cache is recent enough
                    last_date = cached_data.index[-1]
                    if interval == "1d":
                        cutoff = datetime.now() - timedelta(hours=6)
                    else:
                        cutoff = datetime.now() - timedelta(minutes=30)

                    if last_date.tz_localize(None) > cutoff:  # type: ignore
                        self.logger.info(f"Using cached data for {ticker}")
                        return cached_data

            # Download fresh data
            self.logger.info(f"Downloading {ticker} data: {period}, {interval}")
            stock = yf.Ticker(ticker)
            data = stock.history(period=period, interval=interval)

            if data.empty:
                self.logger.warning(f"No data returned for {ticker}")
                return pd.DataFrame()

            # Clean and validate data
            data = self._clean_data(data)

            # Store in database
            self._store_data(ticker, data, interval)

            # Update metadata
            try:
                info = stock.info
                self._update_metadata(ticker, info)
            except Exception as e:
                self.logger.warning(f"Could not update metadata for {ticker}: {e}")

            self.logger.info(f"Successfully retrieved {len(data)} records for {ticker}")
            return data

        except Exception as e:
            self.logger.error(f"Error retrieving data for {ticker}: {e}")
            # Try to return cached data as fallback
            cached_data = self._get_cached_data(ticker, interval)
            if cached_data is not None and not cached_data.empty:
                self.logger.info(f"Returning cached data for {ticker} due to error")
                return cached_data
            return pd.DataFrame()

    def get_multiple_stocks(
        self, tickers: List[str], period: str = "1y", max_workers: int = 5
    ) -> Dict[str, pd.DataFrame]:
        """
        Get data for multiple stocks concurrently

        Args:
            tickers: List of stock symbols
            period: Data period
            max_workers: Maximum concurrent downloads

        Returns:
            Dictionary mapping ticker to DataFrame
        """
        results = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_ticker = {
                executor.submit(self.get_stock_data, ticker, period): ticker for ticker in tickers
            }

            # Collect results
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    data = future.result()
                    if not data.empty:
                        results[ticker] = data
                    else:
                        self.logger.warning(f"No data for {ticker}")
                except Exception as e:
                    self.logger.error(f"Error downloading {ticker}: {e}")

        self.logger.info(f"Downloaded data for {len(results)}/{len(tickers)} tickers")
        return results

    def _clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate data"""
        if data.empty:
            return data

        # Remove rows with all NaN values
        data = data.dropna(how="all")

        # Forward fill missing values (max 3 consecutive)
        data = data.ffill(limit=3)

        # Remove obvious outliers (price changes > 50% in one day)
        if "Close" in data.columns and len(data) > 1:
            price_change = data["Close"].pct_change().abs()
            outlier_mask = price_change > 0.5
            if outlier_mask.any():
                self.logger.warning(f"Removing {outlier_mask.sum()} outlier records")
                data = data[~outlier_mask]

        # Ensure positive prices and volumes
        price_cols = ["Open", "High", "Low", "Close"]
        for col in price_cols:
            if col in data.columns:
                data = data[data[col] > 0]

        if "Volume" in data.columns:
            data = data[data["Volume"] >= 0]

        return data

    def _store_data(self, ticker: str, data: pd.DataFrame, interval: str) -> None:
        """Store data in database"""
        if data.empty:
            return

        # Prepare data for storage
        data_copy = data.copy()
        data_copy["ticker"] = ticker
        data_copy = data_copy.reset_index()

        # Choose table based on interval
        if interval == "1d":
            table_name = "daily_data"
            data_copy["date"] = data_copy["Date"].dt.date
            columns_map = {
                "ticker": "ticker",
                "date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
                "Dividends": "dividends",
                "Stock Splits": "stock_splits",
            }
        else:
            table_name = "intraday_data"
            data_copy["datetime"] = data_copy["Date"]
            columns_map = {
                "ticker": "ticker",
                "datetime": "datetime",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }

        # Select only existing columns and rename to match database schema
        available_columns = [col for col in columns_map.keys() if col in data_copy.columns]
        data_to_store = data_copy[available_columns].copy()

        # Rename columns to match database schema
        rename_map = {col: columns_map[col] for col in available_columns}
        data_to_store = data_to_store.rename(columns=rename_map)

        # Store with conflict resolution
        try:
            data_to_store.to_sql(table_name, self.conn, if_exists="append", index=False)
            self.conn.commit()
        except Exception as e:
            # Handle UNIQUE constraint and other integrity errors gracefully
            if "UNIQUE constraint failed" in str(e):
                # Data already exists in database, which is expected behavior
                # SQLite automatically rolls back the failed insert, so we just continue
                self.logger.debug(f"Data for {ticker} on this date already exists")
            else:
                # Re-raise other errors
                raise

    def _get_cached_data(self, ticker: str, interval: str) -> Optional[pd.DataFrame]:
        """Retrieve cached data from database"""
        try:
            if interval == "1d":
                query = """
                    SELECT date as Date, open, high, low, close, volume, dividends, stock_splits
                    FROM daily_data 
                    WHERE ticker = ? 
                    ORDER BY date
                """
            else:
                query = """
                    SELECT datetime as Date, open, high, low, close, volume
                    FROM intraday_data 
                    WHERE ticker = ? 
                    ORDER BY datetime
                """

            df = pd.read_sql_query(query, self.conn, params=[ticker], parse_dates=["Date"])

            if not df.empty:
                df.set_index("Date", inplace=True)
                # Capitalize column names to match yfinance format
                df.columns = [col.capitalize() for col in df.columns]
                return df

        except Exception as e:
            self.logger.error(f"Error retrieving cached data for {ticker}: {e}")

        return None

    def _update_metadata(self, ticker: str, info: Dict[str, Any]) -> None:
        """Update stock metadata"""
        try:
            metadata = {
                "ticker": ticker,
                "company_name": info.get("longName", ""),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "market_cap": info.get("marketCap", 0),
                "last_updated": datetime.now(),
            }

            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO metadata 
                (ticker, company_name, sector, industry, market_cap, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    metadata["ticker"],
                    metadata["company_name"],
                    metadata["sector"],
                    metadata["industry"],
                    metadata["market_cap"],
                    metadata["last_updated"],
                ),
            )
            self.conn.commit()

        except Exception as e:
            self.logger.error(f"Error updating metadata for {ticker}: {e}")

    def get_portfolio_summary(self, tickers: List[str]) -> pd.DataFrame:
        """Get summary statistics for portfolio tickers"""
        try:
            placeholders = ",".join(["?" for _ in tickers])
            query = f"""
                SELECT 
                    m.ticker,
                    m.company_name,
                    m.sector,
                    m.market_cap,
                    d.close as last_price,
                    d.volume as last_volume,
                    d.date as last_date
                FROM metadata m
                LEFT JOIN daily_data d ON m.ticker = d.ticker
                WHERE m.ticker IN ({placeholders})
                AND d.date = (
                    SELECT MAX(date) 
                    FROM daily_data 
                    WHERE ticker = m.ticker
                )
                ORDER BY m.market_cap DESC
            """

            df = pd.read_sql_query(query, self.conn, params=tickers)  # type: ignore
            return df

        except Exception as e:
            self.logger.error(f"Error getting portfolio summary: {e}")
            return pd.DataFrame()

    def cleanup_old_data(self, days_to_keep: int = 730) -> int:
        """Clean up old data to manage database size"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            cursor = self.conn.cursor()
            total_deleted = 0

            # Clean daily data
            cursor.execute("DELETE FROM daily_data WHERE date < ?", (cutoff_date.date(),))
            total_deleted += cursor.rowcount

            # Clean intraday data (keep less)
            intraday_cutoff = datetime.now() - timedelta(days=30)
            cursor.execute("DELETE FROM intraday_data WHERE datetime < ?", (intraday_cutoff,))
            total_deleted += cursor.rowcount

            # Clean old signals
            signal_cutoff = datetime.now() - timedelta(days=90)
            cursor.execute("DELETE FROM signal_history WHERE created_at < ?", (signal_cutoff,))
            total_deleted += cursor.rowcount

            self.conn.commit()
            self.logger.info(
                f"Cleaned data older than {days_to_keep} days. Deleted {total_deleted} records"
            )

            return total_deleted

        except Exception as e:
            self.logger.error(f"Error cleaning old data: {e}")
            return 0

    def backup_database(self, backup_path: str) -> None:
        """Create database backup"""
        try:
            backup_conn = sqlite3.connect(backup_path)
            self.conn.backup(backup_conn)
            backup_conn.close()
            self.logger.info(f"Database backed up to {backup_path}")
        except Exception as e:
            self.logger.error(f"Error creating backup: {e}")

    def get_data_quality_report(self, tickers: List[str]) -> Dict[str, Any]:
        """Generate data quality report"""
        report: Dict[str, Any] = {
            "tickers_checked": len(tickers),
            "successful_downloads": 0,
            "missing_data": [],
            "stale_data": [],
            "data_gaps": [],
            "timestamp": datetime.now(),
        }

        for ticker in tickers:
            try:
                data = self._get_cached_data(ticker, "1d")
                if data is None or data.empty:
                    report["missing_data"].append(ticker)
                else:
                    report["successful_downloads"] += 1

                    # Check for stale data
                    last_date = data.index[-1]
                    if (datetime.now() - last_date.tz_localize(None)).days > 7:  # type: ignore
                        report["stale_data"].append(ticker)

                    # Check for data gaps
                    date_diff = data.index.to_series().diff()
                    gaps = date_diff[date_diff > pd.Timedelta(days=7)]
                    if not gaps.empty:
                        report["data_gaps"].append({"ticker": ticker, "gaps": len(gaps)})

            except Exception as e:
                self.logger.error(f"Error checking data quality for {ticker}: {e}")
                report["missing_data"].append(ticker)

        return report

    def get_signal_history(
        self,
        ticker: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        signal_type: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Retrieve signal history from database with optional filters.

        Args:
            ticker: Filter by ticker (e.g., 'AAPL')
            start_date: Filter signals from this date (format: YYYY-MM-DD)
            end_date: Filter signals until this date (format: YYYY-MM-DD)
            signal_type: Filter by signal type (BUY, SELL, HOLD)
            min_confidence: Minimum confidence threshold (0.0 - 1.0)
            limit: Maximum number of records to return

        Returns:
            List of signal dictionaries ordered by date descending
        """
        try:
            query = "SELECT * FROM signal_history WHERE 1=1"
            params = []

            if ticker:
                query += " AND ticker = ?"
                params.append(ticker.upper().strip())

            if start_date:
                query += " AND date >= ?"
                params.append(start_date)

            if end_date:
                query += " AND date <= ?"
                params.append(end_date)

            if signal_type:
                query += " AND signal_type = ?"
                params.append(signal_type)

            if min_confidence > 0:
                query += " AND confidence >= ?"
                params.append(str(min_confidence))

            # Order by date descending, then by id descending for latest signals first
            query += " ORDER BY date DESC, id DESC LIMIT ?"
            params.append(str(limit))

            cursor = self.conn.cursor()
            cursor.execute(query, params)

            columns = [
                "id",
                "ticker",
                "date",
                "signal_type",
                "signal_value",
                "confidence",
                "entry_price",
                "target_price",
                "stop_loss",
                "regime",
                "reasons",
                "created_at",
            ]

            signals = []
            for row in cursor.fetchall():
                signal_dict = dict(zip(columns, row))
                # Convert None/NULL strings to None
                for key in signal_dict:
                    if signal_dict[key] == "NULL" or signal_dict[key] is None:
                        signal_dict[key] = None
                signals.append(signal_dict)

            return signals

        except Exception as e:
            self.logger.error(f"Error retrieving signal history: {e}")
            return []

    def get_signals_by_ticker(self, ticker: str, limit: int = 50) -> List[Dict]:
        """Get signal history for a specific ticker"""
        return self.get_signal_history(ticker=ticker, limit=limit)

    def get_signals_by_date_range(
        self, start_date: str, end_date: str, limit: int = 100
    ) -> List[Dict]:
        """Get signals within a date range"""
        return self.get_signal_history(start_date=start_date, end_date=end_date, limit=limit)

    def get_signals_stats(self, ticker: Optional[str] = None) -> Dict:
        """Get statistics about signals"""
        try:
            query = """
                SELECT
                    COUNT(*) as total_signals,
                    COUNT(DISTINCT ticker) as unique_tickers,
                    COUNT(DISTINCT CASE WHEN signal_type = 'BUY' THEN 1 END) as buy_signals,
                    COUNT(DISTINCT CASE WHEN signal_type = 'SELL' THEN 1 END) as sell_signals,
                    COUNT(DISTINCT CASE WHEN signal_type = 'HOLD' THEN 1 END) as hold_signals,
                    AVG(confidence) as avg_confidence,
                    MIN(date) as earliest_signal,
                    MAX(date) as latest_signal
                FROM signal_history
            """
            params = []

            if ticker:
                query += " WHERE ticker = ?"
                params.append(ticker.upper().strip())

            cursor = self.conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()

            if row:
                columns = [
                    "total_signals",
                    "unique_tickers",
                    "buy_signals",
                    "sell_signals",
                    "hold_signals",
                    "avg_confidence",
                    "earliest_signal",
                    "latest_signal",
                ]
                return dict(zip(columns, row))
            return {}

        except Exception as e:
            self.logger.error(f"Error getting signal stats: {e}")
            return {}

    def get_portfolio_performance(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Retrieve portfolio performance history from database.

        Args:
            start_date: Filter performance from this date (format: YYYY-MM-DD)
            end_date: Filter performance until this date (format: YYYY-MM-DD)
            limit: Maximum number of records to return (default: 100, max: 1000)

        Returns:
            List of performance dictionaries ordered by date descending
        """
        try:
            query = "SELECT * FROM portfolio_performance WHERE 1=1"
            params = []

            if start_date:
                query += " AND date >= ?"
                params.append(start_date)

            if end_date:
                query += " AND date <= ?"
                params.append(end_date)

            # Order by date descending for latest first
            query += " ORDER BY date DESC LIMIT ?"
            params.append(str(min(limit, 1000)))

            cursor = self.conn.cursor()
            cursor.execute(query, params)

            columns = [
                "id",
                "date",
                "portfolio_value",
                "daily_return",
                "volatility",
                "sharpe_ratio",
                "max_drawdown",
                "created_at",
            ]

            performance = []
            for row in cursor.fetchall():
                perf_dict = dict(zip(columns, row))
                performance.append(perf_dict)

            return performance

        except Exception as e:
            self.logger.error(f"Error retrieving portfolio performance: {e}")
            return []

    def get_performance_summary(self, days: int = 30) -> Dict:
        """
        Get portfolio performance summary for recent period.

        Args:
            days: Number of days to look back (default: 30)

        Returns:
            Summary statistics including current value, returns, volatility, etc.
        """
        try:
            from datetime import datetime, timedelta

            cutoff_date = (datetime.now() - timedelta(days=days)).date()

            query = """
                SELECT
                    COUNT(*) as total_records,
                    MAX(date) as latest_date,
                    MIN(date) as earliest_date,
                    MAX(portfolio_value) as max_value,
                    MIN(portfolio_value) as min_value,
                    (SELECT portfolio_value FROM portfolio_performance
                     ORDER BY date DESC LIMIT 1) as current_value,
                    (SELECT portfolio_value FROM portfolio_performance
                     WHERE date = (SELECT MIN(date) FROM portfolio_performance
                                   WHERE date >= ?)
                     LIMIT 1) as opening_value,
                    AVG(daily_return) as avg_daily_return,
                    AVG(volatility) as avg_volatility,
                    MAX(volatility) as max_volatility,
                    MIN(volatility) as min_volatility,
                    AVG(sharpe_ratio) as avg_sharpe_ratio,
                    MIN(max_drawdown) as worst_drawdown,
                    MAX(sharpe_ratio) as best_sharpe_ratio
                FROM portfolio_performance
                WHERE date >= ?
            """
            params = [cutoff_date, cutoff_date]

            cursor = self.conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()

            if row:
                columns = [
                    "total_records",
                    "latest_date",
                    "earliest_date",
                    "max_value",
                    "min_value",
                    "current_value",
                    "opening_value",
                    "avg_daily_return",
                    "avg_volatility",
                    "max_volatility",
                    "min_volatility",
                    "avg_sharpe_ratio",
                    "worst_drawdown",
                    "best_sharpe_ratio",
                ]
                summary = dict(zip(columns, row))

                # Calculate period return if we have opening and current values
                if (
                    summary["opening_value"]
                    and summary["current_value"]
                    and summary["opening_value"] != 0
                ):
                    summary["period_return"] = (
                        summary["current_value"] - summary["opening_value"]
                    ) / summary["opening_value"]
                else:
                    summary["period_return"] = None

                return summary
            return {}

        except Exception as e:
            self.logger.error(f"Error getting performance summary: {e}")
            return {}

    def get_daily_performance(self, limit: int = 30) -> List[Dict]:
        """Get recent daily performance records"""
        return self.get_portfolio_performance(limit=limit)

    def get_performance_by_date_range(
        self, start_date: str, end_date: str, limit: int = 1000
    ) -> List[Dict]:
        """Get performance data for a specific date range"""
        return self.get_portfolio_performance(start_date=start_date, end_date=end_date, limit=limit)

    def get_performance_metrics(self, days: int = 90) -> Dict:
        """
        Get aggregated performance metrics for analysis.

        Args:
            days: Number of days to analyze (default: 90)

        Returns:
            Aggregated metrics for performance analysis
        """
        try:
            from datetime import datetime, timedelta

            cutoff_date = (datetime.now() - timedelta(days=days)).date()

            # Get all performance records for the period
            query = """
                SELECT
                    date,
                    portfolio_value,
                    daily_return,
                    volatility,
                    sharpe_ratio,
                    max_drawdown
                FROM portfolio_performance
                WHERE date >= ?
                ORDER BY date ASC
            """

            cursor = self.conn.cursor()
            cursor.execute(query, (cutoff_date,))
            rows = cursor.fetchall()

            if not rows:
                return {}

            # Calculate metrics from data
            dates = [row[0] for row in rows]
            values = [row[1] for row in rows]
            daily_returns = [row[2] for row in rows]
            volatilities = [row[3] for row in rows]
            sharpe_ratios = [row[4] for row in rows]
            max_drawdowns = [row[5] for row in rows]

            # Filter out None values for calculations
            daily_returns_filtered = [r for r in daily_returns if r is not None]
            volatilities_filtered = [v for v in volatilities if v is not None]
            sharpe_ratios_filtered = [s for s in sharpe_ratios if s is not None]
            max_drawdowns_filtered = [d for d in max_drawdowns if d is not None]

            metrics = {
                "period_days": days,
                "records_count": len(rows),
                "start_date": dates[0] if dates else None,
                "end_date": dates[-1] if dates else None,
                "start_value": values[0] if values else None,
                "end_value": values[-1] if values else None,
                "min_value": min(values) if values else None,
                "max_value": max(values) if values else None,
                "avg_volatility": (
                    sum(volatilities_filtered) / len(volatilities_filtered)
                    if volatilities_filtered
                    else None
                ),
                "max_volatility": (max(volatilities_filtered) if volatilities_filtered else None),
                "min_volatility": (min(volatilities_filtered) if volatilities_filtered else None),
                "avg_sharpe_ratio": (
                    sum(sharpe_ratios_filtered) / len(sharpe_ratios_filtered)
                    if sharpe_ratios_filtered
                    else None
                ),
                "worst_sharpe_ratio": (
                    min(sharpe_ratios_filtered) if sharpe_ratios_filtered else None
                ),
                "best_sharpe_ratio": (
                    max(sharpe_ratios_filtered) if sharpe_ratios_filtered else None
                ),
                "avg_daily_return": (
                    sum(daily_returns_filtered) / len(daily_returns_filtered)
                    if daily_returns_filtered
                    else None
                ),
                "worst_drawdown": (min(max_drawdowns_filtered) if max_drawdowns_filtered else None),
            }

            # Calculate total return if we have start and end values
            if metrics["start_value"] and metrics["end_value"] and metrics["start_value"] != 0:
                metrics["total_return"] = (metrics["end_value"] - metrics["start_value"]) / metrics[
                    "start_value"
                ]
            else:
                metrics["total_return"] = None

            return metrics

        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            return {}

    def close(self) -> None:
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.logger.info("Database connection closed")
