"""Test database connection and schema management."""

import sqlite3
from pathlib import Path

import pytest

from hid_recorder.database import DatabaseManager


class TestDatabaseManager:
    """Test DatabaseManager for database initialization and schema management."""

    def test_create_database_manager_with_memory_db(self) -> None:
        """Test creating DatabaseManager with in-memory database."""
        db_path = ":memory:"
        manager = DatabaseManager(db_path)

        assert manager.db_path == db_path

    def test_create_database_manager_with_file_db(self, tmp_path: Path) -> None:
        """Test creating DatabaseManager with file-based database."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))

        assert manager.db_path == str(db_path)

    def test_initialize_creates_sessions_table(self, tmp_path: Path) -> None:
        """Test that initialize() creates sessions table with correct schema."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))
        manager.initialize()

        # Verify sessions table exists
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
            )
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == "sessions"

            # Verify columns
            cursor = conn.execute("PRAGMA table_info(sessions)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            expected_columns = {
                "id": "TEXT",
                "name": "TEXT",
                "started_at": "TIMESTAMP",
                "ended_at": "TIMESTAMP",
                "metadata": "TEXT",
                "created_at": "TIMESTAMP",
            }
            assert columns == expected_columns

    def test_initialize_creates_events_table(self, tmp_path: Path) -> None:
        """Test that initialize() creates events table with correct schema."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))
        manager.initialize()

        # Verify events table exists
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='events'"
            )
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == "events"

            # Verify columns
            cursor = conn.execute("PRAGMA table_info(events)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            expected_columns = {
                "id": "TEXT",
                "session_id": "TEXT",
                "timestamp": "REAL",
                "device": "TEXT",
                "kind": "TEXT",
                "code": "INTEGER",
                "code_name": "TEXT",
                "value": "INTEGER",
            }
            assert columns == expected_columns

    def test_initialize_creates_indexes(self, tmp_path: Path) -> None:
        """Test that initialize() creates necessary indexes."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))
        manager.initialize()

        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = {row[0] for row in cursor.fetchall()}

            # Expected indexes
            expected_indexes = {
                "idx_sessions_name",
                "idx_sessions_started_at",
                "idx_sessions_ended_at",
                "idx_events_session_id",
                "idx_events_timestamp",
            }

            assert expected_indexes.issubset(indexes)

    def test_initialize_sets_foreign_key_constraint(self, tmp_path: Path) -> None:
        """Test that foreign key constraint is set on events.session_id."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))
        manager.initialize()

        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.execute("PRAGMA foreign_key_list(events)")
            fk_info = cursor.fetchall()

            assert len(fk_info) == 1
            # fk_info format: [id, seq, table, from, to, on_update, on_delete, match]
            assert fk_info[0][2] == "sessions"  # references sessions table
            assert fk_info[0][3] == "session_id"  # from column
            assert fk_info[0][4] == "id"  # to column
            assert fk_info[0][6] == "CASCADE"  # on_delete CASCADE

    def test_initialize_is_idempotent(self, tmp_path: Path) -> None:
        """Test that initialize() can be called multiple times safely."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))

        # Call initialize multiple times
        manager.initialize()
        manager.initialize()
        manager.initialize()

        # Should not raise any errors and tables should still exist
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
            assert "sessions" in tables
            assert "events" in tables

    def test_get_connection_returns_working_connection(self, tmp_path: Path) -> None:
        """Test that get_connection() returns a working database connection."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))
        manager.initialize()

        conn = manager.get_connection()
        assert conn is not None

        # Verify we can execute queries
        cursor = conn.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1

        conn.close()

    def test_context_manager_provides_connection(self, tmp_path: Path) -> None:
        """Test that DatabaseManager can be used as a context manager."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))
        manager.initialize()

        with manager as conn:
            cursor = conn.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1

    def test_context_manager_commits_on_success(self, tmp_path: Path) -> None:
        """Test that context manager commits transaction on successful exit."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))
        manager.initialize()

        session_id = "test-session-id"
        with manager as conn:
            conn.execute(
                "INSERT INTO sessions "
                "(id, name, started_at, ended_at, metadata) "
                "VALUES (?, ?, datetime('now'), NULL, '{}')",
                (session_id, "test"),
            )

        # Verify data was committed
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == session_id

    def test_context_manager_rolls_back_on_exception(self, tmp_path: Path) -> None:
        """Test that context manager rolls back transaction on exception."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))
        manager.initialize()

        session_id = "test-session-id"
        error_message = "Test error"

        # Helper function to perform the operation that raises
        def insert_and_raise() -> None:
            with manager as conn:
                conn.execute(
                    "INSERT INTO sessions "
                    "(id, name, started_at, ended_at, metadata) "
                    "VALUES (?, ?, datetime('now'), NULL, '{}')",
                    (session_id, "test"),
                )
                raise RuntimeError(error_message)

        with pytest.raises(RuntimeError, match=error_message):
            insert_and_raise()

        # Verify data was rolled back
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
            result = cursor.fetchone()
            assert result is None
