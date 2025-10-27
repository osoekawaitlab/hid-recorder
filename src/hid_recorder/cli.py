"""CLI for the hid-recorder."""

from argparse import ArgumentParser

from hid_recorder import __version__


def main() -> None:
    """Main entry point for the CLI."""
    parser = ArgumentParser(description="HID Recorder CLI")
    parser.add_argument(
        "--version",
        action="version",
        version=__version__,
        help="Show the version of hid-recorder",
    )
    _ = parser.parse_args()
