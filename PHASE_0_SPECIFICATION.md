# Phase 0: Database Abstraction Layer Implementation Specification

## Executive Summary

Phase 0 transforms the database layer from raw SQLite to a production-grade abstraction layer using **SQLAlchemy 2.0 ORM** and **Alembic** migrations. This provides:

- Type-safe database models
- Connection pooling and management
- Support for multiple database engines (SQLite → PostgreSQL → MySQL)
- Automatic schema versioning via migrations
- Foundation for Phase 1 (User/Auth) and Phase 2 (Data Isolation)

**Duration**: 1-2 weeks
**Complexity**: Medium
**Dependencies**: None (can be done independently)

---

## Part 1: Architecture Overview

### Current State
```
Raw SQL Queries → sqlite3 Module → SQLite File
(No pooling, no type safety, database-specific)
```

### Target State
```
SQLAlchemy ORM → SQLAlchemy Dialects → [SQLite | PostgreSQL | MySQL]
(Pooling, type-safe, database-agnostic)
```

### Key Components

#### 1.1 SQLAlchemy Core
- Provides database abstraction layer
- Supports multiple database dialects
- Handles connection pooling
- Type-safe SQL generation

#### 1.2 SQLAlchemy ORM
- Declarative models (classes map to tables)
- Relationships and foreign keys
- Session management
- Query API

#### 1.3 Alembic
- Database migration framework
- Version control for schema
- Rollback support
- Auto-generation of migrations

#### 1.4 Database Drivers
- **SQLite**: `sqlite3` (built-in)
- **PostgreSQL**: `psycopg2` (async: `asyncpg`)
- **MySQL/MariaDB**: `pymysql` or `mysql-connector-python`

---

## Part 2: File Structure

### New Directory Layout
```
traderrr/
├── app/
│   ├── models/                          # NEW: SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── base.py                      # Base model class
│   │   ├── market_data.py               # DailyData, IntradayData, Metadata
│   │   ├── trading.py                   # SignalHistory, PortfolioPerformance
│   │   ├── portfolio.py                 # PortfolioPosition
│   │   └── system.py                    # SystemEvent
│   ├── db.py                            # NEW: Database initialization and session
│   └── (existing files unchanged)
│
├── migrations/                          # NEW: Alembic database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/                        # Migration files
│       ├── 001_initial_schema.py
│       └── (future migrations)
│
├── config/
│   ├── database.py                      # KEEP for now (will be deprecated)
│   ├── settings.py                      # MODIFIED: Add database URL config
│   └── (existing files)
│
├── alembic.ini                          # NEW: Alembic configuration
├── requirements.txt                     # MODIFIED: Add SQLAlchemy, Alembic, drivers
└── (existing files)
```

---

## Part 3: Dependencies to Install

### requirements.txt Additions
```
# Database ORM and Migrations
SQLAlchemy>=2.0.0,<3.0.0
Alembic>=1.12.0

# Database Drivers
psycopg2-binary>=2.9.0          # PostgreSQL (synchronous)
PyMySQL>=1.1.0                  # MySQL/MariaDB (synchronous)

# Optional: for async support (future)
asyncpg>=0.27.0                 # PostgreSQL (async)
aiomysql>=0.2.0                 # MySQL/MariaDB (async)

# Connection pooling utilities
SQLAlchemy-Utils>=0.41.0        # Utility functions
```

### Installation Command
```bash
pip install SQLAlchemy>=2.0.0 Alembic>=1.12.0 psycopg2-binary>=2.9.0 PyMySQL>=1.1.0
```

---

## Part 4: SQLAlchemy Models

### 4.1 Base Model Class
**File**: `app/models/base.py`

```python
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""
    pass

class TimestampMixin:
    """Mixin for automatic timestamp tracking"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
```

### 4.2 Market Data Models
**File**: `app/models/market_data.py`

