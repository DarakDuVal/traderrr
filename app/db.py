"""
Database initialization and session management

Provides:
- DatabaseManager: Main class for database operations
- Support for SQLite, PostgreSQL, MySQL
- Connection pooling and session management
- Database initialization and health checks
"""

import os
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, event, inspect, pool, text
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.engine import Engine

from app.models.base import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions

    Supports multiple database types:
    - SQLite (single file, development/testing)
    - PostgreSQL (cloud-ready, production)
    - MySQL/MariaDB (production alternative)

    Features:
    - Connection pooling (database-dependent)
    - Session management with context managers
    - Automatic table creation from models
    - Database health checks
    """

    def __init__(self, database_url: str | None = None):
        """
        Initialize database manager

        Args:
            database_url: SQLAlchemy database URL
                Examples:
                - sqlite:///data/market_data.db (development)
                - postgresql://user:pass@localhost/traderrr (production)
                - mysql://user:pass@localhost/traderrr (production)

                If not provided, will construct from environment variables
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
        """Get database URL from environment or use SQLite default

        Environment variables checked (in order):
        1. DATABASE_URL - Full connection string
        2. DATABASE_TYPE - Type of database (sqlite, postgresql, mysql)
        3. Individual DB_* variables - For constructing URL

        Returns:
            SQLAlchemy database URL string
        """
        # Environment variable takes precedence
        if db_url := os.getenv("DATABASE_URL"):
            logger.info("Using DATABASE_URL from environment")
            return db_url

        # Fall back to database type selection
        db_type = os.getenv("DATABASE_TYPE", "sqlite").lower()

        if db_type == "postgresql":
            user = os.getenv("DB_USER", "postgres")
            password = os.getenv("DB_PASSWORD", "password")
            host = os.getenv("DB_HOST", "localhost")
            port = os.getenv("DB_PORT", "5432")
            dbname = os.getenv("DB_NAME", "traderrr")
            url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
            logger.info(f"Using PostgreSQL database: {host}:{port}/{dbname}")
            return url

        elif db_type in ("mysql", "mariadb"):
            user = os.getenv("DB_USER", "root")
            password = os.getenv("DB_PASSWORD", "password")
            host = os.getenv("DB_HOST", "localhost")
            port = os.getenv("DB_PORT", "3306")
            dbname = os.getenv("DB_NAME", "traderrr")
            url = f"mysql://{user}:{password}@{host}:{port}/{dbname}"
            logger.info(f"Using MySQL/MariaDB database: {host}:{port}/{dbname}")
            return url

        # SQLite (default)
        db_path = os.getenv("DATABASE_PATH", "data/market_data.db")
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        url = f"sqlite:///{db_path}"
        logger.info(f"Using SQLite database: {db_path}")
        return url

    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine with appropriate configuration

        Configures:
        - Connection pooling (different for SQLite vs PostgreSQL/MySQL)
        - Foreign key constraints (SQLite)
        - Connection testing and recycling (for long-lived connections)
        - SQL echo (for debugging)

        Returns:
            SQLAlchemy Engine instance
        """

        # Determine if SQLite
        is_sqlite = self.database_url.startswith("sqlite://")

        kwargs = {
            "echo": os.getenv("SQL_ECHO", "False").lower() == "true",
        }

        if is_sqlite:
            # SQLite configuration
            # Use static pool since SQLite is file-based and single-threaded
            kwargs.update({
                "connect_args": {"check_same_thread": False},
                "poolclass": pool.StaticPool,
            })
            logger.info("SQLite engine configured with StaticPool")
        else:
            # PostgreSQL/MySQL configuration
            # Use QueuePool for better multi-threaded performance
            kwargs.update({
                "pool_size": int(os.getenv("DB_POOL_SIZE", "20")),
                "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "40")),
                "pool_pre_ping": True,  # Test connection before use
                "pool_recycle": 3600,   # Recycle connections after 1 hour
            })
            logger.info(
                f"Database engine configured with QueuePool "
                f"(size={kwargs['pool_size']}, overflow={kwargs['max_overflow']})"
            )

        engine = create_engine(self.database_url, **kwargs)

        # Enable foreign key constraints for SQLite
        if is_sqlite:
            @event.listens_for(Engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                """Enable foreign keys in SQLite"""
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

            logger.info("SQLite PRAGMA foreign_keys enabled")

        return engine

    def init_db(self) -> None:
        """Create all tables based on ORM models

        Creates tables for all models that inherit from Base.
        Safe to call multiple times - only creates missing tables.
        """
        logger.info(f"Initializing database: {self.database_url.split('@')[0] if '@' in self.database_url else self.database_url.split(':')[0]}")
        Base.metadata.create_all(self.engine)
        logger.info("Database initialization complete")

    def drop_db(self) -> None:
        """Drop all tables (for testing/cleanup)

        CAUTION: This is destructive and will delete all data.
        Only use in development/testing environments.
        """
        logger.warning("Dropping all database tables - THIS IS DESTRUCTIVE")
        Base.metadata.drop_all(self.engine)
        logger.warning("All tables dropped")

    def get_session(self) -> Session:
        """Get a new database session

        Returns:
            SQLAlchemy Session instance

        Example:
            session = db_manager.get_session()
            try:
                result = session.query(User).first()
                session.commit()
            finally:
                session.close()
        """
        return self.SessionLocal()

    @contextmanager
    def session_context(self):
        """Context manager for database sessions

        Automatically commits on success, rolls back on error,
        and closes the session regardless.

        Yields:
            SQLAlchemy Session instance

        Example:
            with db_manager.session_context() as session:
                user = session.query(User).first()
                # Automatically commits on exit
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
        """Get database information for diagnostics

        Returns:
            Dictionary with database info including:
            - database_url (with password redacted)
            - tables: list of table names
            - is_connected: connection test result
        """
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()

        # Redact password in URL for logging
        safe_url = self.database_url
        if "@" in safe_url:
            scheme, rest = safe_url.split("://", 1)
            credentials, host = rest.split("@", 1)
            user = credentials.split(":")[0]
            safe_url = f"{scheme}://{user}:***@{host}"

        # Determine database type from URL
        if self.database_url.startswith("postgresql://"):
            db_type = "PostgreSQL"
        elif self.database_url.startswith("mysql://"):
            db_type = "MySQL"
        else:
            db_type = "SQLite"

        return {
            "database_type": db_type,
            "database_url": safe_url,
            "tables": tables,
            "is_connected": self._test_connection(),
        }

    def _test_connection(self) -> bool:
        """Test database connection

        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False

    def close(self) -> None:
        """Close database connection pool

        Call this on application shutdown to properly close connections.
        """
        self.engine.dispose()
        logger.info("Database connection pool closed")


# Global database manager instance
_db_manager: DatabaseManager | None = None


def init_db_manager(database_url: str | None = None) -> DatabaseManager:
    """Initialize global database manager

    Should be called once at application startup.

    Args:
        database_url: Optional database URL (if not provided, uses environment)

    Returns:
        DatabaseManager instance
    """
    global _db_manager
    _db_manager = DatabaseManager(database_url)
    _db_manager.init_db()
    return _db_manager


def get_db_manager() -> DatabaseManager:
    """Get global database manager

    Must call init_db_manager() first.

    Returns:
        DatabaseManager instance

    Raises:
        RuntimeError: If database manager not initialized
    """
    if _db_manager is None:
        raise RuntimeError("Database manager not initialized. Call init_db_manager() first.")
    return _db_manager


def get_session() -> Session:
    """Get a database session

    Convenience function equivalent to get_db_manager().get_session()

    Returns:
        SQLAlchemy Session instance
    """
    return get_db_manager().get_session()
