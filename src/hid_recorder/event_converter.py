"""Converter for hid-interceptor InputEvent to hid-recorder Event model."""

from hid_interceptor.models import InputEvent
from ulid import ULID

from hid_recorder.models import EventItem


def convert_input_event_to_event(
    input_event: InputEvent, session_id: ULID
) -> EventItem:
    """Convert hid-interceptor InputEvent to hid-recorder Event.

    Args:
        input_event: InputEvent from hid-interceptor (KeyEvent, RelEvent, or AbsEvent).
        session_id: ULID of the session to associate this event with.

    Returns:
        Event object suitable for persistence with generated ULID.
    """
    return EventItem(
        id=ULID(),
        session_id=session_id,
        event=input_event,
    )