```python
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class DailyData(Base, TimestampMixin):
    """OHLCV daily market data"""
    __tablename__ = "daily_data"
    __table_args__ = (
        Index("idx_daily_data_ticker_date", "ticker", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False)
    date: Mapped[date] = mapped_column(nullable=False)
    open: Mapped[Decimal] = mapped_column(nullable=False)
    high: Mapped[Decimal] = mapped_column(nullable=False)
    low: Mapped[Decimal] = mapped_column(nullable=False)
    close: Mapped[Decimal] = mapped_column(nullable=False)
    volume: Mapped[int] = mapped_column(nullable=False)
    dividends: Mapped[Decimal | None] = mapped_column(default=None)
    stock_splits: Mapped[Decimal | None] = mapped_column(default=None)

class IntradayData(Base, TimestampMixin):
    """Intraday market data"""
    __tablename__ = "intraday_data"
    __table_args__ = (
        Index("idx_intraday_data_ticker_datetime", "ticker", "datetime"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False)
    datetime: Mapped[datetime] = mapped_column(nullable=False)
    open: Mapped[Decimal] = mapped_column(nullable=False)
    high: Mapped[Decimal] = mapped_column(nullable=False)
    low: Mapped[Decimal] = mapped_column(nullable=False)
    close: Mapped[Decimal] = mapped_column(nullable=False)
    volume: Mapped[int] = mapped_column(nullable=False)

class Metadata(Base, TimestampMixin):
    """Stock metadata information"""
    __tablename__ = "metadata"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    company_name: Mapped[str | None] = mapped_column(default=None)
    sector: Mapped[str | None] = mapped_column(default=None)
    industry: Mapped[str | None] = mapped_column(default=None)
    market_cap: Mapped[Decimal | None] = mapped_column(default=None)
    last_updated: Mapped[datetime | None] = mapped_column(default=None)
```

### 4.3 Trading Data Models
**File**: `app/models/trading.py`

```python
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class SignalHistory(Base, TimestampMixin):
    """Trading signal history"""
    __tablename__ = "signal_history"
    __table_args__ = (
        Index("idx_signal_history_ticker_date", "ticker", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False)
    date: Mapped[date] = mapped_column(nullable=False)
    signal_type: Mapped[str] = mapped_column(String(20), nullable=False)  # BUY, SELL, HOLD
    signal_value: Mapped[Decimal] = mapped_column(nullable=False)
    confidence: Mapped[Decimal] = mapped_column(nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(nullable=False)
    target_price: Mapped[Decimal] = mapped_column(nullable=False)
    stop_loss: Mapped[Decimal] = mapped_column(nullable=False)
    regime: Mapped[str | None] = mapped_column(String(20), default=None)
    reasons: Mapped[str] = mapped_column(Text, nullable=False)

class PortfolioPerformance(Base, TimestampMixin):
    """Portfolio performance metrics"""
    __tablename__ = "portfolio_performance"
    __table_args__ = (
        Index("idx_portfolio_performance_date", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(nullable=False)
    portfolio_value: Mapped[Decimal] = mapped_column(nullable=False)
    daily_return: Mapped[Decimal] = mapped_column(nullable=False)
    volatility: Mapped[Decimal] = mapped_column(nullable=False)
    sharpe_ratio: Mapped[Decimal | None] = mapped_column(default=None)
    max_drawdown: Mapped[Decimal | None] = mapped_column(default=None)
```

### 4.4 Portfolio Models
**File**: `app/models/portfolio.py`

```python
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class PortfolioPosition(Base, TimestampMixin):
    """Portfolio holdings"""
    __tablename__ = "portfolio_positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    shares: Mapped[Decimal] = mapped_column(nullable=False)
```

### 4.5 System Models
**File**: `app/models/system.py`

```python
from datetime import datetime
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class SystemEvent(Base, TimestampMixin):
    """System event log"""
    __tablename__ = "system_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, default=None)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # INFO, WARNING, ERROR
```

### 4.6 Models Package Init
**File**: `app/models/__init__.py`

