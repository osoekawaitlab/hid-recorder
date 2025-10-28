"""Repository for Event domain model CRUD operations."""

from ulid import ULID

from hid_recorder.database import DatabaseManager
from hid_recorder.models import Event


class EventRepository:
    """Repository for managing Event persistence.

    This class follows the Repository Pattern and Single Responsibility Principle
    by focusing solely on Event data access operations.

    Attributes:
        db_manager: DatabaseManager instance for database access.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize EventRepository with a DatabaseManager.

        Args:
            db_manager: DatabaseManager instance for database operations.
        """
        self.db_manager = db_manager

    def create(self, event: Event) -> ULID:
        """Create a new event in the database.

        Args:
            event: Event object to persist (with pre-generated ULID).

        Returns:
            The event_id (ULID) of the created event.
        """
        with self.db_manager as conn:
            conn.execute(
                """
                INSERT INTO events
                    (event_id, session_id, timestamp, device, kind, code,
                     code_name, value)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(event.event_id),
                    str(event.session_id),
                    event.timestamp,
                    event.device,
                    event.kind,
                    event.code,
                    event.code_name,
                    event.value,
                ),
            )
        return event.event_id

    def get_by_session(
        self,
        session_id: ULID,
        device_filter: str | None = None,
        kind_filter: str | None = None,
    ) -> list[Event]:
        """Retrieve all events for a session, with optional filtering.

        Args:
            session_id: ULID of the session.
            device_filter: Optional device path to filter by.
            kind_filter: Optional event kind to filter by (KEY, REL, ABS).

        Returns:
            List of Event objects, ordered by timestamp.
        """
        query = """
            SELECT event_id, session_id, timestamp, device, kind, code, code_name, value
            FROM events
            WHERE session_id = ?
        """
        params: list[str] = [str(session_id)]

        if device_filter is not None:
            query += " AND device = ?"
            params.append(device_filter)

        if kind_filter is not None:
            query += " AND kind = ?"
            params.append(kind_filter)

        query += " ORDER BY timestamp ASC"

        with self.db_manager as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

        return [self._row_to_event(row) for row in rows]

    def count_by_session(self, session_id: ULID) -> int:
        """Count the number of events for a session.

        Args:
            session_id: ULID of the session.

        Returns:
            Number of events in the session.
        """
        with self.db_manager as conn:
            cursor = conn.execute(
                """
                SELECT COUNT(*)
                FROM events
                WHERE session_id = ?
                """,
                (str(session_id),),
            )
            result = cursor.fetchone()

        return result[0] if result else 0

    def _row_to_event(self, row: tuple) -> Event:  # type: ignore[type-arg]
        """Convert a database row to an Event object.

        Args:
            row: Database row tuple
                (event_id, session_id, timestamp, device, kind, code, code_name, value).

        Returns:
            Event object constructed from the row data.
        """
        (
            event_id_str,
            session_id_str,
            timestamp,
            device,
            kind,
            code,
            code_name,
            value,
        ) = row

        return Event(
            event_id=ULID.from_str(event_id_str),
            session_id=ULID.from_str(session_id_str),
            timestamp=timestamp,
            device=device,
            kind=kind,
            code=code,
            code_name=code_name,
            value=value,
        )
