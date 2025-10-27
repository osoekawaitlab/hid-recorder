"""Nox configuration file for hid_recorder project."""

import nox

nox.options.default_venv_backend = "uv"

PYTHON_VERSIONS = ["3.10", "3.11", "3.12", "3.13", "3.14"]


@nox.session(python="3.12")
def tests_unit(session: nox.Session) -> None:
    """Run unit tests only."""
    session.install("-e", ".", "--group=dev")
    session.run("pytest", "tests/unit/", "-v")


@nox.session(python="3.12")
def tests_e2e(session: nox.Session) -> None:
    """Run E2E tests only."""
    session.install("-e", ".", "--group=dev")
    session.run("pytest", "tests/e2e/", "-v")


@nox.session(python=PYTHON_VERSIONS)
def tests_all_versions(session: nox.Session) -> None:
    """Run all tests across all supported Python versions."""
    session.install("-e", ".", "--group=dev")
    session.run("pytest")


@nox.session(python="3.12")
def mypy(session: nox.Session) -> None:
    """Run mypy type checking (requires Azure SDK for type stubs)."""
    session.install("-e", ".", "--group=dev")
    session.run("mypy", "src/", "tests/")


@nox.session(python="3.12")
def lint(session: nox.Session) -> None:
    """Run ruff linting."""
    session.install("-e", ".", "--group=dev")
    session.run("ruff", "check", ".")


@nox.session(python="3.12")
def format_code(session: nox.Session) -> None:
    """Run ruff formatting."""
    session.install("-e", ".", "--group=dev")
    session.run("ruff", "format", ".")


@nox.session(python="3.12")
def quality(session: nox.Session) -> None:
    """Run all code quality checks (mypy, ruff)."""
    session.install("-e", ".", "--group=dev")
    session.run("mypy", "src/", "tests/")
    session.run("ruff", "check", ".")


@nox.session(python="3.12")
def check_all(session: nox.Session) -> None:
    """Run all checks and tests."""
    session.install("-e", ".", "--group=dev")
    session.run("pytest")
    session.run("mypy", "src/", "tests/")
    session.run("ruff", "check", ".")


@nox.session(python="3.12")
def docs_build(session: nox.Session) -> None:
    """Build documentation."""
    session.install("-e", ".", "--group=docs", "--group=dev")
    session.run("mkdocs", "build", "--strict")