```python
"""SQLAlchemy ORM models"""

from app.models.base import Base, TimestampMixin
from app.models.market_data import DailyData, IntradayData, Metadata
from app.models.trading import SignalHistory, PortfolioPerformance
from app.models.portfolio import PortfolioPosition
from app.models.system import SystemEvent

__all__ = [
    "Base",
    "TimestampMixin",
    "DailyData",
    "IntradayData",
    "Metadata",
    "SignalHistory",
    "PortfolioPerformance",
    "PortfolioPosition",
    "SystemEvent",
]
```

---

## Part 5: Database Initialization Module

### 5.1 Database Configuration and Session Management
**File**: `app/db.py`

```python
"""
Database initialization and session management
Supports SQLite, PostgreSQL, and MySQL
"""

import os
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, event, inspect, pool
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.engine import Engine

from app.models.base import Base

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and sessions"""

    def __init__(self, database_url: str | None = None):
        """
        Initialize database manager

        Args:
            database_url: SQLAlchemy database URL
                Example: sqlite:///data/market_data.db
                Example: postgresql://user:pass@localhost/traderrr
                Example: mysql://user:pass@localhost/traderrr
        """
        self.database_url = database_url or self._get_database_url()
        self.engine = self._create_engine()
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
        )
        self.scoped_session = scoped_session(self.SessionLocal)

    @staticmethod
    def _get_database_url() -> str:
        """Get database URL from environment or use SQLite default"""
        # Environment variable takes precedence
        if db_url := os.getenv("DATABASE_URL"):
            return db_url

        # Fall back to SQLite (development/testing default)
        db_type = os.getenv("DATABASE_TYPE", "sqlite")

        if db_type == "postgresql":
            user = os.getenv("DB_USER", "postgres")
            password = os.getenv("DB_PASSWORD", "password")
            host = os.getenv("DB_HOST", "localhost")
            port = os.getenv("DB_PORT", "5432")
            dbname = os.getenv("DB_NAME", "traderrr")
            return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

        elif db_type in ("mysql", "mariadb"):
            user = os.getenv("DB_USER", "root")
            password = os.getenv("DB_PASSWORD", "password")
            host = os.getenv("DB_HOST", "localhost")
            port = os.getenv("DB_PORT", "3306")
            dbname = os.getenv("DB_NAME", "traderrr")
            return f"mysql://{user}:{password}@{host}:{port}/{dbname}"

        # SQLite (default)
        db_path = os.getenv("DATABASE_PATH", "data/market_data.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return f"sqlite:///{db_path}"

    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine with appropriate configuration"""

        # Determine if SQLite
        is_sqlite = self.database_url.startswith("sqlite://")

        kwargs = {
            "echo": os.getenv("SQL_ECHO", "False").lower() == "true",
        }

        if is_sqlite:
            # SQLite configuration
            kwargs.update({
                "connect_args": {"check_same_thread": False},
                "poolclass": pool.StaticPool,  # Single connection for SQLite
            })
        else:
            # PostgreSQL/MySQL configuration
            kwargs.update({
                "pool_size": int(os.getenv("DB_POOL_SIZE", "20")),
                "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "40")),
                "pool_pre_ping": True,  # Test connections before use
                "pool_recycle": 3600,  # Recycle connections after 1 hour
            })

        engine = create_engine(self.database_url, **kwargs)

        # Enable foreign key constraints for SQLite
        if is_sqlite:
            @event.listens_for(Engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        return engine

    def init_db(self) -> None:
        """Create all tables based on ORM models"""
        logger.info(f"Initializing database: {self.database_url}")
        Base.metadata.create_all(self.engine)
        logger.info("Database initialization complete")

    def drop_db(self) -> None:
        """Drop all tables (for testing/cleanup)"""
        logger.warning("Dropping all database tables")
        Base.metadata.drop_all(self.engine)

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()

    @contextmanager
    def session_context(self):
        """Context manager for database sessions

        Usage:
            with db_manager.session_context() as session:
                user = session.query(User).first()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()

    def get_database_info(self) -> dict:
        """Get database information for diagnostics"""
        inspector = inspect(self.engine)
        return {
            "database_url": self.database_url.split("@")[0] + "@***",  # Hide password
            "tables": inspector.get_table_names(),
            "is_connected": self._test_connection(),
        }

    def _test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.engine.connect() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False

    def close(self) -> None:
        """Close database connection pool"""
        self.engine.dispose()
        logger.info("Database connection pool closed")

# Global database manager instance
_db_manager: DatabaseManager | None = None

def init_db_manager(database_url: str | None = None) -> DatabaseManager:
    """Initialize global database manager"""
    global _db_manager
    _db_manager = DatabaseManager(database_url)
    _db_manager.init_db()
    return _db_manager

def get_db_manager() -> DatabaseManager:
    """Get global database manager"""
    if _db_manager is None:
        raise RuntimeError("Database manager not initialized. Call init_db_manager() first.")
    return _db_manager

def get_session() -> Session:
    """Get a database session"""
    return get_db_manager().get_session()
```

