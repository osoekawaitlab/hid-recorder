"""Recorder public API for managing recording sessions and events."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Generator
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, TypeVar

from hid_interceptor.models import InputEvent
from typing_extensions import Self
from ulid import ULID

from hid_recorder.database import DatabaseManager
from hid_recorder.event_converter import convert_input_event_to_event
from hid_recorder.event_repository import EventRepository
from hid_recorder.models import EventItem, Session
from hid_recorder.session_repository import SessionRepository

if TYPE_CHECKING:
    from types import TracebackType


RecorderHook = Callable[[InputEvent], None]
T = TypeVar("T")


class SessionHandle:
    """Represents an active recording session with async helpers."""

    def __init__(
        self,
        recorder: Recorder,
        session: Session,
        hook: RecorderHook,
    ) -> None:
        """Store session context and the recorder hook."""
        self._recorder = recorder
        self.session = session
        self.hook = hook
        self.stop_event = asyncio.Event()
        self._closed = False

    async def run(
        self,
        runner: Callable[[asyncio.Event], Awaitable[T]],
        *,
        auto_close: bool = True,
    ) -> T:
        """Run an async workflow (e.g. HIDInterceptor.run) for this session."""
        try:
            return await runner(self.stop_event)
        finally:
            if auto_close:
                await self.close()

    async def close(self) -> None:
        """End the session if it is still active."""
        if self._closed:
            return
        self._closed = True
        self._recorder.end_session(self.session.id)

    async def __aenter__(self) -> Self:
        """Return the handle when entering an async context block."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Ensure the session is closed when leaving an async context."""
        await self.close()


class SessionHandleFactory:
    """Factory enabling `await` and `async with` usage for sessions."""

    def __init__(
        self,
        recorder: Recorder,
        name: str,
        metadata: dict[str, str] | None,
    ) -> None:
        """Capture parameters used when creating a session handle."""
        self._recorder = recorder
        self._name = name
        self._metadata = metadata or {}
        self._handle: SessionHandle | None = None

    async def _ensure_handle(self) -> SessionHandle:
        if self._handle is None:
            session = self._recorder.start_session(
                name=self._name, metadata=self._metadata
            )
            hook = self._recorder.create_hook()
            self._handle = SessionHandle(self._recorder, session, hook)
        return self._handle

    def __await__(self) -> Generator[Any, None, SessionHandle]:
        """Allow `await recorder.session(...)` to yield a handle."""
        return self._ensure_handle().__await__()

    async def __aenter__(self) -> SessionHandle:
        """Provide a session handle when entering an async context."""
        return await self._ensure_handle()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Close the underlying session when leaving the context."""
        handle = await self._ensure_handle()
        await handle.close()


class Recorder:
    """Public API for recording HID input events.

    This class provides a high-level interface for managing recording sessions
    and retrieving recorded events. It follows the Facade Pattern to hide
    complexity from calling code.

    Note:
        This class is stateful. An instance of this class holds a reference to
        the currently active session ID (`_active_session_id`). This is used by
        the hook created via `create_hook()` to automatically record events to
        the correct session. While the `session()` async context manager handles
        this lifecycle automatically, if you are managing multiple concurrent
        sessions manually, it is recommended to use a separate `Recorder`
        instance for each concurrent task to avoid race conditions.

    Attributes:
        db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path: str) -> None:
        """Initialize Recorder with a database path.

        Args:
            db_path: Path to SQLite database file or ":memory:" for in-memory database.
        """
        self.db_path = db_path
        self._db_manager = DatabaseManager(db_path)
        self._db_manager.initialize()

        self._session_repo = SessionRepository(self._db_manager)
        self._event_repo = EventRepository(self._db_manager)
        self._active_session_id: ULID | None = None

    def start_session(
        self, name: str, metadata: dict[str, str] | None = None
    ) -> Session:
        """Start a new recording session.

        Args:
            name: Human-readable name for the session.
            metadata: Optional metadata dictionary (e.g., device info, test conditions).

        Returns:
            The created Session object with a unique session_id (ULID).
        """
        session = Session(
            id=ULID(),
            name=name,
            started_at=datetime.now(timezone.utc),
            ended_at=None,
            metadata=metadata or {},
        )
        self._session_repo.create(session)
        self._active_session_id = session.id
        return session

    def end_session(self, session_id: ULID) -> None:
        """End a recording session.

        Args:
            session_id: ULID of the session to end.
        """
        ended_at = datetime.now(timezone.utc)
        self._session_repo.end(session_id, ended_at)
        if self._active_session_id == session_id:
            self._active_session_id = None

    def get_session(self, session_id: ULID) -> Session | None:
        """Retrieve a session by its ID.

        Args:
            session_id: ULID of the session to retrieve.

        Returns:
            Session object if found, None otherwise.
        """
        return self._session_repo.get(session_id)

    def list_sessions(self) -> list[Session]:
        """List all recording sessions.

        Returns:
            List of all Session objects, ordered by start time (most recent first).
        """
        return self._session_repo.list_all()

    def list_active_sessions(self) -> list[Session]:
        """List only active (not ended) recording sessions.

        Returns:
            List of active Session objects.
        """
        return self._session_repo.list_active()

    def get_events(
        self,
        session_id: ULID,
        device_filter: str | None = None,
        kind_filter: str | None = None,
    ) -> list[EventItem]:
        """Retrieve events for a session.

        Args:
            session_id: ULID of the session.
            device_filter: Optional device path to filter by.
            kind_filter: Optional event kind to filter by (KEY, REL, ABS).

        Returns:
            List of Event objects, ordered by timestamp.
        """
        return self._event_repo.get_by_session(
            session_id, device_filter=device_filter, kind_filter=kind_filter
        )

    def record_event(self, input_event: InputEvent, session_id: ULID) -> ULID:
        """Record an input event to a session.

        This method converts a hid-interceptor InputEvent to our Event model
        and persists it to the database.

        Args:
            input_event: InputEvent from hid-interceptor
                (KeyEvent, RelEvent, or AbsEvent).
            session_id: ULID of the session to record this event to.

        Returns:
            The event_id (ULID) of the created event.

        Example:
            def my_hook(input_event: InputEvent) -> None:
                recorder.record_event(input_event, current_session_id)
        """
        event = convert_input_event_to_event(input_event, session_id)
        return self._event_repo.create(event)

    def create_hook(self) -> RecorderHook:
        """Create a hook function for automatic event recording.

        Returns a hook function that can be passed to hid-interceptor.
        The hook automatically records events to the active session.

        Returns:
            A callable that accepts InputEvent and records it.

        Raises:
            RuntimeError: When hook is called but no active session exists.

        Example:
            recorder = Recorder(db_path)
            hook = recorder.create_hook()

            async with recorder.session(name="test") as ctx:
                interceptor = HIDInterceptor(hooks=[ctx.hook])
                await ctx.run(interceptor.run)
        """

        def hook(input_event: InputEvent) -> None:
            if self._active_session_id is None:
                msg = "No active session"
                raise RuntimeError(msg)
            self.record_event(input_event, self._active_session_id)

        return hook

    def session(
        self, name: str, metadata: dict[str, str] | None = None
    ) -> SessionHandleFactory:
        """Create a session handle that supports async workflows.

        The returned object can be awaited to obtain a :class:`SessionHandle`
        or used directly in an ``async with`` block. Typical usage with
        ``hid_interceptor`` looks like:

        ```python
        async with recorder.session(name="demo") as ctx:
            interceptor = HIDInterceptor(hooks=[ctx.hook])
            await ctx.run(interceptor.run)
        ```
        """
        return SessionHandleFactory(self, name, metadata)
