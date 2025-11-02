"""Test EventRepository for event CRUD operations."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from hid_interceptor import KeyEvent, RelEvent
from ulid import ULID

from hid_recorder.database import DatabaseManager
from hid_recorder.event_repository import EventRepository
from hid_recorder.models import EventItem, Session
from hid_recorder.session_repository import SessionRepository


class TestEventRepository:
    """Test EventRepository for creating, reading, and managing events."""

    @pytest.fixture
    def db_manager(self, tmp_path: Path) -> DatabaseManager:
        """Create and initialize a DatabaseManager for testing."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))
        manager.initialize()
        return manager

    @pytest.fixture
    def session_repository(self, db_manager: DatabaseManager) -> SessionRepository:
        """Create a SessionRepository for testing."""
        return SessionRepository(db_manager)

    @pytest.fixture
    def event_repository(self, db_manager: DatabaseManager) -> EventRepository:
        """Create an EventRepository for testing."""
        return EventRepository(db_manager)

    @pytest.fixture
    def test_session(self, session_repository: SessionRepository) -> Session:
        """Create a test session."""
        session = Session(
            id=ULID(),
            name="test_session",
            started_at=datetime.now(timezone.utc),
            ended_at=None,
            metadata={},
        )
        session_repository.create(session)
        return session

    def test_create_event_item(
        self,
        event_repository: EventRepository,
        test_session: Session,
        db_manager: DatabaseManager,
    ) -> None:
        """Test creating a new event."""
        timestamp = 1234567890.123456
        event = EventItem(
            id=ULID(),
            session_id=test_session.id,
            event=KeyEvent(
                timestamp=timestamp,
                device="/dev/input/event0",
                code=30,
                code_name="KEY_A",
                value=1,
            ),
        )

        event_id = event_repository.create(event)

        # Verify event was created and ID was returned
        assert isinstance(event_id, ULID)

        # Verify event in database
        expected_code = 30
        with db_manager as conn:
            cursor = conn.execute(
                "SELECT session_id, device, kind, code FROM events WHERE id = ?",
                (str(event_id),),
            )
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == str(test_session.id)
            assert result[1] == "/dev/input/event0"
            assert result[2] == "KEY"
            assert result[3] == expected_code

    def test_get_events_by_session(
        self,
        event_repository: EventRepository,
        test_session: Session,
    ) -> None:
        """Test retrieving all events for a session."""
        # Create multiple events
        event1 = EventItem(
            id=ULID(),
            session_id=test_session.id,
            event=KeyEvent(
                timestamp=1000.0,
                device="/dev/input/event0",
                code=30,
                code_name="KEY_A",
                value=1,
            ),
        )
        event2 = EventItem(
            id=ULID(),
            session_id=test_session.id,
            event=KeyEvent(
                timestamp=1001.0,
                device="/dev/input/event0",
                code=30,
                code_name="KEY_A",
                value=0,
            ),
        )

        event_repository.create(event1)
        event_repository.create(event2)

        # Retrieve events
        expected_event_count = 2
        first_timestamp = 1000.0
        second_timestamp = 1001.0
        events = event_repository.get_by_session(test_session.id)
        assert len(events) == expected_event_count
        assert all(e.session_id == test_session.id for e in events)

        # Verify ordering by timestamp
        assert events[0].event.timestamp == first_timestamp
        assert events[1].event.timestamp == second_timestamp

    def test_get_events_for_nonexistent_session(
        self, event_repository: EventRepository
    ) -> None:
        """Test that getting events for nonexistent session returns empty list."""
        nonexistent_session_id = ULID()
        events = event_repository.get_by_session(nonexistent_session_id)
        assert events == []

    def test_get_events_by_session_with_device_filter(
        self,
        event_repository: EventRepository,
        test_session: Session,
    ) -> None:
        """Test retrieving events filtered by device."""
        # Create events from different devices
        event_keyboard = EventItem(
            id=ULID(),
            session_id=test_session.id,
            event=KeyEvent(
                timestamp=1000.0,
                device="/dev/input/event0",
                code=30,
                code_name="KEY_A",
                value=1,
            ),
        )
        event_mouse = EventItem(
            id=ULID(),
            session_id=test_session.id,
            event=RelEvent(
                timestamp=1001.0,
                device="/dev/input/event1",
                code=0,
                code_name="REL_X",
                value=10,
            ),
        )

        event_repository.create(event_keyboard)
        event_repository.create(event_mouse)

        # Filter by keyboard device
        keyboard_events = event_repository.get_by_session(
            test_session.id, device_filter="/dev/input/event0"
        )
        assert len(keyboard_events) == 1
        assert keyboard_events[0].event.device == "/dev/input/event0"
        assert keyboard_events[0].event.kind.value == "KEY"

    def test_get_events_by_session_with_kind_filter(
        self,
        event_repository: EventRepository,
        test_session: Session,
    ) -> None:
        """Test retrieving events filtered by kind."""
        # Create events of different kinds
        event_key = EventItem(
            id=ULID(),
            session_id=test_session.id,
            event=KeyEvent(
                timestamp=1000.0,
                device="/dev/input/event0",
                code=30,
                code_name="KEY_A",
                value=1,
            ),
        )
        event_rel = EventItem(
            id=ULID(),
            session_id=test_session.id,
            event=RelEvent(
                timestamp=1001.0,
                device="/dev/input/event0",
                code=0,
                code_name="REL_X",
                value=10,
            ),
        )

        event_repository.create(event_key)
        event_repository.create(event_rel)

        # Filter by KEY kind
        key_events = event_repository.get_by_session(test_session.id, kind_filter="KEY")
        assert len(key_events) == 1
        assert key_events[0].event.kind.value == "KEY"

    def test_count_events_by_session(
        self,
        event_repository: EventRepository,
        test_session: Session,
    ) -> None:
        """Test counting events for a session."""
        # Create multiple events
        expected_event_count = 3
        for i in range(expected_event_count):
            event = EventItem(
                id=ULID(),
                session_id=test_session.id,
                event=KeyEvent(
                    timestamp=1000.0 + i,
                    device="/dev/input/event0",
                    code=30,
                    code_name="KEY_A",
                    value=1,
                ),
            )
            event_repository.create(event)

        # Count events
        count = event_repository.count_by_session(test_session.id)
        assert count == expected_event_count

    def test_count_events_for_nonexistent_session(
        self, event_repository: EventRepository
    ) -> None:
        """Test that counting events for nonexistent session returns 0."""
        nonexistent_session_id = ULID()
        count = event_repository.count_by_session(nonexistent_session_id)
        assert count == 0

    def test_delete_events_cascades_on_session_delete(
        self,
        event_repository: EventRepository,
        session_repository: SessionRepository,
        test_session: Session,
    ) -> None:
        """Test that deleting a session cascades to delete its events."""
        # Create events
        expected_event_count = 2
        for i in range(expected_event_count):
            event = EventItem(
                id=ULID(),
                session_id=test_session.id,
                event=KeyEvent(
                    timestamp=1000.0 + i,
                    device="/dev/input/event0",
                    code=30,
                    code_name="KEY_A",
                    value=1,
                ),
            )
            event_repository.create(event)

        # Verify events exist
        count_before = event_repository.count_by_session(test_session.id)
        assert count_before == expected_event_count

        # Delete session
        session_repository.delete(test_session.id)

        # Verify events were deleted
        count_after = event_repository.count_by_session(test_session.id)
        assert count_after == 0

    def test_event_id_is_auto_assigned(
        self,
        event_repository: EventRepository,
        test_session: Session,
    ) -> None:
        """Test that event_id is auto-assigned and increments."""
        event1 = EventItem(
            id=ULID(),
            session_id=test_session.id,
            event=KeyEvent(
                timestamp=1000.0,
                device="/dev/input/event0",
                code=30,
                code_name="KEY_A",
                value=1,
            ),
        )
        event2 = EventItem(
            id=ULID(),
            session_id=test_session.id,
            event=KeyEvent(
                timestamp=1001.0,
                device="/dev/input/event0",
                code=31,
                code_name="KEY_S",
                value=1,
            ),
        )

        id1 = event_repository.create(event1)
        id2 = event_repository.create(event2)

        assert id1 is not None
        assert id2 is not None
        assert id2 > id1  # IDs should increment
