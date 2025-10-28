"""Converter for hid-interceptor InputEvent to hid-recorder Event model."""

from hid_interceptor.models import InputEvent
from ulid import ULID

from hid_recorder.models import Event


def convert_input_event_to_event(input_event: InputEvent, session_id: ULID) -> Event:
    """Convert hid-interceptor InputEvent to hid-recorder Event.

    Args:
        input_event: InputEvent from hid-interceptor (KeyEvent, RelEvent, or AbsEvent).
        session_id: ULID of the session to associate this event with.

    Returns:
        Event object suitable for persistence with generated ULID.
    """
    kind_attr = input_event.kind
    kind_value_raw = getattr(kind_attr, "value", kind_attr)
    kind_value = str(kind_value_raw)

    return Event(
        event_id=ULID(),
        session_id=session_id,
        timestamp=input_event.timestamp,
        device=input_event.device,
        kind=kind_value,
        code=input_event.code,
        code_name=input_event.code_name,
        value=input_event.value,
    )
