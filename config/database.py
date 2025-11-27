"""
config/database.py - Database configuration and utilities
"""

import sqlite3
import logging
import os
import time
from typing import Optional, Union, cast


class DatabaseConfig:
    """Database configuration and utilities"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)

        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    def init_database(self) -> bool:
        """Initialize database with required tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Daily data table
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

            # Intraday data table
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

            # Metadata table
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

            # Signal history table
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

            # Portfolio performance table
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

            # System events table
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

            # Portfolio positions table
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

            # Create indexes for performance
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

            conn.commit()
            conn.close()

            self.logger.info("Database initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            return False

    def check_connection(self) -> bool:
        """Check database connectivity"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("SELECT 1")
            conn.close()
            return True
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            return False

    def get_database_info(self) -> dict:
        """Get database information and statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            info: dict = {
                "path": self.db_path,
                "size_mb": (
                    os.path.getsize(self.db_path) / (1024 * 1024)
                    if os.path.exists(self.db_path)
                    else 0
                ),
                "tables": {},
            }

            # Get table information
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()

            for (table_name,) in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                tables_dict = cast(dict, info["tables"])
                tables_dict[table_name] = count

            # Get data range for daily_data
            try:
                cursor.execute("SELECT MIN(date), MAX(date) FROM daily_data")
                min_date, max_date = cursor.fetchone()
                data_range: Union[dict, None] = {"start": min_date, "end": max_date}
                info["data_range"] = data_range
            except:
                data_range_none: Union[dict, None] = None
                info["data_range"] = data_range_none

            conn.close()
            return info

        except Exception as e:
            self.logger.error(f"Error getting database info: {e}")
            return {"error": str(e)}

    def vacuum_database(self) -> bool:
        """Optimize database by running VACUUM"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("VACUUM")
            conn.close()
            self.logger.info("Database vacuumed successfully")
            return True
        except Exception as e:
            self.logger.error(f"Database vacuum failed: {e}")
            return False

    def backup_database(self, backup_path: str) -> bool:
        """Create database backup"""
        try:
            # Ensure backup directory exists
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)

            # Copy database file
            import shutil

            shutil.copy2(self.db_path, backup_path)

            self.logger.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Database backup failed: {e}")
            return False

    def restore_database(self, backup_path: str) -> bool:
        """Restore database from backup"""
        try:
            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"Backup file not found: {backup_path}")

            # Create backup of current database
            current_backup = f"{self.db_path}.backup_{int(time.time())}"
            self.backup_database(current_backup)

            # Restore from backup
            import shutil

            shutil.copy2(backup_path, self.db_path)

            self.logger.info(f"Database restored from {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Database restore failed: {e}")
            return False

    def execute_query(self, query: str, params: Optional[tuple] = None) -> list:
        """Execute a query and return results"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            results = cursor.fetchall()
            conn.commit()
            conn.close()

            return results
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}")
            return []

    def log_system_event(
        self,
        event_type: str,
        description: str,
        details: Optional[str] = None,
        severity: str = "INFO",
    ) -> None:
        """Log system event to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO system_events (event_type, description, details, severity)
                VALUES (?, ?, ?, ?)
            """,
                (event_type, description, details, severity),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.error(f"Failed to log system event: {e}")

    def get_recent_events(self, limit: int = 50) -> list:
        """Get recent system events"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT event_type, description, details, severity, created_at
                FROM system_events
                ORDER BY created_at DESC
                LIMIT ?
            """,
                (limit,),
            )

            events = cursor.fetchall()
            conn.close()

            return [
                {
                    "event_type": event[0],
                    "description": event[1],
                    "details": event[2],
                    "severity": event[3],
                    "created_at": event[4],
                }
                for event in events
            ]

        except Exception as e:
            self.logger.error(f"Failed to get recent events: {e}")
            return []

    def cleanup_old_data(self, days_to_keep: int = 730) -> dict:
        """Clean up old data"""
        try:
            from datetime import datetime, timedelta

            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cleanup_stats = {}

            # Clean daily data
            cursor.execute("DELETE FROM daily_data WHERE date < ?", (cutoff_date.date(),))
            cleanup_stats["daily_data"] = cursor.rowcount

            # Clean intraday data (keep less)
            intraday_cutoff = datetime.now() - timedelta(days=30)
            cursor.execute("DELETE FROM intraday_data WHERE datetime < ?", (intraday_cutoff,))
            cleanup_stats["intraday_data"] = cursor.rowcount

            # Clean old signals
            signal_cutoff = datetime.now() - timedelta(days=90)
            cursor.execute("DELETE FROM signal_history WHERE created_at < ?", (signal_cutoff,))
            cleanup_stats["signal_history"] = cursor.rowcount

            # Clean old system events
            event_cutoff = datetime.now() - timedelta(days=30)
            cursor.execute("DELETE FROM system_events WHERE created_at < ?", (event_cutoff,))
            cleanup_stats["system_events"] = cursor.rowcount

            conn.commit()
            conn.close()

            total_deleted = sum(cleanup_stats.values())
            self.logger.info(f"Cleaned up {total_deleted} old records")

            return cleanup_stats

        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return {"error": str(e)}
