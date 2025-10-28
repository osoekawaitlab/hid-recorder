"""Test package exports."""

import re

import hid_recorder
from hid_recorder.models import Event, Session
from hid_recorder.recorder import Recorder


def test_version_exported() -> None:
    """Test that __version__ is correctly exported."""
    assert hasattr(hid_recorder, "__version__"), "__version__ not found in hid_recorder"
    version = hid_recorder.__version__
    assert isinstance(version, str), "__version__ should be a string"
    # Simple semantic versioning pattern check
    pattern = r"^\d+\.\d+\.\d+$"
    assert re.match(pattern, version), (
        f"__version__ '{version}' does not match semantic versioning pattern"
    )


def test_recorder_exported() -> None:
    """Test that Recorder class is exported."""
    assert hasattr(hid_recorder, "Recorder"), "Recorder class not found in hid_recorder"
    # Verify it's the correct class
    assert hid_recorder.Recorder is Recorder


def test_session_exported() -> None:
    """Test that Session model is exported."""
    assert hasattr(hid_recorder, "Session"), "Session model not found in hid_recorder"
    # Verify it's the correct class
    assert hid_recorder.Session is Session


def test_event_exported() -> None:
    """Test that Event model is exported."""
    assert hasattr(hid_recorder, "Event"), "Event model not found in hid_recorder"
    # Verify it's the correct class
    assert hid_recorder.Event is Event
