"""Domain models for HID recording."""

from datetime import datetime

from hid_interceptor import InputEvent
from pydantic import BaseModel, ConfigDict
from ulid import ULID


class Session(BaseModel):
    """Recording session - aggregate root for events.

    Represents a cohesive unit of HID event recording, typically corresponding
    to a single test execution or recording period.

    Attributes:
        id: Unique identifier for the session (ULID).
        name: Human-readable name for the session.
        started_at: Timestamp when the session started.
        ended_at: Timestamp when the session ended (None if still active).
        metadata: Additional metadata for the session (e.g., device info).
    """

    model_config = ConfigDict(frozen=True)

    id: ULID
    name: str
    started_at: datetime
    ended_at: datetime | None
    metadata: dict[str, str]

    @property
    def is_active(self) -> bool:
        """Check if the session is still active.

        Returns:
            True if the session has not ended yet, False otherwise.
        """
        return self.ended_at is None

    @property
    def duration(self) -> float | None:
        """Calculate the duration of the session in seconds.

        Returns:
            Duration in seconds if session has ended, None otherwise.
        """
        if self.ended_at is None:
            return None
        return (self.ended_at - self.started_at).total_seconds()


class EventItem(BaseModel):
    """HID event item within a recording session.

    Represents a single HID input event captured from hid-interceptor.

    Attributes:
        id: Unique identifier for the event (ULID).
        session_id: ID of the session this event belongs to (ULID).
        event: The actual HID input event data (InputEvent).
    """

    model_config = ConfigDict(frozen=True)

    id: ULID
    session_id: ULID
    event: InputEvent
