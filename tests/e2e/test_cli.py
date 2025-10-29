"""E2E tests for CLI."""

import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from ulid import ULID

import hid_recorder
from hid_recorder.database import DatabaseManager


@pytest.fixture
def cli_executable_path() -> Path:
    """Get the path to the CLI executable."""
    python_path = Path(sys.executable)
    cli_path = python_path.parent / "hid-recorder"
    assert cli_path.exists(), f"CLI executable not found at {cli_path}"
    return cli_path


@pytest.fixture
def test_db(tmp_path: Path) -> Path:
    """Create a test database with sample sessions."""
    db_path = tmp_path / "test.db"

    # Use the application's own schema initializer
    db_manager = DatabaseManager(str(db_path))
    db_manager.initialize()

    # Insert test sessions directly with SQL.
    # Enable type detection so the registered datetime adapter is used.
    conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    now = datetime.now(timezone.utc)
    session1_id = str(ULID())
    session2_id = str(ULID())

    conn.execute(
        """
        INSERT INTO sessions (session_id, name, started_at, ended_at, metadata)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            session1_id,
            "test_session_1",
            now,
            now,  # Ended session
            json.dumps({"type": "test"}),
        ),
    )

    conn.execute(
        """
        INSERT INTO sessions (session_id, name, started_at, ended_at, metadata)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            session2_id,
            "test_session_2",
            now,
            None,  # Active session
            json.dumps({"type": "demo"}),
        ),
    )

    conn.commit()
    conn.close()

    return db_path


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


def test_cli_list_sessions(cli_executable_path: Path, test_db: Path) -> None:
    """Test list-sessions command."""
    result = subprocess.run(  # noqa: S603
        [
            cli_executable_path.absolute(),
            "list-sessions",
            "--database",
            str(test_db),
            "--format",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    # Parse JSON output
    sessions = json.loads(result.stdout)
    expected_session_count = 2
    assert len(sessions) == expected_session_count
    assert sessions[0]["name"] in ["test_session_1", "test_session_2"]
    assert sessions[1]["name"] in ["test_session_1", "test_session_2"]