---

## Part 6: Configuration Updates

### 6.1 Environment Variable Configuration
**File**: `config/settings.py` (additions)

```python
# Add to existing config classes:

class Config:
    """Base configuration"""

    # Database configuration
    DATABASE_TYPE = os.getenv("DATABASE_TYPE", "sqlite")  # sqlite, postgresql, mysql
    DATABASE_URL = os.getenv("DATABASE_URL", None)
    DATABASE_PATH = os.getenv("DATABASE_PATH", "data/market_data.db")

    # Database pool settings
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "40"))
    DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

    # Database connection settings
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "traderrr")

    # SQL debugging
    SQL_ECHO = os.getenv("SQL_ECHO", "False").lower() == "true"
```

### 6.2 Example .env File
**File**: `.env.example`

```bash
# Database Selection (sqlite, postgresql, mysql)
DATABASE_TYPE=sqlite

# For SQLite:
DATABASE_PATH=data/market_data.db

# For PostgreSQL/MySQL (optional, can use individual env vars instead):
# DATABASE_URL=postgresql://user:pass@localhost:5432/traderrr

# PostgreSQL/MySQL Connection Details:
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=traderrr

# Connection Pool Settings:
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_RECYCLE=3600

# SQL Debugging (for development):
SQL_ECHO=False
```

---

## Part 7: Alembic Migration Framework

### 7.1 Initialize Alembic
**Command to run**:
```bash
alembic init -t sqlalchemy migrations
```

### 7.2 Alembic Configuration
**File**: `alembic.ini` (key changes)

```ini
[sqlalchemy]
# This line will be read by the env.py script to get the database URL
sqlalchemy.url = driver://user:password@localhost/dbname

[alembic]
# path to migration scripts
script_location = migrations

# migration file naming
file_template = %%(rev)s_%%(slug)s
```

### 7.3 Alembic Environment Configuration
**File**: `migrations/env.py` (updated)

```python
"""Alembic migration environment configuration"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os

from app.models.base import Base

# Get database URL from environment
config = context.config
database_url = os.getenv("DATABASE_URL", None)

if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging
fileConfig(config.config_file_name)

# Target metadata for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### 7.4 Initial Migration Template
**File**: `migrations/versions/001_initial_schema.py`

```python
"""Initial database schema

Revision ID: 001
Revises:
Create Date: 2025-11-27 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Create initial schema"""
    # This will be auto-generated by: alembic revision --autogenerate -m "initial schema"
    pass

def downgrade() -> None:
    """Drop all tables"""
    pass
```

---

## Part 8: Application Initialization

### 8.1 Flask App Factory Update
**File**: `app/__init__.py` (add to existing)

```python
"""Application factory"""

from flask import Flask
from app.db import init_db_manager

def create_app(config_name="development"):
    """Create Flask application"""
    app = Flask(__name__)

    # ... existing app configuration ...

    # Initialize database
    @app.before_request
    def setup_db():
        init_db_manager()  # Initialize if not already done

    # ... rest of app setup ...

    return app

# At app startup:
app = create_app()
db_manager = init_db_manager()
```

### 8.2 Main Application Entry Point
**File**: `main.py` (update existing database initialization)

```python
"""Application entry point"""

import logging
from app import create_app
from app.db import init_db_manager

