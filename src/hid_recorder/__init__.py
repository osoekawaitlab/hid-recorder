"""Record HID input events to database or file."""

from hid_recorder.models import Event, Session
from hid_recorder.recorder import Recorder

__version__ = "0.1.0"

__all__ = ["Event", "Recorder", "Session", "__version__"]
