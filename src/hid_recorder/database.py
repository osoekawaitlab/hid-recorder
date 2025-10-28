"""Database connection and schema management."""

import sqlite3
from threading import RLock
from types import TracebackType


class DatabaseManager:
    """Manages SQLite database connection and schema.

    This class follows the Single Responsibility Principle by focusing solely on
    database connection management and schema initialization.

    Attributes:
        db_path: Path to the SQLite database file (or ":memory:" for in-memory DB).
    """

    def __init__(self, db_path: str) -> None:
        """Initialize DatabaseManager with a database path.

        Args:
            db_path: Path to SQLite database file or ":memory:" for in-memory database.
        """
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None
        # Re-entrant lock protects the shared connection across worker threads.
        self._lock = RLock()

    def initialize(self) -> None:
        """Initialize database schema (tables and indexes).

        This method is idempotent and can be safely called multiple times.
        Creates:
            - sessions table for recording sessions
            - events table for HID events
            - indexes for efficient queries
            - foreign key constraints
        """
        conn = self.get_connection()

        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")

        # Create sessions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                started_at TIMESTAMP NOT NULL,
                ended_at TIMESTAMP,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create events table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                device TEXT NOT NULL,
                kind TEXT NOT NULL,
                code INTEGER NOT NULL,
                code_name TEXT NOT NULL,
                value INTEGER NOT NULL,
                FOREIGN KEY (session_id)
                    REFERENCES sessions(session_id)
                    ON DELETE CASCADE
            )
        """)

        # Create indexes for sessions
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_name ON sessions(name)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_ended_at ON sessions(ended_at)
        """)

        # Create indexes for events
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_session_id ON events(session_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)
        """)

        conn.commit()

    def get_connection(self) -> sqlite3.Connection:
        """Get a connection to the database.

        Returns:
            SQLite database connection.
        """
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            # Enable foreign keys for this connection
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    def __enter__(self) -> sqlite3.Connection:
        """Enter context manager, returning a database connection.

        Returns:
            SQLite database connection with transaction started.
        """
        self._lock.acquire()
        self._conn = self.get_connection()
        return self._conn

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager, committing or rolling back transaction.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        """
        try:
            if self._conn is not None:
                if exc_type is None:
                    # No exception, commit the transaction
                    self._conn.commit()
                else:
                    # Exception occurred, rollback the transaction
                    self._conn.rollback()
        finally:
            self._lock.release()