logger = logging.getLogger(__name__)

def main():
    """Main entry point"""

    # Initialize database
    logger.info("Initializing database...")
    db_manager = init_db_manager()
    logger.info(f"Database initialized: {db_manager.get_database_info()}")

    # Create Flask app
    app = create_app()

    # Run application
    logger.info("Starting application...")
    app.run(host="0.0.0.0", port=5000, debug=False)

if __name__ == "__main__":
    main()
```

---

## Part 9: Migration Guide

### 9.1 Creating New Migrations

**Auto-generate migration from model changes**:
```bash
alembic revision --autogenerate -m "Add new_column to users table"
```

**Review generated migration in `migrations/versions/xxx_add_new_column.py`**:
```python
def upgrade() -> None:
    op.add_column('users', sa.Column('new_column', sa.String(), nullable=False))

def downgrade() -> None:
    op.drop_column('users', 'new_column')
```

**Apply migration**:
```bash
alembic upgrade head
```

**Rollback migration**:
```bash
alembic downgrade -1
```

### 9.2 Migration Best Practices

1. **Always review auto-generated migrations** - Alembic may not catch all details
2. **Name migrations descriptively** - `001_initial_schema.py`, `002_add_user_table.py`
3. **Keep migrations small** - One logical change per migration
4. **Test rollbacks** - Ensure `downgrade()` actually works
5. **Never modify old migrations** - Create new ones instead

---

## Part 10: Query Examples (Before & After)

### 10.1 Basic Queries

**BEFORE (Raw SQL)**:
```python
from config.database import DatabaseConfig

db = DatabaseConfig("data/market_data.db")
conn = sqlite3.connect(db.db_path)
cursor = conn.cursor()

cursor.execute("SELECT * FROM daily_data WHERE ticker = ? ORDER BY date DESC LIMIT 1", ("AAPL",))
result = cursor.fetchone()
conn.close()
```

**AFTER (SQLAlchemy)**:
```python
from app.db import get_db_manager
from app.models import DailyData
from sqlalchemy import desc

db = get_db_manager()
with db.session_context() as session:
    last_data = session.query(DailyData) \
        .filter(DailyData.ticker == "AAPL") \
        .order_by(desc(DailyData.date)) \
        .first()
```

### 10.2 Complex Queries

**BEFORE**:
```python
cursor.execute("""
    SELECT ticker, SUM(shares) as total_shares
    FROM portfolio_positions
    GROUP BY ticker
    ORDER BY total_shares DESC
""")
results = cursor.fetchall()
```

**AFTER**:
```python
from sqlalchemy import func

with db.session_context() as session:
    results = session.query(
        PortfolioPosition.ticker,
        func.sum(PortfolioPosition.shares).label('total_shares')
    ).group_by(PortfolioPosition.ticker) \
     .order_by(func.sum(PortfolioPosition.shares).desc()) \
     .all()
```

### 10.3 Inserts and Updates

**BEFORE**:
```python
cursor.execute(
    "INSERT INTO daily_data (ticker, date, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
    ("AAPL", "2025-01-01", 150.0, 155.0, 149.0, 153.0, 1000000)
)
conn.commit()
```

**AFTER**:
```python
from app.models import DailyData

with db.session_context() as session:
    daily = DailyData(
        ticker="AAPL",
        date="2025-01-01",
        open=150.0,
        high=155.0,
        low=149.0,
        close=153.0,
        volume=1000000
    )
    session.add(daily)
    session.commit()
```

---

## Part 11: Testing Strategy

### 11.1 Database Testing

**Test SQLite in-memory database**:
```python
import pytest
from sqlalchemy import create_engine
from app.models.base import Base
from app.db import DatabaseManager

