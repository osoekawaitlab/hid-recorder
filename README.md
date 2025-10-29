# hid-recorder

A Python library for recording HID (Human Interface Device) input events from hid-interceptor to SQLite database.

## Features

- **Session-based Recording**: Group events into sessions with metadata
- **Event Persistence**: Store all input events (keyboard, mouse, etc.) to SQLite
- **Easy Retrieval**: Query events by session, device, or event type
- **Async Session Helper**: Automatic lifecycle management via async context manager
- **Type-Safe**: Full type annotations with mypy strict mode
- **Well-Tested**: 97% test coverage with comprehensive unit and E2E tests

## Installation

```bash
pip install https://github.com/osoekawaitlab/hid-recorder
```

## Platform Support

hid-recorder relies on [hid-interceptor](https://github.com/osoekawaitlab/hid-interceptor), which uses the Linux `evdev` stack (`python-evdev`). Recording from physical devices therefore requires a Linux environment with access to `/dev/input/event*` (for example, running with the proper udev permissions or as root). On other operating systems you can still exercise the API with synthetic events, but live device capture is not available.

## Quick Start

### Basic Usage

```python
from hid_interceptor.models import KeyEvent
from hid_recorder import Recorder

# Initialize recorder with database path
recorder = Recorder("my_recordings.db")

# Start a recording session (this session becomes the active one)
session = recorder.start_session(
    name="test_001",
    metadata={"device": "custom_keyboard", "test_type": "functionality"},
)

# Obtain a reusable hook that always records to the active session
hook = recorder.create_hook()

# Simulate an incoming event (in real usage, pass `hook` to HIDInterceptor)
hook(
    KeyEvent(
        device="/dev/input/event0",
        timestamp=1000.0,
        code=30,
        code_name="KEY_A",
        value=1,
    )
)

# End session when done
recorder.end_session(session.session_id)

# Retrieve recorded events
for event in recorder.get_events(session.session_id):
    print(f"{event.timestamp}: {event.code_name} = {event.value}")
```

### Using Context Manager

```python
from hid_recorder import Recorder

recorder = Recorder("my_recordings.db")

# Automatic session lifecycle management (async)
import asyncio
from hid_interceptor import HIDInterceptor


async def main() -> None:
    async with recorder.session(name="test_002", metadata={"mode": "auto"}) as ctx:
        # Hook automatically records to the active session
        interceptor = HIDInterceptor(hooks=[ctx.hook])
        await ctx.run(interceptor.run)


asyncio.run(main())
```

## Domain Model

### Session

A `Session` represents a recording session - a logical grouping of events.

**Attributes:**

- `session_id`: Unique ULID identifier
- `name`: Human-readable name
- `started_at`: timezone.utc timestamp when session started
- `ended_at`: timezone.utc timestamp when session ended (None if active)
- `metadata`: Dictionary of custom metadata
- `is_active`: Property indicating if session is still active
- `duration`: Property calculating session duration in seconds

**Use Cases:**

- Automated testing of custom input devices
- Recording human interactions for analysis
- Capturing input sequences for replay

### Event

An `Event` represents a single HID input event.

**Attributes:**

- `event_id`: Auto-assigned ULID
- `session_id`: ULID of parent session
- `timestamp`: Event timestamp (from hid-interceptor)
- `device`: Device path (e.g., "/dev/input/event0")
- `kind`: Event type ("KEY", "REL", or "ABS")
- `code`: Event code
- `code_name`: Human-readable code name (e.g., "KEY_A")
- `value`: Event value

## API Reference

### Recorder

The facade exposes the following key methods:

- `start_session(name, metadata) -> Session`: begin a new recording session and activate it.
- `end_session(session_id) -> None`: finish a session and deactivate it.
- `record_event(input_event, session_id) -> ULID`: persist an event and return its ULID.
- `get_session(session_id) -> Session | None`: retrieve a session by ID.
- `list_sessions() -> list[Session]`: list all sessions (most recent first).
- `list_active_sessions() -> list[Session]`: list only active sessions.
- `get_events(session_id, device_filter=None, kind_filter=None) -> list[Event]`: fetch recorded events with optional filters.
- `create_hook() -> Callable[[InputEvent], None]`: get a reusable hook that records to the active session.
- `session(name, metadata=None) -> SessionHandleFactory`: async helper returning a handle for automatic lifecycle management.

`SessionHandle` (obtained via `async with` or `await recorder.session(...)`) exposes:

- `.session`: the active `Session` dataclass.
- `.hook`: a hook compatible with `HIDInterceptor`.
- `.stop_event`: `asyncio.Event` used to stop long-running tasks.
- `.run(runner, auto_close=True)`: convenience method to run async workflows such as `HIDInterceptor.run`.

## Examples

### Filtering Events

```python
# Get only keyboard events
keyboard_events = recorder.get_events(
    session_id,
    device_filter="/dev/input/event0"
)

# Get only mouse movement events
mouse_events = recorder.get_events(
    session_id,
    kind_filter="REL"
)
```

### Multiple Sessions

```python
# Record multiple test sessions
session1 = recorder.start_session(name="test_001")
# ... record events ...
recorder.end_session(session1.session_id)

session2 = recorder.start_session(name="test_002")
# ... record events ...
recorder.end_session(session2.session_id)

# List all sessions
all_sessions = recorder.list_sessions()

# Get events for specific session
test_001_events = recorder.get_events(session1.session_id)
test_002_events = recorder.get_events(session2.session_id)
```

### Integration with hid-interceptor

```python
import asyncio
from hid_interceptor import HIDInterceptor
from hid_recorder import Recorder


async def main() -> None:
    recorder = Recorder("recordings.db")

    async with recorder.session(name="interaction_capture") as ctx:
        interceptor = HIDInterceptor(hooks=[ctx.hook])
        await ctx.run(interceptor.run)


asyncio.run(main())
```

## Development

### Running Tests

```bash
# Unit tests
nox -s tests_unit

# E2E tests
nox -s tests_e2e

# All tests
nox -s tests_unit tests_e2e
```

### Code Quality

```bash
# Type checking and linting
nox -s quality

# Format code
nox -s format_code
```

## Architecture

hid-recorder follows Clean Architecture principles:

- **Domain Layer**: `Session` and `Event` models
- **Repository Layer**: Data access abstraction
- **Facade Layer**: `Recorder` public API
- **Infrastructure Layer**: SQLite database management

Key design patterns:

- **Repository Pattern**: `SessionRepository`, `EventRepository`
- **Facade Pattern**: `Recorder` class
- **Context Manager**: Automatic session lifecycle
- **Dependency Inversion**: Repositories depend on abstractions

## License

MIT License

## Requirements

- Python 3.10+
- hid-interceptor (for event capture)
- Linux with `evdev` access to `/dev/input/event*`
- SQLite 3 (included with Python)

## Contributing

Contributions are welcome! Please ensure:

- All tests pass (`nox -s tests_unit tests_e2e`)
- Code quality checks pass (`nox -s quality`)
