"""Repository for Event domain model CRUD operations."""

from sqlite3 import Row

from ulid import ULID

from hid_recorder.database import DatabaseManager
from hid_recorder.models import EventItem


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

    def create(self, event: EventItem) -> ULID:
        """Create a new event in the database.

        Args:
            event: Event object to persist (with pre-generated ULID).

        Returns:
            The id (ULID) of the created event.
        """
        with self.db_manager as conn:
            conn.execute(
                """
                INSERT INTO events
                    (id, session_id, timestamp, device, kind, code,
                     code_name, value)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(event.id),
                    str(event.session_id),
                    event.event.timestamp,
                    event.event.device,
                    event.event.kind,
                    event.event.code,
                    event.event.code_name,
                    event.event.value,
                ),
            )
        return event.id

    def get_by_session(
        self,
        session_id: ULID,
        device_filter: str | None = None,
        kind_filter: str | None = None,
    ) -> list[EventItem]:
        """Retrieve all events for a session, with optional filtering.

        Args:
            session_id: ULID of the session.
            device_filter: Optional device path to filter by.
            kind_filter: Optional event kind to filter by (KEY, REL, ABS).

        Returns:
            List of Event objects, ordered by timestamp.
        """
        query = """
            SELECT id, session_id, timestamp, device, kind, code, code_name, value
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

    def _row_to_event(self, row: Row) -> EventItem:
        """Convert a database row to an EventItem object.

        Args:
            row: Database row
                (id, session_id, timestamp, device, kind, code, code_name, value).

        Returns:
            EventItem object constructed from the row data.
        """
        temp = dict(row)
        id_ = temp["id"]
        session_id = temp["session_id"]
        del temp["id"]
        del temp["session_id"]
        return EventItem.model_validate(
            {"id": id_, "session_id": session_id, "event": temp}
        )
