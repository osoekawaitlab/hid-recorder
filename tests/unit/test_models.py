"""Test domain models."""

from datetime import datetime, timezone

import pytest
from hid_interceptor.models import KeyEvent
from pydantic import ValidationError
from ulid import ULID

from hid_recorder.models import EventItem, Session


class TestSession:
    """Test Session domain model."""

    def test_create_session_with_minimal_fields(self) -> None:
        """Test creating a session with minimal required fields."""
        session_id = ULID()
        name = "test_session"
        started_at = datetime.now(timezone.utc)

        session = Session(
            id=session_id,
            name=name,
            started_at=started_at,
            ended_at=None,
            metadata={},
        )

        assert session.id == session_id
        assert session.name == name
        assert session.started_at == started_at
        assert session.ended_at is None
        assert session.metadata == {}

    def test_create_session_with_metadata(self) -> None:
        """Test creating a session with metadata."""
        session_id = ULID()
        metadata = {"device": "custom_keyboard", "version": "1.0.0"}

        session = Session(
            id=session_id,
            name="test",
            started_at=datetime.now(timezone.utc),
            ended_at=None,
            metadata=metadata,
        )

        assert session.metadata == metadata

    def test_session_is_active_when_not_ended(self) -> None:
        """Test that session is active when ended_at is None."""
        session = Session(
            id=ULID(),
            name="test",
            started_at=datetime.now(timezone.utc),
            ended_at=None,
            metadata={},
        )

        assert session.is_active is True

    def test_session_is_not_active_when_ended(self) -> None:
        """Test that session is not active when ended_at is set."""
        started_at = datetime.now(timezone.utc)
        ended_at = datetime.now(timezone.utc)

        session = Session(
            id=ULID(),
            name="test",
            started_at=started_at,
            ended_at=ended_at,
            metadata={},
        )

        assert session.is_active is False

    def test_session_duration_is_none_when_active(self) -> None:
        """Test that duration is None when session is still active."""
        session = Session(
            id=ULID(),
            name="test",
            started_at=datetime.now(timezone.utc),
            ended_at=None,
            metadata={},
        )

        assert session.duration is None

    def test_session_duration_calculated_correctly(self) -> None:
        """Test that duration is calculated correctly when session is ended."""
        started_at = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        ended_at = datetime(2025, 1, 1, 0, 0, 5, tzinfo=timezone.utc)
        expected_duration_seconds = 5.0

        session = Session(
            id=ULID(),
            name="test",
            started_at=started_at,
            ended_at=ended_at,
            metadata={},
        )

        assert session.duration == expected_duration_seconds

    def test_session_is_immutable(self) -> None:
        """Test that Session is immutable (frozen)."""
        session = Session(
            id=ULID(),
            name="test",
            started_at=datetime.now(timezone.utc),
            ended_at=None,
            metadata={},
        )

        with pytest.raises(ValidationError):
            session.name = "new_name"


class TestEvent:
    """Test Event domain model."""

    def test_create_event_with_all_fields(self) -> None:
        """Test creating an event with all fields."""
        event_id = ULID()
        session_id = ULID()
        timestamp = 1234567890.123456
        device = "/dev/input/event0"
        code = 30
        code_name = "KEY_A"
        value = 1
        key_event = KeyEvent(
            timestamp=timestamp,
            device=device,
            code=code,
            code_name=code_name,
            value=value,
        )

        event = EventItem(
            id=event_id,
            session_id=session_id,
            event=key_event,
        )

        assert event.id == event_id
        assert event.session_id == session_id
        assert event.event.timestamp == timestamp
        assert event.event.device == device
        assert event.event.code == code
        assert event.event.code_name == code_name
        assert event.event.value == value

    def test_event_is_immutable(self) -> None:
        """Test that Event is immutable (frozen)."""
        event = EventItem(
            id=ULID(),
            session_id=ULID(),
            event=KeyEvent(
                timestamp=1234567890.0,
                device="/dev/input/event0",
                code=30,
                code_name="KEY_A",
                value=1,
            ),
        )

        with pytest.raises(ValidationError):
            event.session_id = ULID()
