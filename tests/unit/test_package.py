"""Test package exports."""

import re

import hid_recorder


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
