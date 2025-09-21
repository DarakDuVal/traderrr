"""
data_manager.py - Core data management system using Yahoo Finance
"""

import yfinance as yf
import pandas as pd
import numpy as np
import sqlite3
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class DataManager:
    """
    Production-grade data manager for Yahoo Finance data
    Handles data retrieval, storage, caching, and error recovery
    """
    
    def __init__(self, db_path: str = "market_data.db", cache_dir: str = "cache"):
        self.db_path = db_path
        self.cache_dir = cache_dir
        self.logger = self._setup_logging()
        
        # Create directories
        os.makedirs(cache_dir, exist_ok=True)
        
        # Initialize database
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()
        
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
        self.last_request_time = {}
        self.min_request_interval = 0.1  # 100ms between requests
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('DataManager')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def _create_tables(self):
        """Create database tables"""
        cursor = self.conn.cursor()
        
        # Daily data table
        cursor.execute('''
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
        ''')
        
        # Intraday data table
        cursor.execute('''
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
        ''')
        
        # Metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metadata (
                ticker TEXT PRIMARY KEY,
                company_name TEXT,
                sector TEXT,
                industry TEXT,
                market_cap REAL,
                last_updated TIMESTAMP
            )
        ''')
        
        # Signal history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signal_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT,
                date DATE,
                signal_type TEXT,
                signal_value REAL,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def _rate_limit(self, ticker: str):
        """Implement rate limiting"""
        now = time.time()
        if ticker in self.last_request_time:
            time_since_last = now - self.last_request_time[ticker]
            if time_since_last < self.min_request_interval:
                time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time[ticker] = time.time()
    
    def get_stock_data(self, 
                      ticker: str, 
                      period: str = "2y", 
                      interval: str = "1d",
                      force_update: bool = False) -> pd.DataFrame:
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
                    
                    if last_date.tz_localize(None) > cutoff:
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
    
    def get_multiple_stocks(self, 
                           tickers: List[str], 
                           period: str = "1y",
                           max_workers: int = 5) -> Dict[str, pd.DataFrame]:
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
                executor.submit(self.get_stock_data, ticker, period): ticker 
                for ticker in tickers
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
        data = data.dropna(how='all')
        
        # Forward fill missing values (max 3 consecutive)
        data = data.fillna(method='ffill', limit=3)
        
        # Remove obvious outliers (price changes > 50% in one day)
        if 'Close' in data.columns and len(data) > 1:
            price_change = data['Close'].pct_change().abs()
            outlier_mask = price_change > 0.5
            if outlier_mask.any():
                self.logger.warning(f"Removing {outlier_mask.sum()} outlier records")
                data = data[~outlier_mask]
        
        # Ensure positive prices and volumes
        price_cols = ['Open', 'High', 'Low', 'Close']
        for col in price_cols:
            if col in data.columns:
                data = data[data[col] > 0]
        
        if 'Volume' in data.columns:
            data = data[data['Volume'] >= 0]
        
        return data
    
    def _store_data(self, ticker: str, data: pd.DataFrame, interval: str):
        """Store data in database"""
        if data.empty:
            return
        
        # Prepare data for storage
        data_copy = data.copy()
        data_copy['ticker'] = ticker
        data_copy = data_copy.reset_index()
        
        # Choose table based on interval
        if interval == "1d":
            table_name = "daily_data"
            data_copy['date'] = data_copy['Date'].dt.date
            columns = ['ticker', 'date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Dividends', 'Stock Splits']
        else:
            table_name = "intraday_data"
            data_copy['datetime'] = data_copy['Date']
            columns = ['ticker', 'datetime', 'Open', 'High', 'Low', 'Close', 'Volume']
        
        # Select only existing columns
        available_columns = [col for col in columns if col in data_copy.columns]
        data_to_store = data_copy[available_columns]
        
        # Store with conflict resolution
        data_to_store.to_sql(table_name, self.conn, if_exists='append', index=False)
        self.conn.commit()
    
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
            
            df = pd.read_sql_query(query, self.conn, params=[ticker], parse_dates=['Date'])
            
            if not df.empty:
                df.set_index('Date', inplace=True)
                # Capitalize column names to match yfinance format
                df.columns = [col.capitalize() for col in df.columns]
                return df
            
        except Exception as e:
            self.logger.error(f"Error retrieving cached data for {ticker}: {e}")
        
        return None
    
    def _update_metadata(self, ticker: str, info: dict):
        """Update stock metadata"""
        try:
            metadata = {
                'ticker': ticker,
                'company_name': info.get('longName', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap': info.get('marketCap', 0),
                'last_updated': datetime.now()
            }
            
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO metadata 
                (ticker, company_name, sector, industry, market_cap, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                metadata['ticker'],
                metadata['company_name'],
                metadata['sector'],
                metadata['industry'],
                metadata['market_cap'],
                metadata['last_updated']
            ))
            self.conn.commit()
            
        except Exception as e:
            self.logger.error(f"Error updating metadata for {ticker}: {e}")
    
    def get_portfolio_summary(self, tickers: List[str]) -> pd.DataFrame:
        """Get summary statistics for portfolio tickers"""
        try:
            placeholders = ','.join(['?' for _ in tickers])
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
            
            df = pd.read_sql_query(query, self.conn, params=tickers)
            return df
            
        except Exception as e:
            self.logger.error(f"Error getting portfolio summary: {e}")
            return pd.DataFrame()
    
    def cleanup_old_data(self, days_to_keep: int = 730):
        """Clean up old data to manage database size"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            cursor = self.conn.cursor()
            
            # Clean daily data
            cursor.execute(
                "DELETE FROM daily_data WHERE date < ?",
                (cutoff_date.date(),)
            )
            
            # Clean intraday data (keep less)
            intraday_cutoff = datetime.now() - timedelta(days=30)
            cursor.execute(
                "DELETE FROM intraday_data WHERE datetime < ?",
                (intraday_cutoff,)
            )
            
            # Clean old signals
            signal_cutoff = datetime.now() - timedelta(days=90)
            cursor.execute(
                "DELETE FROM signal_history WHERE created_at < ?",
                (signal_cutoff,)
            )
            
            self.conn.commit()
            self.logger.info(f"Cleaned data older than {days_to_keep} days")
            
        except Exception as e:
            self.logger.error(f"Error cleaning old data: {e}")
    
    def backup_database(self, backup_path: str):
        """Create database backup"""
        try:
            backup_conn = sqlite3.connect(backup_path)
            self.conn.backup(backup_conn)
            backup_conn.close()
            self.logger.info(f"Database backed up to {backup_path}")
        except Exception as e:
            self.logger.error(f"Error creating backup: {e}")
    
    def get_data_quality_report(self, tickers: List[str]) -> Dict:
        """Generate data quality report"""
        report = {
            'tickers_checked': len(tickers),
            'successful_downloads': 0,
            'missing_data': [],
            'stale_data': [],
            'data_gaps': [],
            'timestamp': datetime.now()
        }
        
        for ticker in tickers:
            try:
                data = self._get_cached_data(ticker, "1d")
                if data is None or data.empty:
                    report['missing_data'].append(ticker)
                else:
                    report['successful_downloads'] += 1
                    
                    # Check for stale data
                    last_date = data.index[-1]
                    if (datetime.now() - last_date.tz_localize(None)).days > 7:
                        report['stale_data'].append(ticker)
                    
                    # Check for data gaps
                    date_diff = data.index.to_series().diff()
                    gaps = date_diff[date_diff > pd.Timedelta(days=7)]
                    if not gaps.empty:
                        report['data_gaps'].append({
                            'ticker': ticker,
                            'gaps': len(gaps)
                        })
                        
            except Exception as e:
                self.logger.error(f"Error checking data quality for {ticker}: {e}")
                report['missing_data'].append(ticker)
        
        return report
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.logger.info("Database connection closed")


# Example usage and testing
if __name__ == "__main__":
    # Initialize data manager
    dm = DataManager()
    
    # Your portfolio tickers
    portfolio_tickers = [
        'AAPL', 'META', 'MSFT', 'NVDA', 'GOOGL',  # Tech
        'JPM', 'BAC',  # Finance
        'PG', 'JNJ', 'KO',  # Consumer
        'VTI', 'SPY',  # ETFs
        'SIEGY', 'VWAGY', 'SYIEY'  # International
    ]
    
    # Download data for all tickers
    print("Downloading portfolio data...")
    portfolio_data = dm.get_multiple_stocks(portfolio_tickers, period="1y")
    
    # Generate summary
    summary = dm.get_portfolio_summary(portfolio_tickers)
    print("\nPortfolio Summary:")
    print(summary)
    
    # Data quality report
    quality_report = dm.get_data_quality_report(portfolio_tickers)
    print(f"\nData Quality Report:")
    print(f"Successful downloads: {quality_report['successful_downloads']}")
    print(f"Missing data: {quality_report['missing_data']}")
    print(f"Stale data: {quality_report['stale_data']}")
    
    # Cleanup
    dm.close()
