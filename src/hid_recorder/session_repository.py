"""Repository for Session domain model CRUD operations."""

import json
from datetime import datetime
from sqlite3 import Row

from ulid import ULID

from hid_recorder.database import DatabaseManager
from hid_recorder.models import Session


class SessionRepository:
    """Repository for managing Session persistence.

    This class follows the Repository Pattern and Dependency Inversion Principle
    by depending on the DatabaseManager abstraction rather than concrete database
    implementation details.

    Attributes:
        db_manager: DatabaseManager instance for database access.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize SessionRepository with a DatabaseManager.

        Args:
            db_manager: DatabaseManager instance for database operations.
        """
        self.db_manager = db_manager

    def create(self, session: Session) -> None:
        """Create a new session in the database.

        Args:
            session: Session object to persist.
        """
        with self.db_manager as conn:
            conn.execute(
                """
                INSERT INTO sessions
                    (id, name, started_at, ended_at, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(session.id),
                    session.name,
                    session.started_at,
                    session.ended_at,
                    json.dumps(session.metadata),
                ),
            )

    def get(self, session_id: ULID) -> Session | None:
        """Retrieve a session by its ID.

        Args:
            session_id: ULID of the session to retrieve.

        Returns:
            Session object if found, None otherwise.
        """
        with self.db_manager as conn:
            cursor = conn.execute(
                """
                SELECT id, name, started_at, ended_at, metadata
                FROM sessions
                WHERE id = ?
                """,
                (str(session_id),),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_session(row)

    def end(self, session_id: ULID, ended_at: datetime) -> None:
        """End a session by setting its ended_at timestamp.

        Args:
            session_id: ULID of the session to end.
            ended_at: Timestamp when the session ended.
        """
        with self.db_manager as conn:
            conn.execute(
                """
                UPDATE sessions
                SET ended_at = ?
                WHERE id = ?
                """,
                (ended_at, str(session_id)),
            )

    def list_all(self) -> list[Session]:
        """List all sessions.

        Returns:
            List of all Session objects.
        """
        with self.db_manager as conn:
            cursor = conn.execute(
                """
                SELECT id, name, started_at, ended_at, metadata
                FROM sessions
                ORDER BY started_at DESC
                """
            )
            rows = cursor.fetchall()

        return [self._row_to_session(row) for row in rows]

    def list_active(self) -> list[Session]:
        """List only active (not ended) sessions.

        Returns:
            List of active Session objects.
        """
        with self.db_manager as conn:
            cursor = conn.execute(
                """
                SELECT id, name, started_at, ended_at, metadata
                FROM sessions
                WHERE ended_at IS NULL
                ORDER BY started_at DESC
                """
            )
            rows = cursor.fetchall()

        return [self._row_to_session(row) for row in rows]

    def list_by_name_pattern(self, pattern: str) -> list[Session]:
        """List sessions matching a name pattern (SQL LIKE pattern).

        Args:
            pattern: SQL LIKE pattern (e.g., "test_%" for names starting with "test_").

        Returns:
            List of matching Session objects.
        """
        with self.db_manager as conn:
            cursor = conn.execute(
                """
                SELECT id, name, started_at, ended_at, metadata
                FROM sessions
                WHERE name LIKE ?
                ORDER BY started_at DESC
                """,
                (pattern,),
            )
            rows = cursor.fetchall()

        return [self._row_to_session(row) for row in rows]

    def delete(self, session_id: ULID) -> None:
        """Delete a session from the database.

        Due to CASCADE foreign key constraint, this will also delete all events
        associated with the session.

        Args:
            session_id: ULID of the session to delete.
        """
        with self.db_manager as conn:
            conn.execute(
                """
                DELETE FROM sessions
                WHERE id = ?
                """,
                (str(session_id),),
            )

    def _row_to_session(self, row: Row) -> Session:
        """Convert a database row to a Session object.

        Args:
            row: Database row (id, name, started_at, ended_at, metadata).

        Returns:
            Session object constructed from the row data.
        """
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        return Session.model_validate(dict(row, metadata=metadata))
