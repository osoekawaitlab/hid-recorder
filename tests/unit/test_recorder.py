"""Test Recorder public API."""

import asyncio
from pathlib import Path

import pytest
from hid_interceptor.models import KeyEvent, RelEvent
from ulid import ULID

from hid_recorder.recorder import Recorder


class TestRecorder:
    """Test Recorder public API for session management and event recording."""

    @pytest.fixture
    def db_path(self, tmp_path: Path) -> str:
        """Create a temporary database path."""
        return str(tmp_path / "test.db")

    @pytest.fixture
    def recorder(self, db_path: str) -> Recorder:
        """Create a Recorder instance for testing."""
        return Recorder(db_path)

    def test_create_recorder_initializes_database(self, db_path: str) -> None:
        """Test that creating a Recorder initializes the database."""
        recorder = Recorder(db_path)
        assert recorder.db_path == db_path

        # Verify database was initialized by checking sessions can be listed
        sessions = recorder.list_sessions()
        assert sessions == []

    def test_start_session_creates_active_session(self, recorder: Recorder) -> None:
        """Test starting a new session."""
        name = "test_session"
        metadata = {"device": "keyboard", "version": "1.0"}

        session = recorder.start_session(name=name, metadata=metadata)

        assert session.session_id is not None
        assert isinstance(session.session_id, ULID)
        assert session.name == name
        assert session.metadata == metadata
        assert session.is_active is True
        assert session.ended_at is None

    def test_end_session_marks_session_as_ended(self, recorder: Recorder) -> None:
        """Test ending a session."""
        session = recorder.start_session(name="test", metadata={})
        assert session.is_active is True

        recorder.end_session(session.session_id)

        # Retrieve and verify session is ended
        ended_session = recorder.get_session(session.session_id)
        assert ended_session is not None
        assert ended_session.is_active is False
        assert ended_session.ended_at is not None

    def test_get_session_returns_session_by_id(self, recorder: Recorder) -> None:
        """Test retrieving a session by ID."""
        created_session = recorder.start_session(name="test", metadata={})

        retrieved_session = recorder.get_session(created_session.session_id)

        assert retrieved_session is not None
        assert retrieved_session.session_id == created_session.session_id
        assert retrieved_session.name == "test"

    def test_get_session_returns_none_for_nonexistent_id(
        self, recorder: Recorder
    ) -> None:
        """Test that getting a nonexistent session returns None."""
        nonexistent_id = ULID()
        result = recorder.get_session(nonexistent_id)
        assert result is None

    def test_list_sessions_returns_all_sessions(self, recorder: Recorder) -> None:
        """Test listing all sessions."""
        expected_session_count = 3
        session1 = recorder.start_session(name="session1", metadata={})
        session2 = recorder.start_session(name="session2", metadata={})
        session3 = recorder.start_session(name="session3", metadata={})

        sessions = recorder.list_sessions()

        assert len(sessions) == expected_session_count
        session_ids = {s.session_id for s in sessions}
        assert session1.session_id in session_ids
        assert session2.session_id in session_ids
        assert session3.session_id in session_ids

    def test_list_active_sessions_only_returns_active(self, recorder: Recorder) -> None:
        """Test listing only active sessions."""
        active_session = recorder.start_session(name="active", metadata={})
        ended_session = recorder.start_session(name="ended", metadata={})
        recorder.end_session(ended_session.session_id)

        active_sessions = recorder.list_active_sessions()

        assert len(active_sessions) == 1
        assert active_sessions[0].session_id == active_session.session_id

    def test_session_context_manager_creates_and_ends_session(
        self, recorder: Recorder
    ) -> None:
        """Test using session() as an async context manager."""

        async def main() -> None:
            name = "context_test"
            metadata = {"key": "value"}

            async with recorder.session(name=name, metadata=metadata) as ctx:
                session_id = ctx.session.session_id
                assert ctx.session.name == name
                assert ctx.session.metadata == metadata
                assert ctx.session.is_active is True

            ended_session = recorder.get_session(session_id)
            assert ended_session is not None
            assert ended_session.is_active is False

        asyncio.run(main())

    def test_session_handle_can_be_awaited(self, recorder: Recorder) -> None:
        """Test that session() can be awaited to obtain a SessionHandle."""

        async def main() -> None:
            handle = await recorder.session(name="awaited", metadata={})
            try:
                assert handle.session.is_active is True
            finally:
                await handle.close()

            ended_session = recorder.get_session(handle.session.session_id)
            assert ended_session is not None
            assert ended_session.is_active is False

        asyncio.run(main())

    def test_session_context_manager_ends_session_on_exception(
        self, recorder: Recorder
    ) -> None:
        """Test that session context manager ends session even on exception."""

        async def main() -> None:
            error_message = "Test error"
            session_id: ULID | None = None

            async def session_with_error() -> None:
                nonlocal session_id
                async with recorder.session(name="test", metadata={}) as ctx:
                    session_id = ctx.session.session_id
                    raise RuntimeError(error_message)

            with pytest.raises(RuntimeError, match=error_message):
                await session_with_error()

            assert session_id is not None
            ended_session = recorder.get_session(session_id)
            assert ended_session is not None
            assert ended_session.is_active is False

        asyncio.run(main())

    def test_get_events_returns_events_for_session(self, recorder: Recorder) -> None:
        """Test retrieving events for a session."""
        session = recorder.start_session(name="test", metadata={})

        # Initially no events
        events = recorder.get_events(session.session_id)
        assert events == []

    def test_get_events_returns_empty_for_nonexistent_session(
        self, recorder: Recorder
    ) -> None:
        """Test that getting events for nonexistent session returns empty list."""
        nonexistent_id = ULID()
        events = recorder.get_events(nonexistent_id)
        assert events == []

    def test_recorder_can_be_reused_across_instances(self, db_path: str) -> None:
        """Test that Recorder instances can share the same database."""
        # Create session with first instance
        recorder1 = Recorder(db_path)
        session = recorder1.start_session(name="test", metadata={})

        # Retrieve session with second instance
        recorder2 = Recorder(db_path)
        retrieved_session = recorder2.get_session(session.session_id)

        assert retrieved_session is not None
        assert retrieved_session.session_id == session.session_id

    def test_start_session_with_default_empty_metadata(
        self, recorder: Recorder
    ) -> None:
        """Test starting a session with default empty metadata."""
        session = recorder.start_session(name="test")

        assert session.metadata == {}

    def test_record_event_saves_event_to_session(self, recorder: Recorder) -> None:
        """Test recording an event to a session."""
        session = recorder.start_session(name="test", metadata={})
        input_event = KeyEvent(
            device="/dev/input/event0",
            timestamp=1000.0,
            code=30,
            code_name="KEY_A",
            value=1,
        )

        recorder.record_event(input_event, session.session_id)

        # Verify event was saved
        events = recorder.get_events(session.session_id)
        assert len(events) == 1
        assert events[0].device == "/dev/input/event0"
        assert events[0].kind == "KEY"
        assert events[0].code_name == "KEY_A"

    def test_record_multiple_events_to_session(self, recorder: Recorder) -> None:
        """Test recording multiple events to a session."""
        session = recorder.start_session(name="test", metadata={})

        recorder.record_event(
            KeyEvent(
                device="/dev/input/event0",
                timestamp=1000.0,
                code=30,
                code_name="KEY_A",
                value=1,
            ),
            session.session_id,
        )
        recorder.record_event(
            RelEvent(
                device="/dev/input/event1",
                timestamp=1001.0,
                code=0,
                code_name="REL_X",
                value=10,
            ),
            session.session_id,
        )

        # Verify both events were saved
        expected_event_count = 2
        events = recorder.get_events(session.session_id)
        assert len(events) == expected_event_count
        assert events[0].kind == "KEY"
        assert events[1].kind == "REL"

    def test_record_event_returns_event_id(self, recorder: Recorder) -> None:
        """Test that record_event returns the assigned event_id."""
        session = recorder.start_session(name="test", metadata={})
        input_event = KeyEvent(
            device="/dev/input/event0",
            timestamp=1000.0,
            code=30,
            code_name="KEY_A",
            value=1,
        )

        event_id = recorder.record_event(input_event, session.session_id)

        assert event_id is not None
        assert event_id > 0

    def test_record_events_to_different_sessions(self, recorder: Recorder) -> None:
        """Test that events are correctly associated with their sessions."""
        session1 = recorder.start_session(name="session1", metadata={})
        session2 = recorder.start_session(name="session2", metadata={})

        recorder.record_event(
            KeyEvent(
                device="/dev/input/event0",
                timestamp=1000.0,
                code=30,
                code_name="KEY_A",
                value=1,
            ),
            session1.session_id,
        )
        recorder.record_event(
            KeyEvent(
                device="/dev/input/event0",
                timestamp=1000.0,
                code=30,
                code_name="KEY_A",
                value=1,
            ),
            session1.session_id,
        )
        recorder.record_event(
            KeyEvent(
                device="/dev/input/event0",
                timestamp=1000.0,
                code=30,
                code_name="KEY_A",
                value=1,
            ),
            session2.session_id,
        )

        # Verify events are associated with correct sessions
        expected_session1_events = 2
        expected_session2_events = 1
        session1_events = recorder.get_events(session1.session_id)
        session2_events = recorder.get_events(session2.session_id)

        assert len(session1_events) == expected_session1_events
        assert len(session2_events) == expected_session2_events

    def test_create_hook_records_to_active_session(self, recorder: Recorder) -> None:
        """Test that hook returned by create_hook records to active session."""
        # Start a session
        session = recorder.start_session(name="test", metadata={})

        # Get hook function
        hook = recorder.create_hook()

        # Simulate hid-interceptor calling the hook
        hook(
            KeyEvent(
                device="/dev/input/event0",
                timestamp=1000.0,
                code=30,
                code_name="KEY_A",
                value=1,
            )
        )

        # Verify event was recorded to active session
        events = recorder.get_events(session.session_id)
        assert len(events) == 1
        assert events[0].code_name == "KEY_A"

    def test_create_hook_raises_when_no_active_session(
        self, recorder: Recorder
    ) -> None:
        """Test that hook raises error when no active session exists."""
        hook = recorder.create_hook()

        with pytest.raises(RuntimeError, match="No active session"):
            hook(
                KeyEvent(
                    device="/dev/input/event0",
                    timestamp=1000.0,
                    code=30,
                    code_name="KEY_A",
                    value=1,
                )
            )

    def test_create_hook_with_context_manager(self, recorder: Recorder) -> None:
        """Test that hook works with async context manager (auto lifecycle)."""

        async def main() -> None:
            hook = recorder.create_hook()

            async with recorder.session(name="test", metadata={}) as ctx:
                hook(
                    KeyEvent(
                        device="/dev/input/event0",
                        timestamp=1000.0,
                        code=30,
                        code_name="KEY_A",
                        value=1,
                    )
                )
                session_id = ctx.session.session_id

            events = recorder.get_events(session_id)
            assert len(events) == 1
            assert events[0].code_name == "KEY_A"

        asyncio.run(main())

    def test_session_handle_run_closes_session_by_default(
        self, recorder: Recorder
    ) -> None:
        """SessionHandle.run should end the session when runner exits."""

        async def main() -> None:
            async def dummy_runner(stop_event: asyncio.Event) -> str:
                stop_event.set()
                return "done"

            async with recorder.session(name="run", metadata={}) as ctx:
                session_id = ctx.session.session_id
                result = await ctx.run(dummy_runner)

            assert result == "done"
            ended_session = recorder.get_session(session_id)
            assert ended_session is not None
            assert ended_session.is_active is False

        asyncio.run(main())
