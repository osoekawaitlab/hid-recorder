"""E2E tests for CLI."""

import subprocess
import sys
from pathlib import Path

import pytest

import hid_recorder


@pytest.fixture
def cli_executable_path() -> Path:
    """Get the path to the CLI executable."""
    python_path = Path(sys.executable)
    cli_path = python_path.parent / "hid-recorder"
    assert cli_path.exists(), f"CLI executable not found at {cli_path}"
    return cli_path


def test_cli_version(cli_executable_path: Path) -> None:
    """Test that the CLI version command works."""
    result = subprocess.run(  # noqa: S603
        [cli_executable_path.absolute(), "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert hid_recorder.__version__ in result.stdout
