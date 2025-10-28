"""CLI for the hid-recorder."""

import json
import sys
from argparse import ArgumentParser, Namespace

from hid_recorder import Recorder, __version__


def cmd_list_sessions(args: Namespace) -> None:
    """List all recording sessions."""
    recorder = Recorder(args.database)
    sessions = recorder.list_sessions()

    if args.format == "json":
        output = [
            {
                "session_id": str(session.session_id),
                "name": session.name,
                "started_at": session.started_at.isoformat(),
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                "is_active": session.is_active,
                "metadata": session.metadata,
            }
            for session in sessions
        ]
        sys.stdout.write(json.dumps(output, indent=2))
    else:
        # Simple text format
        for session in sessions:
            status = "ACTIVE" if session.is_active else "ENDED"
            sys.stdout.write(f"{session.session_id} | {session.name} | {status}\n")


def main() -> None:
    """Main entry point for the CLI."""
    parser = ArgumentParser(description="HID Recorder CLI")
    parser.add_argument(
        "--version",
        action="version",
        version=__version__,
        help="Show the version of hid-recorder",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list-sessions command
    list_parser = subparsers.add_parser(
        "list-sessions", help="List all recording sessions"
    )
    list_parser.add_argument(
        "--database",
        required=True,
        help="Path to the database file",
    )
    list_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (json or text)",
    )
    list_parser.set_defaults(func=cmd_list_sessions)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    elif args.command is None:
        parser.print_help()
        sys.exit(0)
