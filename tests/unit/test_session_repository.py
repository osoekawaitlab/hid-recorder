"""Test SessionRepository for session CRUD operations."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from ulid import ULID

from hid_recorder.database import DatabaseManager
from hid_recorder.models import Session
from hid_recorder.session_repository import SessionRepository


class TestSessionRepository:
    """Test SessionRepository for creating, reading, updating, and deleting sessions."""

    @pytest.fixture
    def db_manager(self, tmp_path: Path) -> DatabaseManager:
        """Create and initialize a DatabaseManager for testing."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))
        manager.initialize()
        return manager

    @pytest.fixture
    def repository(self, db_manager: DatabaseManager) -> SessionRepository:
        """Create a SessionRepository for testing."""
        return SessionRepository(db_manager)

    def test_create_session(
        self, repository: SessionRepository, db_manager: DatabaseManager
    ) -> None:
        """Test creating a new session."""
        session_id = ULID()
        name = "test_session"
        started_at = datetime.now(timezone.utc)
        metadata = {"device": "keyboard", "version": "1.0"}

        session = Session(
            session_id=session_id,
            name=name,
            started_at=started_at,
            ended_at=None,
            metadata=metadata,
        )

        repository.create(session)

        # Verify session was created
        with db_manager as conn:
            cursor = conn.execute(
                "SELECT session_id, name, ended_at FROM sessions WHERE session_id = ?",
                (str(session_id),),
            )
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == str(session_id)
            assert result[1] == name
            assert result[2] is None  # ended_at should be NULL

    def test_get_session_by_id(self, repository: SessionRepository) -> None:
        """Test retrieving a session by ID."""
        session_id = ULID()
        session = Session(
            session_id=session_id,
            name="test_session",
            started_at=datetime.now(timezone.utc),
            ended_at=None,
            metadata={"key": "value"},
        )
        repository.create(session)

        # Retrieve the session
        retrieved = repository.get(session_id)
        assert retrieved is not None
        assert retrieved.session_id == session_id
        assert retrieved.name == "test_session"
        assert retrieved.ended_at is None
        assert retrieved.metadata == {"key": "value"}

    def test_get_nonexistent_session_returns_none(
        self, repository: SessionRepository
    ) -> None:
        """Test that getting a nonexistent session returns None."""
        nonexistent_id = ULID()
        result = repository.get(nonexistent_id)
        assert result is None

    def test_end_session(self, repository: SessionRepository) -> None:
        """Test ending a session by setting ended_at."""
        session_id = ULID()
        started_at = datetime.now(timezone.utc)
        session = Session(
            session_id=session_id,
            name="test_session",
            started_at=started_at,
            ended_at=None,
            metadata={},
        )
        repository.create(session)

        # End the session
        ended_at = datetime.now(timezone.utc)
        repository.end(session_id, ended_at)

        # Verify session was ended
        retrieved = repository.get(session_id)
        assert retrieved is not None
        assert retrieved.ended_at is not None
        assert retrieved.ended_at.timestamp() == pytest.approx(ended_at.timestamp())

    def test_list_all_sessions(self, repository: SessionRepository) -> None:
        """Test listing all sessions."""
        session1_id = ULID()
        session2_id = ULID()

        session1 = Session(
            session_id=session1_id,
            name="session_1",
            started_at=datetime.now(timezone.utc),
            ended_at=None,
            metadata={},
        )
        session2 = Session(
            session_id=session2_id,
            name="session_2",
            started_at=datetime.now(timezone.utc),
            ended_at=None,
            metadata={},
        )

        repository.create(session1)
        repository.create(session2)

        # List all sessions
        expected_session_count = 2
        sessions = repository.list_all()
        assert len(sessions) == expected_session_count
        session_ids = {s.session_id for s in sessions}
        assert session1_id in session_ids
        assert session2_id in session_ids

    def test_list_active_sessions_only(self, repository: SessionRepository) -> None:
        """Test listing only active (not ended) sessions."""
        active_id = ULID()
        ended_id = ULID()

        active_session = Session(
            session_id=active_id,
            name="active",
            started_at=datetime.now(timezone.utc),
            ended_at=None,
            metadata={},
        )
        ended_session = Session(
            session_id=ended_id,
            name="ended",
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
            metadata={},
        )

        repository.create(active_session)
        repository.create(ended_session)

        # List only active sessions
        active_sessions = repository.list_active()
        assert len(active_sessions) == 1
        assert active_sessions[0].session_id == active_id
        assert active_sessions[0].is_active is True

    def test_list_sessions_by_name_pattern(self, repository: SessionRepository) -> None:
        """Test listing sessions by name pattern."""
        test1_id = ULID()
        test2_id = ULID()
        other_id = ULID()

        session1 = Session(
            session_id=test1_id,
            name="test_001",
            started_at=datetime.now(timezone.utc),
            ended_at=None,
            metadata={},
        )
        session2 = Session(
            session_id=test2_id,
            name="test_002",
            started_at=datetime.now(timezone.utc),
            ended_at=None,
            metadata={},
        )
        session3 = Session(
            session_id=other_id,
            name="other_session",
            started_at=datetime.now(timezone.utc),
            ended_at=None,
            metadata={},
        )

        repository.create(session1)
        repository.create(session2)
        repository.create(session3)

        # List sessions matching pattern
        expected_matching_count = 2
        test_sessions = repository.list_by_name_pattern("test_%")
        assert len(test_sessions) == expected_matching_count
        test_ids = {s.session_id for s in test_sessions}
        assert test1_id in test_ids
        assert test2_id in test_ids
        assert other_id not in test_ids

    def test_delete_session(self, repository: SessionRepository) -> None:
        """Test deleting a session."""
        session_id = ULID()
        session = Session(
            session_id=session_id,
            name="to_delete",
            started_at=datetime.now(timezone.utc),
            ended_at=None,
            metadata={},
        )
        repository.create(session)

        # Delete the session
        repository.delete(session_id)

        # Verify session was deleted
        result = repository.get(session_id)
        assert result is None

    def test_delete_nonexistent_session_does_not_raise(
        self, repository: SessionRepository
    ) -> None:
        """Test that deleting a nonexistent session does not raise an error."""
        nonexistent_id = ULID()
        # Should not raise
        repository.delete(nonexistent_id)

    def test_metadata_is_serialized_correctly(
        self, repository: SessionRepository
    ) -> None:
        """Test that metadata dict is correctly serialized and deserialized."""
        session_id = ULID()
        complex_metadata = {
            "device": "keyboard",
            "version": "1.2.3",
            "test_type": "integration",
        }

        session = Session(
            session_id=session_id,
            name="metadata_test",
            started_at=datetime.now(timezone.utc),
            ended_at=None,
            metadata=complex_metadata,
        )
        repository.create(session)

        # Retrieve and verify metadata
        retrieved = repository.get(session_id)
        assert retrieved is not None
        assert retrieved.metadata == complex_metadata
        assert retrieved.metadata["device"] == "keyboard"
        assert retrieved.metadata["version"] == "1.2.3"
