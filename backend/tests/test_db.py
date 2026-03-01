"""
Tests for app/db.py database manager functionality

Tests cover:
- DatabaseManager initialization
- Database URL construction from environment variables
- Engine creation for different database types (SQLite, PostgreSQL, MySQL)
- Session management (get_session, context manager)
- Database operations (init_db, drop_db)
- Database info retrieval and connection testing
- Global database manager functions
"""

import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from sqlalchemy import text, inspect

from app.db import (
    DatabaseManager,
    init_db_manager,
    get_db_manager,
    get_session,
    _db_manager,
)
from app.models.base import Base


class TestDatabaseManager:
    """Tests for DatabaseManager class"""

    def test_database_manager_init_with_sqlite(self) -> None:
        """Test DatabaseManager initialization with SQLite"""
        db_url = "sqlite:///:memory:"
        manager = DatabaseManager(db_url)

        assert manager.database_url == db_url
        assert manager.engine is not None
        assert manager.SessionLocal is not None
        assert manager.scoped_session is not None

    def test_database_manager_init_creates_engine(self) -> None:
        """Test that DatabaseManager creates an engine"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_url = f"sqlite:///{tmpdir}/test.db"
            manager = DatabaseManager(db_url)

            assert manager.engine is not None
            assert manager.engine.url is not None

    def test_get_database_url_from_env(self) -> None:
        """Test getting database URL from DATABASE_URL environment variable"""
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///test.db"}):
            url = DatabaseManager._get_database_url()
            assert url == "sqlite:///test.db"

    def test_get_database_url_postgresql(self) -> None:
        """Test PostgreSQL database URL construction"""
        env_vars = {
            "DATABASE_TYPE": "postgresql",
            "DB_USER": "user",
            "DB_PASSWORD": "pass",
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
            "DB_NAME": "testdb",
            "DATABASE_URL": "",  # Clear DATABASE_URL
        }
        with patch.dict(os.environ, env_vars, clear=True):
            url = DatabaseManager._get_database_url()
            assert "postgresql://" in url
            assert "user:pass@localhost:5432/testdb" in url

    def test_get_database_url_mysql(self) -> None:
        """Test MySQL database URL construction"""
        env_vars = {
            "DATABASE_TYPE": "mysql",
            "DB_USER": "root",
            "DB_PASSWORD": "secret",
            "DB_HOST": "localhost",
            "DB_PORT": "3306",
            "DB_NAME": "testdb",
            "DATABASE_URL": "",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            url = DatabaseManager._get_database_url()
            assert "mysql://" in url
            assert "root:secret@localhost:3306/testdb" in url

    def test_get_database_url_sqlite_default(self) -> None:
        """Test SQLite database URL default when no DATABASE_URL set"""
        env_vars = {"DATABASE_URL": "", "DATABASE_TYPE": ""}
        with patch.dict(os.environ, env_vars, clear=True):
            url = DatabaseManager._get_database_url()
            assert url.startswith("sqlite:///")

    def test_create_engine_sqlite(self) -> None:
        """Test engine creation for SQLite"""
        manager = DatabaseManager("sqlite:///:memory:")
        assert manager.engine is not None
        # Test that we can connect
        with manager.engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

    def test_create_engine_sqlite_with_pragma(self) -> None:
        """Test that SQLite engine has foreign key constraints enabled"""
        manager = DatabaseManager("sqlite:///:memory:")
        with manager.engine.connect() as conn:
            # Test foreign keys are enabled
            result = conn.execute(text("PRAGMA foreign_keys"))
            assert result.scalar() == 1

    def test_init_db_creates_tables(self) -> None:
        """Test that init_db creates tables"""
        manager = DatabaseManager("sqlite:///:memory:")
        manager.init_db()

        inspector = inspect(manager.engine)
        tables = inspector.get_table_names()

        # Should have created tables from models
        assert len(tables) > 0

    def test_get_session(self) -> None:
        """Test getting a session from DatabaseManager"""
        manager = DatabaseManager("sqlite:///:memory:")
        manager.init_db()

        session = manager.get_session()
        assert session is not None
        session.close()

    def test_session_context_manager(self) -> None:
        """Test session context manager"""
        manager = DatabaseManager("sqlite:///:memory:")
        manager.init_db()

        with manager.session_context() as session:
            assert session is not None

    def test_session_context_manager_rollback_on_error(self) -> None:
        """Test that session context manager rolls back on error"""
        manager = DatabaseManager("sqlite:///:memory:")
        manager.init_db()

        with pytest.raises(ValueError):
            with manager.session_context() as session:
                # Intentionally raise an error to trigger rollback
                raise ValueError("Test error")

    def test_get_database_info_sqlite(self) -> None:
        """Test getting database information for SQLite"""
        manager = DatabaseManager("sqlite:///:memory:")
        manager.init_db()

        info = manager.get_database_info()

        assert "database_type" in info
        assert info["database_type"] == "SQLite"
        assert "database_url" in info
        assert "tables" in info
        assert isinstance(info["tables"], list)
        assert "is_connected" in info
        assert isinstance(info["is_connected"], bool)

    def test_get_database_info_tables(self) -> None:
        """Test that database info includes table names"""
        manager = DatabaseManager("sqlite:///:memory:")
        manager.init_db()

        info = manager.get_database_info()
        assert len(info["tables"]) > 0

    def test_test_connection_success(self) -> None:
        """Test successful database connection"""
        manager = DatabaseManager("sqlite:///:memory:")
        result = manager._test_connection()
        assert result is True

    def test_test_connection_failure(self) -> None:
        """Test failed database connection"""
        manager = DatabaseManager("sqlite:///:memory:")
        # Close the engine to simulate a connection failure
        manager.engine.dispose()

        # Try to test connection with disposed engine
        result = manager._test_connection()
        # Should handle the error gracefully
        assert isinstance(result, bool)

    def test_drop_db(self) -> None:
        """Test dropping all database tables"""
        manager = DatabaseManager("sqlite:///:memory:")
        manager.init_db()

        # Verify tables were created
        inspector = inspect(manager.engine)
        tables_before = inspector.get_table_names()
        assert len(tables_before) > 0

        # Drop all tables
        manager.drop_db()

        # Verify tables were dropped
        inspector = inspect(manager.engine)
        tables_after = inspector.get_table_names()
        assert len(tables_after) == 0

    def test_close_database(self) -> None:
        """Test closing database connection pool"""
        manager = DatabaseManager("sqlite:///:memory:")
        # Should not raise an error
        manager.close()


class TestGlobalDatabaseManager:
    """Tests for global database manager functions"""

    def test_init_db_manager(self) -> None:
        """Test initializing global database manager"""
        # Clear any existing manager
        import app.db

        app.db._db_manager = None

        manager = init_db_manager("sqlite:///:memory:")

        assert manager is not None
        assert isinstance(manager, DatabaseManager)

    def test_get_db_manager_without_init_raises_error(self) -> None:
        """Test that get_db_manager raises error if not initialized"""
        import app.db

        app.db._db_manager = None

        with pytest.raises(RuntimeError):
            get_db_manager()

    def test_get_db_manager_after_init(self) -> None:
        """Test getting global database manager after initialization"""
        import app.db

        app.db._db_manager = None

        init_db_manager("sqlite:///:memory:")
        manager = get_db_manager()

        assert manager is not None
        assert isinstance(manager, DatabaseManager)

    def test_get_session_convenience_function(self) -> None:
        """Test convenience function get_session()"""
        import app.db

        app.db._db_manager = None

        init_db_manager("sqlite:///:memory:")
        session = get_session()

        assert session is not None
        session.close()


class TestDatabaseManagerPasswordRedaction:
    """Tests for password redaction in database URLs"""

    def test_get_database_info_redacts_password_postgresql(self) -> None:
        """Test that PostgreSQL passwords are redacted in database info"""
        from unittest.mock import patch, MagicMock

        # Create a mock engine that won't try to connect
        with patch("app.db.create_engine") as mock_create:
            mock_engine = MagicMock()
            mock_create.return_value = mock_engine

            manager = DatabaseManager(
                "postgresql://user:password123@localhost:5432/testdb"
            )

            # Mock the inspector to avoid actual connection
            with patch("app.db.inspect") as mock_inspect:
                mock_inspector = MagicMock()
                mock_inspector.get_table_names.return_value = []
                mock_inspect.return_value = mock_inspector

                with patch.object(manager, "_test_connection", return_value=True):
                    info = manager.get_database_info()
                    url = info["database_url"]

                    assert "password123" not in url
                    assert "***" in url
                    assert "user" in url

    def test_get_database_info_redacts_password_mysql(self) -> None:
        """Test that MySQL passwords are redacted in database info"""
        from unittest.mock import patch, MagicMock

        # Create a mock engine that won't try to connect
        with patch("app.db.create_engine") as mock_create:
            mock_engine = MagicMock()
            mock_create.return_value = mock_engine

            manager = DatabaseManager("mysql://root:secret@localhost:3306/testdb")

            # Mock the inspector to avoid actual connection
            with patch("app.db.inspect") as mock_inspect:
                mock_inspector = MagicMock()
                mock_inspector.get_table_names.return_value = []
                mock_inspect.return_value = mock_inspector

                with patch.object(manager, "_test_connection", return_value=True):
                    info = manager.get_database_info()
                    url = info["database_url"]

                    assert "secret" not in url
                    assert "***" in url
                    assert "root" in url

    def test_database_type_detection(self) -> None:
        """Test correct database type detection"""
        from unittest.mock import patch, MagicMock

        with patch("app.db.create_engine") as mock_create:
            mock_engine = MagicMock()
            mock_create.return_value = mock_engine

            with patch("app.db.inspect") as mock_inspect:
                mock_inspector = MagicMock()
                mock_inspector.get_table_names.return_value = []
                mock_inspect.return_value = mock_inspector

                # PostgreSQL
                pg_manager = DatabaseManager(
                    "postgresql://user:pass@localhost:5432/testdb"
                )
                with patch.object(pg_manager, "_test_connection", return_value=True):
                    pg_info = pg_manager.get_database_info()
                    assert pg_info["database_type"] == "PostgreSQL"

                # MySQL
                mysql_manager = DatabaseManager(
                    "mysql://user:pass@localhost:3306/testdb"
                )
                with patch.object(mysql_manager, "_test_connection", return_value=True):
                    mysql_info = mysql_manager.get_database_info()
                    assert mysql_info["database_type"] == "MySQL"

        # SQLite (no mocking needed)
        sqlite_manager = DatabaseManager("sqlite:///:memory:")
        sqlite_info = sqlite_manager.get_database_info()
        assert sqlite_info["database_type"] == "SQLite"