@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing"""
    db = DatabaseManager("sqlite:///:memory:")
    db.init_db()
    yield db
    db.close()

def test_daily_data_insert(test_db):
    """Test inserting market data"""
    with test_db.session_context() as session:
        daily = DailyData(
            ticker="TEST",
            date="2025-01-01",
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000000
        )
        session.add(daily)
        session.commit()

        result = session.query(DailyData).filter_by(ticker="TEST").first()
        assert result.ticker == "TEST"
        assert result.close == 102.0
```

### 11.2 Multi-Database Testing

**Test against multiple database engines**:
```python
@pytest.mark.parametrize("db_url", [
    "sqlite:///:memory:",
    "postgresql://localhost/test_traderrr",
    "mysql://localhost/test_traderrr",
])
def test_all_databases(db_url):
    """Test that models work with all supported databases"""
    db = DatabaseManager(db_url)
    db.init_db()
    # ... run tests ...
    db.drop_db()
```

---

## Part 12: Rollout Checklist

### Pre-Implementation
- [ ] Review and approve this specification
- [ ] Set up feature branch: `feature/phase-0-orm`
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Create Alembic project: `alembic init -t sqlalchemy migrations`

### Implementation
- [ ] Create `app/models/` package with all model files
- [ ] Create `app/db.py` database manager
- [ ] Update `config/settings.py` with database configuration
- [ ] Initialize Alembic with proper `env.py`
- [ ] Create initial migration
- [ ] Update `app/__init__.py` for database initialization
- [ ] Update `main.py` for database startup
- [ ] Create `.env.example` with all configuration options
- [ ] Write unit tests for database layer

### Testing
- [ ] Test with SQLite (default)
- [ ] Test with PostgreSQL (if available)
- [ ] Test with MySQL (if available)
- [ ] Test migrations (upgrade & downgrade)
- [ ] Test session management
- [ ] Run existing test suite (should still pass)

### Documentation
- [ ] Document database configuration options
- [ ] Document ORM model structure
- [ ] Document migration procedures
- [ ] Update CONTRIBUTING.md with database setup

### Deployment
- [ ] Merge to develop branch
- [ ] Tag as release candidate
- [ ] Create detailed release notes
- [ ] Plan Phase 1 (User/Auth) kickoff

---

## Part 13: Success Criteria

### Functional Requirements
- [ ] All 7 tables represented as SQLAlchemy models
- [ ] Database initialization creates all tables
- [ ] All CRUD operations work with ORM
- [ ] Connection pooling configured for multi-DB support
- [ ] Alembic migrations framework operational
- [ ] Foreign key constraints enforced (especially for Phase 1)

### Quality Requirements
- [ ] 100% of existing raw SQL migrated to ORM (by end of Phase 1)
- [ ] All tests pass with new ORM layer
- [ ] No performance regression vs raw SQL
- [ ] Code follows SQLAlchemy best practices
- [ ] Comprehensive error handling

### Compatibility Requirements
- [ ] Works with SQLite (development default)
- [ ] Works with PostgreSQL (production)
- [ ] Works with MySQL/MariaDB (production option)
- [ ] Backward compatible with existing data
- [ ] Can read/write existing database files

---

## Part 14: Risks and Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Breaking existing code | High | High | Keep old database.py, gradual migration |
| Performance regression | Medium | High | Benchmark raw SQL vs ORM queries |
| Complex migrations | Medium | Medium | Test migrations thoroughly |
| Database lock issues | Low | High | Use proper connection pooling |
| PostgreSQL compatibility | Low | High | Test migrations on actual PostgreSQL |

---

## Part 15: Next Steps After Phase 0

Once Phase 0 is complete:

1. **Migrate all raw SQL to ORM** - Replace DataManager raw queries
2. **Begin Phase 1** - User/Auth system with foreign keys
3. **Add relationship definitions** - Foreign key relationships between models
4. **Implement repository pattern** (optional) - Cleaner data access
5. **Add caching layer** (optional) - Query result caching

---

## Appendix: Useful Commands

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize Alembic
alembic init -t sqlalchemy migrations

# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head

# View current revision
alembic current

# View migration history
alembic history --verbose

# Rollback one revision
alembic downgrade -1

# Run tests
pytest tests/ -v

# Check SQL syntax (before applying)
alembic upgrade --sql head | less
```

---

**Document Version**: 1.0
**Status**: Ready for Implementation
**Last Updated**: 2025-11-27
