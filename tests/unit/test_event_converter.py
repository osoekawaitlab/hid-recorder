"""Test event conversion from hid-interceptor InputEvent to our Event model."""

from hid_interceptor.models import AbsEvent, KeyEvent, RelEvent
from ulid import ULID

from hid_recorder.event_converter import convert_input_event_to_event


class TestEventConverter:
    """Test converting hid-interceptor InputEvent to hid-recorder Event."""

    def test_convert_key_event(self) -> None:
        """Test converting a KeyEvent from hid-interceptor."""
        expected_timestamp = 1234567890.123456
        expected_code = 30

        input_event = KeyEvent(
            device="/dev/input/event0",
            timestamp=expected_timestamp,
            code=expected_code,
            code_name="KEY_A",
            value=1,
        )
        session_id = ULID()

        event = convert_input_event_to_event(input_event, session_id)

        assert event.session_id == session_id
        assert event.timestamp == expected_timestamp
        assert event.device == "/dev/input/event0"
        assert event.kind == "KEY"
        assert event.code == expected_code
        assert event.code_name == "KEY_A"
        assert event.value == 1
        assert isinstance(event.event_id, ULID)  # ULID is auto-generated

    def test_convert_rel_event(self) -> None:
        """Test converting a RelEvent from hid-interceptor."""
        expected_value = 10

        input_event = RelEvent(
            device="/dev/input/event1",
            timestamp=1234567891.0,
            code=0,
            code_name="REL_X",
            value=expected_value,
        )
        session_id = ULID()

        event = convert_input_event_to_event(input_event, session_id)

        assert event.session_id == session_id
        assert event.kind == "REL"
        assert event.code_name == "REL_X"
        assert event.value == expected_value

    def test_convert_abs_event(self) -> None:
        """Test converting an AbsEvent from hid-interceptor."""
        expected_value = 100

        input_event = AbsEvent(
            device="/dev/input/event2",
            timestamp=1234567892.0,
            code=0,
            code_name="ABS_X",
            value=expected_value,
        )
        session_id = ULID()

        event = convert_input_event_to_event(input_event, session_id)

        assert event.session_id == session_id
        assert event.kind == "ABS"
        assert event.code_name == "ABS_X"
        assert event.value == expected_value

    def test_convert_event_preserves_all_fields(self) -> None:
        """Test that conversion preserves all InputEvent fields."""
        input_event = KeyEvent(
            device="/dev/input/event3",
            timestamp=9999999999.999999,
            code=999,
            code_name="TEST_CODE",
            value=1,
        )
        session_id = ULID()

        event = convert_input_event_to_event(input_event, session_id)

        # Verify all fields are preserved
        assert event.device == input_event.device
        assert event.timestamp == input_event.timestamp
        assert event.code == input_event.code
        assert event.code_name == input_event.code_name
        assert event.value == input_event.value
        assert event.kind == input_event.kind.value
        assert event.session_id == session_id

    def test_convert_with_string_kind(self) -> None:
        """Test that kind is converted to string."""
        input_event = KeyEvent(
            device="/dev/input/event0",
            timestamp=1000.0,
            code=1,
            code_name="BTN_LEFT",
            value=1,
        )
        session_id = ULID()

        event = convert_input_event_to_event(input_event, session_id)

        assert isinstance(event.kind, str)
        assert event.kind == "KEY"
