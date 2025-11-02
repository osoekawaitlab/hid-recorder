"""E2E tests for the async session workflow with hid-interceptor."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, ClassVar

import pytest
from hid_interceptor import HIDInterceptor
from hid_interceptor.device import Device
from hid_interceptor.event_dispatcher import EventDispatcher
from hid_interceptor.models import InputEvent, KeyEvent, RelEvent

from hid_recorder import Recorder

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable
    from pathlib import Path

    from ulid import ULID


class FakeDevice(Device):
    """Test double for hid-interceptor devices."""

    events_by_path: ClassVar[dict[str, list[KeyEvent | RelEvent]]] = {}

    def __init__(self, path: str, events: list[KeyEvent | RelEvent]) -> None:
        """Initialize the fake device with a path and queued events."""
        self._path = path
        self._events = events

    @classmethod
    async def open(cls, path: str) -> FakeDevice:
        """Return a FakeDevice seeded with events for the requested path."""
        events = cls.events_by_path.get(path, [])
        return cls(path, list(events))

    @property
    def path(self) -> str:
        """Expose the fake device path."""
        return self._path

    async def events(self) -> AsyncIterator[KeyEvent | RelEvent]:
        """Yield stored events and then block indefinitely."""
        for event in self._events:
            yield event
            await asyncio.sleep(0)

        await asyncio.Event().wait()

    def close(self) -> None:
        """Close the fake device (no-op for tests)."""


class InlineEventDispatcher(EventDispatcher):
    """Dispatcher that executes hooks synchronously on the event loop."""

    async def _execute_hook(
        self, hook: Callable[[InputEvent], None], event: InputEvent
    ) -> None:
        try:
            hook(event)
        except Exception:
            self._logger.exception(
                "Error executing hook: %s", getattr(hook, "__name__", repr(hook))
            )


async def wait_for_event_count(
    recorder: Recorder, session_id: ULID, expected: int, timeout: float = 1.0
) -> None:
    """Poll until the expected number of events is stored or timeout."""
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        events = recorder.get_events(session_id)
        if len(events) >= expected:
            return
        if asyncio.get_running_loop().time() >= deadline:
            timeout_msg = "Timed out waiting for events to persist"
            raise TimeoutError(timeout_msg)
        await asyncio.sleep(0.01)


@pytest.fixture
def recorder(tmp_path: Path) -> Recorder:
    """Build a Recorder that writes into a temporary SQLite file."""
    return Recorder(str(tmp_path / "workflow.db"))


def test_interceptor_records_events_with_session_context(
    recorder: Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Events dispatched by hid-interceptor persist via async session context."""
    device_path = "/dev/input/fake0"
    FakeDevice.events_by_path = {
        device_path: [
            KeyEvent(
                device=device_path,
                timestamp=1000.0,
                code=30,
                code_name="KEY_A",
                value=1,
            ),
            KeyEvent(
                device=device_path,
                timestamp=1000.2,
                code=30,
                code_name="KEY_A",
                value=0,
            ),
        ]
    }

    monkeypatch.setattr(
        "hid_interceptor.interceptor.list_devices",
        lambda _input_device_dir="/dev/input": [device_path],
    )

    async def main() -> None:
        async with recorder.session(name="interceptor_context") as ctx:
            session_id = ctx.session.id
            dispatcher = InlineEventDispatcher(hooks=[ctx.hook])
            interceptor = HIDInterceptor(dispatcher=dispatcher, device_class=FakeDevice)

            run_task = asyncio.create_task(ctx.run(interceptor.run))

            await wait_for_event_count(recorder, session_id, expected=2)
            ctx.stop_event.set()
            await run_task

        stored_events = recorder.get_events(session_id)
        expected_event_count = 2
        assert len(stored_events) == expected_event_count
        assert stored_events[0].event.code_name == "KEY_A"
        assert stored_events[0].event.value == 1
        assert stored_events[1].event.value == 0

        completed_session = recorder.get_session(session_id)
        assert completed_session is not None
        assert completed_session.is_active is False

    asyncio.run(main())


def test_interceptor_session_handle_run_without_context(
    recorder: Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Awaited session handles support manual lifecycle control."""
    device_path = "/dev/input/fake1"
    FakeDevice.events_by_path = {
        device_path: [
            RelEvent(
                device=device_path,
                timestamp=2000.0,
                code=0,
                code_name="REL_X",
                value=15,
            ),
        ]
    }

    monkeypatch.setattr(
        "hid_interceptor.interceptor.list_devices",
        lambda _input_device_dir="/dev/input": [device_path],
    )

    async def main() -> None:
        ctx = await recorder.session(
            name="interceptor_handle", metadata={"mode": "manual"}
        )
        session_id = ctx.session.id
        dispatcher = InlineEventDispatcher(hooks=[ctx.hook])
        interceptor = HIDInterceptor(dispatcher=dispatcher, device_class=FakeDevice)

        run_task = asyncio.create_task(ctx.run(interceptor.run, auto_close=False))

        await wait_for_event_count(recorder, session_id, expected=1)
        ctx.stop_event.set()
        await run_task

        active_session = recorder.get_session(session_id)
        assert active_session is not None
        assert active_session.is_active is True

        await ctx.close()

        stored_events = recorder.get_events(session_id)
        expected_event_count = 1
        assert len(stored_events) == expected_event_count
        assert stored_events[0].event.code_name == "REL_X"

    asyncio.run(main())
